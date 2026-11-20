"""initial schema

Creates every TraceHealth table, plus the rules that the database itself
enforces (so they hold even if application code has a bug):

  * no self-verification               (trigger on verifications)
  * report status follows decisions    (trigger on verifications)
  * final status can't be changed      (trigger on pollution_reports)
  * payouts only for VERIFIED reports  (trigger on payouts + UNIQUE report_id)
  * linkages only for VERIFIED reports (trigger on health_linkages)
  * audit log is append-only           (trigger on audit_logs)

It also inserts the default system settings (linkage parameters, payout amount).

Revision ID: 0001
Revises: 
Create Date: 2026-11-03 11:44:54.179500+00:00
"""
from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import column, table

revision: str = '0001'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# --------------------------------------------------------------------------
# Database-enforced business rules
# ERRCODE check_violation / restrict_violation make violations surface in
# Python as sqlalchemy.exc.IntegrityError, like any other constraint.
# --------------------------------------------------------------------------
TRIGGER_FUNCTIONS = [
    "th_prevent_self_verification",
    "th_apply_verification_to_report",
    "th_guard_report_status",
    "th_validate_payout",
    "th_validate_health_linkage",
    "th_audit_logs_append_only",
]

TRIGGER_SQL = [
    # 1. A reporter may not verify their own report (SRS 5.5)
    """
    CREATE FUNCTION th_prevent_self_verification() RETURNS trigger
    LANGUAGE plpgsql AS $$
    BEGIN
        IF EXISTS (
            SELECT 1 FROM pollution_reports r
            WHERE r.id = NEW.report_id AND r.reporter_id = NEW.verifier_id
        ) THEN
            RAISE EXCEPTION 'A reporter cannot verify their own report (report %)', NEW.report_id
                USING ERRCODE = 'check_violation';
        END IF;
        RETURN NEW;
    END;
    $$
    """,
    """
    CREATE TRIGGER trg_verifications_no_self_verification
    BEFORE INSERT OR UPDATE ON verifications
    FOR EACH ROW EXECUTE FUNCTION th_prevent_self_verification()
    """,
    # 2. Recording a decision updates the report's status in the same transaction
    """
    CREATE FUNCTION th_apply_verification_to_report() RETURNS trigger
    LANGUAGE plpgsql AS $$
    BEGIN
        UPDATE pollution_reports
           SET status = NEW.decision, updated_at = now()
         WHERE id = NEW.report_id;
        RETURN NEW;
    END;
    $$
    """,
    """
    CREATE TRIGGER trg_verifications_apply_to_report
    AFTER INSERT ON verifications
    FOR EACH ROW EXECUTE FUNCTION th_apply_verification_to_report()
    """,
    # 3. Report status may only change in ways backed by a verification record,
    #    and VERIFIED / REJECTED are final.
    """
    CREATE FUNCTION th_guard_report_status() RETURNS trigger
    LANGUAGE plpgsql AS $$
    BEGIN
        IF NEW.status IS NOT DISTINCT FROM OLD.status THEN
            RETURN NEW;
        END IF;
        IF OLD.status IN ('VERIFIED', 'REJECTED') THEN
            RAISE EXCEPTION 'Report % already has a final decision (%)', OLD.id, OLD.status
                USING ERRCODE = 'check_violation';
        END IF;
        IF NEW.status = 'PENDING' THEN
            RAISE EXCEPTION 'Report % cannot return to PENDING', OLD.id
                USING ERRCODE = 'check_violation';
        END IF;
        IF NOT EXISTS (
            SELECT 1 FROM verifications v
            WHERE v.report_id = NEW.id AND v.decision = NEW.status
        ) THEN
            RAISE EXCEPTION 'Status % for report % requires a matching verification record',
                NEW.status, NEW.id
                USING ERRCODE = 'check_violation';
        END IF;
        RETURN NEW;
    END;
    $$
    """,
    """
    CREATE TRIGGER trg_pollution_reports_guard_status
    BEFORE UPDATE OF status ON pollution_reports
    FOR EACH ROW EXECUTE FUNCTION th_guard_report_status()
    """,
    # 4. A payout requires a final VERIFIED decision for the same report and reporter
    """
    CREATE FUNCTION th_validate_payout() RETURNS trigger
    LANGUAGE plpgsql AS $$
    DECLARE
        v_decision text;
        v_is_final boolean;
        v_report_id uuid;
        r_reporter_id uuid;
    BEGIN
        SELECT decision, is_final, report_id
          INTO v_decision, v_is_final, v_report_id
          FROM verifications WHERE id = NEW.verification_id;
        IF FOUND AND (v_decision <> 'VERIFIED' OR NOT v_is_final
                      OR v_report_id <> NEW.report_id) THEN
            RAISE EXCEPTION 'Payouts require a final VERIFIED decision for report %', NEW.report_id
                USING ERRCODE = 'check_violation';
        END IF;
        SELECT reporter_id INTO r_reporter_id FROM pollution_reports WHERE id = NEW.report_id;
        IF FOUND AND r_reporter_id <> NEW.reporter_id THEN
            RAISE EXCEPTION 'Payout recipient must be the reporter of report %', NEW.report_id
                USING ERRCODE = 'check_violation';
        END IF;
        RETURN NEW;
    END;
    $$
    """,
    """
    CREATE TRIGGER trg_payouts_validate
    BEFORE INSERT OR UPDATE ON payouts
    FOR EACH ROW EXECUTE FUNCTION th_validate_payout()
    """,
    # 5. Health linkages may only reference VERIFIED reports
    """
    CREATE FUNCTION th_validate_health_linkage() RETURNS trigger
    LANGUAGE plpgsql AS $$
    BEGIN
        IF EXISTS (
            SELECT 1 FROM pollution_reports r
            WHERE r.id = NEW.report_id AND r.status <> 'VERIFIED'
        ) THEN
            RAISE EXCEPTION 'Health linkages may only reference VERIFIED reports (report %)',
                NEW.report_id
                USING ERRCODE = 'check_violation';
        END IF;
        RETURN NEW;
    END;
    $$
    """,
    """
    CREATE TRIGGER trg_health_linkages_validate
    BEFORE INSERT OR UPDATE ON health_linkages
    FOR EACH ROW EXECUTE FUNCTION th_validate_health_linkage()
    """,
    # 6. The audit log can be added to, but never edited or deleted (NFR 4)
    """
    CREATE FUNCTION th_audit_logs_append_only() RETURNS trigger
    LANGUAGE plpgsql AS $$
    BEGIN
        RAISE EXCEPTION 'audit_logs is append-only: % is not allowed', TG_OP
            USING ERRCODE = 'restrict_violation';
    END;
    $$
    """,
    """
    CREATE TRIGGER trg_audit_logs_append_only
    BEFORE UPDATE OR DELETE ON audit_logs
    FOR EACH ROW EXECUTE FUNCTION th_audit_logs_append_only()
    """,
]

# Approved defaults (editable by administrators from the settings screen)
DEFAULT_SETTINGS = [
    {"key": "linkage.radius_km", "value": 3,
     "description": "Search radius around a verified report for nearby facilities (km)."},
    {"key": "linkage.baseline_weeks", "value": 8,
     "description": "Weeks before the report used as the baseline visit rate."},
    {"key": "linkage.followup_weeks", "value": 4,
     "description": "Weeks after the report checked for a rise in visits."},
    {"key": "linkage.min_baseline_visits", "value": 10,
     "description": "Fewer baseline visits than this gives INSUFFICIENT_DATA."},
    {"key": "linkage.p_value_threshold", "value": 0.05,
     "description": "Significance level for flagging a SIGNAL."},
    {"key": "linkage.category_mapping",
     "value": {
         "OPEN_BURNING": ["RESPIRATORY"],
         "ILLEGAL_DUMPING": ["SKIN", "DIARRHOEAL"],
         "BLOCKED_DRAINAGE": ["DIARRHOEAL", "MALARIA"],
         "MEDICAL_WASTE": ["INJURY", "INFECTION"],
         "OTHER": [],
     },
     "description": "Which health conditions are checked for each pollution category. "
                    "To be confirmed with the partner clinic."},
    {"key": "payout.amount", "value": 50,
     "description": "Incentive paid per verified report."},
    {"key": "payout.currency", "value": "KES",
     "description": "ISO currency code for incentive payouts."},
    {"key": "dashboard.small_count_threshold", "value": 5,
     "description": "Visit counts below this are shown as '<N' to protect privacy."},
]


def upgrade() -> None:
    # PostGIS provides the geography type and distance functions
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('facilities',
    sa.Column('external_code', sa.String(length=50), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('latitude', sa.Double(), nullable=False),
    sa.Column('longitude', sa.Double(), nullable=False),
    sa.Column('location', geoalchemy2.types.Geography(geometry_type='POINT', srid=4326, spatial_index=False, from_text='ST_GeogFromText', name='geography', nullable=False), sa.Computed('(st_setsrid(st_makepoint(longitude, latitude), 4326))::geography', persisted=True), nullable=False),
    sa.Column('area_code', sa.String(length=50), nullable=False),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('latitude BETWEEN -90 AND 90', name=op.f('ck_facilities_latitude_range')),
    sa.CheckConstraint('longitude BETWEEN -180 AND 180', name=op.f('ck_facilities_longitude_range')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_facilities')),
    sa.UniqueConstraint('external_code', name=op.f('uq_facilities_external_code'))
    )
    op.create_index(op.f('ix_facilities_area_code'), 'facilities', ['area_code'], unique=False)
    op.create_index('ix_facilities_location', 'facilities', ['location'], unique=False, postgresql_using='gist')
    op.create_table('users',
    sa.Column('full_name', sa.String(length=120), nullable=False),
    sa.Column('phone_number', sa.String(length=20), nullable=False),
    sa.Column('email', sa.String(length=254), nullable=True),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('preferred_language', sa.Enum('EN', 'SW', name='language', native_enum=False, create_constraint=True), server_default='EN', nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('char_length(trim(full_name)) > 0', name=op.f('ck_users_full_name_not_blank')),
    sa.CheckConstraint('email IS NULL OR email = lower(email)', name=op.f('ck_users_email_lowercase')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
    sa.UniqueConstraint('email', name=op.f('uq_users_email')),
    sa.UniqueConstraint('phone_number', name=op.f('uq_users_phone_number'))
    )
    op.create_table('administrators',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('admin_level', sa.SmallInteger(), server_default=sa.text('1'), nullable=False),
    sa.CheckConstraint('admin_level BETWEEN 1 AND 3', name=op.f('ck_administrators_admin_level_range')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_administrators_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', name=op.f('pk_administrators'))
    )
    op.create_table('agency_staff',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('agency_name', sa.String(length=150), nullable=False),
    sa.Column('department', sa.String(length=150), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_agency_staff_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', name=op.f('pk_agency_staff'))
    )
    op.create_table('audit_logs',
    sa.Column('actor_id', sa.UUID(), nullable=True),
    sa.Column('action', sa.String(length=80), nullable=False),
    sa.Column('entity_type', sa.String(length=50), nullable=False),
    sa.Column('entity_id', sa.UUID(), nullable=True),
    sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['actor_id'], ['users.id'], name=op.f('fk_audit_logs_actor_id_users'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_audit_logs'))
    )
    op.create_index(op.f('ix_audit_logs_actor_id'), 'audit_logs', ['actor_id'], unique=False)
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'], unique=False)
    op.create_index('ix_audit_logs_entity', 'audit_logs', ['entity_type', 'entity_id'], unique=False)
    op.create_table('refresh_tokens',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_refresh_tokens_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_refresh_tokens')),
    sa.UniqueConstraint('token_hash', name=op.f('uq_refresh_tokens_token_hash'))
    )
    op.create_index(op.f('ix_refresh_tokens_user_id'), 'refresh_tokens', ['user_id'], unique=False)
    op.create_table('reporters',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('reputation_score', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('payout_phone', sa.String(length=20), nullable=True),
    sa.Column('payout_consent_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint('payout_phone IS NULL OR payout_consent_at IS NOT NULL', name=op.f('ck_reporters_payout_phone_requires_consent')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_reporters_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', name=op.f('pk_reporters'))
    )
    op.create_table('system_settings',
    sa.Column('key', sa.String(length=100), nullable=False),
    sa.Column('value', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['updated_by'], ['users.id'], name=op.f('fk_system_settings_updated_by_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('key', name=op.f('pk_system_settings'))
    )
    op.create_table('verifiers',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('assigned_zone', sa.String(length=100), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_verifiers_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', name=op.f('pk_verifiers'))
    )
    op.create_table('clinic_import_batches',
    sa.Column('filename', sa.String(length=255), nullable=False),
    sa.Column('imported_by', sa.UUID(), nullable=False),
    sa.Column('status', sa.Enum('ACCEPTED', 'REJECTED', name='import_batch_status', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('row_count', sa.Integer(), nullable=False),
    sa.Column('errors', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('row_count >= 0', name=op.f('ck_clinic_import_batches_row_count_non_negative')),
    sa.ForeignKeyConstraint(['imported_by'], ['administrators.user_id'], name=op.f('fk_clinic_import_batches_imported_by_administrators'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_clinic_import_batches'))
    )
    op.create_table('pollution_reports',
    sa.Column('client_report_id', sa.UUID(), nullable=False),
    sa.Column('reporter_id', sa.UUID(), nullable=False),
    sa.Column('photo_url', sa.String(length=500), nullable=False),
    sa.Column('latitude', sa.Double(), nullable=False),
    sa.Column('longitude', sa.Double(), nullable=False),
    sa.Column('location', geoalchemy2.types.Geography(geometry_type='POINT', srid=4326, spatial_index=False, from_text='ST_GeogFromText', name='geography', nullable=False), sa.Computed('(st_setsrid(st_makepoint(longitude, latitude), 4326))::geography', persisted=True), nullable=False),
    sa.Column('category', sa.Enum('OPEN_BURNING', 'ILLEGAL_DUMPING', 'BLOCKED_DRAINAGE', 'MEDICAL_WASTE', 'OTHER', name='pollution_category', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('captured_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('received_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('status', sa.Enum('PENDING', 'VERIFIED', 'REJECTED', 'FLAGGED', name='report_status', native_enum=False, create_constraint=True), server_default='PENDING', nullable=False),
    sa.Column('sync_status', sa.Enum('SUBMITTED_ONLINE', 'SYNCED_FROM_OFFLINE', name='sync_status', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.CheckConstraint('description IS NULL OR char_length(description) <= 1000', name=op.f('ck_pollution_reports_description_length')),
    sa.CheckConstraint('latitude BETWEEN -90 AND 90', name=op.f('ck_pollution_reports_latitude_range')),
    sa.CheckConstraint('longitude BETWEEN -180 AND 180', name=op.f('ck_pollution_reports_longitude_range')),
    sa.ForeignKeyConstraint(['reporter_id'], ['reporters.user_id'], name=op.f('fk_pollution_reports_reporter_id_reporters'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_pollution_reports')),
    sa.UniqueConstraint('client_report_id', name=op.f('uq_pollution_reports_client_report_id'))
    )
    op.create_index(op.f('ix_pollution_reports_category'), 'pollution_reports', ['category'], unique=False)
    op.create_index('ix_pollution_reports_location', 'pollution_reports', ['location'], unique=False, postgresql_using='gist')
    op.create_index(op.f('ix_pollution_reports_reporter_id'), 'pollution_reports', ['reporter_id'], unique=False)
    op.create_index('ix_pollution_reports_status_captured_at', 'pollution_reports', ['status', 'captured_at'], unique=False)
    op.create_table('clinic_visit_summaries',
    sa.Column('facility_id', sa.UUID(), nullable=False),
    sa.Column('import_batch_id', sa.UUID(), nullable=False),
    sa.Column('condition_category', sa.Enum('RESPIRATORY', 'SKIN', 'DIARRHOEAL', 'MALARIA', 'INJURY', 'INFECTION', 'OTHER', name='condition_category', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('period_start', sa.Date(), nullable=False),
    sa.Column('period_end', sa.Date(), nullable=False),
    sa.Column('visit_count', sa.Integer(), nullable=False),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('period_end >= period_start', name=op.f('ck_clinic_visit_summaries_period_order')),
    sa.CheckConstraint('visit_count >= 0', name=op.f('ck_clinic_visit_summaries_visit_count_non_negative')),
    sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], name=op.f('fk_clinic_visit_summaries_facility_id_facilities'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['import_batch_id'], ['clinic_import_batches.id'], name=op.f('fk_clinic_visit_summaries_import_batch_id_clinic_import_batches'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_clinic_visit_summaries')),
    sa.UniqueConstraint('facility_id', 'condition_category', 'period_start', 'period_end', name='uq_clinic_visit_summaries_facility_condition_period')
    )
    op.create_index(op.f('ix_clinic_visit_summaries_import_batch_id'), 'clinic_visit_summaries', ['import_batch_id'], unique=False)
    op.create_index('ix_clinic_visit_summaries_period', 'clinic_visit_summaries', ['period_start', 'period_end'], unique=False)
    op.create_table('health_linkages',
    sa.Column('report_id', sa.UUID(), nullable=False),
    sa.Column('facility_id', sa.UUID(), nullable=False),
    sa.Column('condition_category', sa.Enum('RESPIRATORY', 'SKIN', 'DIARRHOEAL', 'MALARIA', 'INJURY', 'INFECTION', 'OTHER', name='condition_category', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('radius_km', sa.Numeric(precision=6, scale=2), nullable=False),
    sa.Column('distance_km', sa.Double(), nullable=False),
    sa.Column('baseline_visits', sa.Integer(), nullable=True),
    sa.Column('followup_visits', sa.Integer(), nullable=True),
    sa.Column('rate_ratio', sa.Double(), nullable=True),
    sa.Column('p_value', sa.Double(), nullable=True),
    sa.Column('correlation_score', sa.Double(), nullable=True),
    sa.Column('status', sa.Enum('SIGNAL', 'NO_SIGNAL', 'INSUFFICIENT_DATA', name='linkage_status', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('detected_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('params_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.CheckConstraint("status = 'INSUFFICIENT_DATA' OR (rate_ratio IS NOT NULL AND p_value IS NOT NULL)", name=op.f('ck_health_linkages_statistics_required_for_result')),
    sa.CheckConstraint('correlation_score IS NULL OR correlation_score BETWEEN -1 AND 1', name=op.f('ck_health_linkages_correlation_range')),
    sa.CheckConstraint('distance_km >= 0', name=op.f('ck_health_linkages_distance_non_negative')),
    sa.CheckConstraint('p_value IS NULL OR p_value BETWEEN 0 AND 1', name=op.f('ck_health_linkages_p_value_range')),
    sa.CheckConstraint('radius_km > 0', name=op.f('ck_health_linkages_radius_positive')),
    sa.CheckConstraint('rate_ratio IS NULL OR rate_ratio >= 0', name=op.f('ck_health_linkages_rate_ratio_non_negative')),
    sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], name=op.f('fk_health_linkages_facility_id_facilities'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['report_id'], ['pollution_reports.id'], name=op.f('fk_health_linkages_report_id_pollution_reports'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_health_linkages')),
    sa.UniqueConstraint('report_id', 'facility_id', 'condition_category', name='uq_health_linkages_report_facility_condition')
    )
    op.create_index(op.f('ix_health_linkages_facility_id'), 'health_linkages', ['facility_id'], unique=False)
    op.create_index(op.f('ix_health_linkages_report_id'), 'health_linkages', ['report_id'], unique=False)
    op.create_index(op.f('ix_health_linkages_status'), 'health_linkages', ['status'], unique=False)
    op.create_table('notifications',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('type', sa.String(length=50), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('channel', sa.Enum('PUSH', 'SMS', 'IN_APP', name='notification_channel', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('status', sa.Enum('PENDING', 'SENT', 'FAILED', name='notification_status', native_enum=False, create_constraint=True), server_default='PENDING', nullable=False),
    sa.Column('related_report_id', sa.UUID(), nullable=True),
    sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['related_report_id'], ['pollution_reports.id'], name=op.f('fk_notifications_related_report_id_pollution_reports'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_notifications_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_notifications'))
    )
    op.create_index('ix_notifications_user_created', 'notifications', ['user_id', 'created_at'], unique=False)
    op.create_table('verifications',
    sa.Column('report_id', sa.UUID(), nullable=False),
    sa.Column('verifier_id', sa.UUID(), nullable=False),
    sa.Column('decision', sa.Enum('VERIFIED', 'REJECTED', 'FLAGGED', name='verification_decision', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('is_final', sa.Boolean(), nullable=False),
    sa.Column('verified_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.CheckConstraint("decision <> 'FLAGGED' OR is_final = false", name=op.f('ck_verifications_flag_never_final')),
    sa.CheckConstraint("decision = 'FLAGGED' OR is_final = true", name=op.f('ck_verifications_decision_is_final')),
    sa.CheckConstraint("decision = 'VERIFIED' OR (reason IS NOT NULL AND char_length(trim(reason)) > 0)", name=op.f('ck_verifications_reason_required_unless_verified')),
    sa.ForeignKeyConstraint(['report_id'], ['pollution_reports.id'], name=op.f('fk_verifications_report_id_pollution_reports'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['verifier_id'], ['verifiers.user_id'], name=op.f('fk_verifications_verifier_id_verifiers'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_verifications'))
    )
    op.create_index(op.f('ix_verifications_report_id'), 'verifications', ['report_id'], unique=False)
    op.create_index(op.f('ix_verifications_verifier_id'), 'verifications', ['verifier_id'], unique=False)
    op.create_index('ux_verifications_one_final_per_report', 'verifications', ['report_id'], unique=True, postgresql_where=sa.text('is_final'))
    op.create_table('health_linkage_evidence',
    sa.Column('linkage_id', sa.UUID(), nullable=False),
    sa.Column('summary_id', sa.UUID(), nullable=False),
    sa.Column('evidence_window', sa.Enum('BASELINE', 'FOLLOWUP', name='evidence_window', native_enum=False, create_constraint=True), nullable=False),
    sa.ForeignKeyConstraint(['linkage_id'], ['health_linkages.id'], name=op.f('fk_health_linkage_evidence_linkage_id_health_linkages'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['summary_id'], ['clinic_visit_summaries.id'], name=op.f('fk_health_linkage_evidence_summary_id_clinic_visit_summaries'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('linkage_id', 'summary_id', name=op.f('pk_health_linkage_evidence'))
    )
    op.create_table('payouts',
    sa.Column('report_id', sa.UUID(), nullable=False),
    sa.Column('verification_id', sa.UUID(), nullable=False),
    sa.Column('reporter_id', sa.UUID(), nullable=False),
    sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('currency', sa.String(length=3), server_default=sa.text("'KES'"), nullable=False),
    sa.Column('phone_number', sa.String(length=20), nullable=False),
    sa.Column('provider', sa.Enum('MPESA_DARAJA', 'MOCK', name='payout_provider', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('provider_request_id', sa.String(length=100), nullable=True),
    sa.Column('transaction_ref', sa.String(length=100), nullable=True),
    sa.Column('status', sa.Enum('PENDING', 'SUCCESS', 'FAILED', name='payout_status', native_enum=False, create_constraint=True), server_default='PENDING', nullable=False),
    sa.Column('failure_reason', sa.Text(), nullable=True),
    sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("currency ~ '^[A-Z]{3}$'", name=op.f('ck_payouts_currency_iso_code')),
    sa.CheckConstraint("status <> 'SUCCESS' OR (transaction_ref IS NOT NULL AND paid_at IS NOT NULL)", name=op.f('ck_payouts_success_requires_reference')),
    sa.CheckConstraint('amount > 0', name=op.f('ck_payouts_amount_positive')),
    sa.ForeignKeyConstraint(['report_id'], ['pollution_reports.id'], name=op.f('fk_payouts_report_id_pollution_reports'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['reporter_id'], ['reporters.user_id'], name=op.f('fk_payouts_reporter_id_reporters'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['verification_id'], ['verifications.id'], name=op.f('fk_payouts_verification_id_verifications'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_payouts')),
    sa.UniqueConstraint('report_id', name=op.f('uq_payouts_report_id')),
    sa.UniqueConstraint('transaction_ref', name=op.f('uq_payouts_transaction_ref')),
    sa.UniqueConstraint('verification_id', name=op.f('uq_payouts_verification_id'))
    )
    op.create_index(op.f('ix_payouts_reporter_id'), 'payouts', ['reporter_id'], unique=False)
    op.create_index(op.f('ix_payouts_status'), 'payouts', ['status'], unique=False)
    # ### end Alembic commands ###

    for statement in TRIGGER_SQL:
        op.execute(statement)

    settings_table = table(
        "system_settings",
        column("key", sa.String),
        column("value", postgresql.JSONB),
        column("description", sa.Text),
    )
    op.bulk_insert(settings_table, DEFAULT_SETTINGS)


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_payouts_status'), table_name='payouts')
    op.drop_index(op.f('ix_payouts_reporter_id'), table_name='payouts')
    op.drop_table('payouts')
    op.drop_table('health_linkage_evidence')
    op.drop_index('ux_verifications_one_final_per_report', table_name='verifications', postgresql_where=sa.text('is_final'))
    op.drop_index(op.f('ix_verifications_verifier_id'), table_name='verifications')
    op.drop_index(op.f('ix_verifications_report_id'), table_name='verifications')
    op.drop_table('verifications')
    op.drop_index('ix_notifications_user_created', table_name='notifications')
    op.drop_table('notifications')
    op.drop_index(op.f('ix_health_linkages_status'), table_name='health_linkages')
    op.drop_index(op.f('ix_health_linkages_report_id'), table_name='health_linkages')
    op.drop_index(op.f('ix_health_linkages_facility_id'), table_name='health_linkages')
    op.drop_table('health_linkages')
    op.drop_index('ix_clinic_visit_summaries_period', table_name='clinic_visit_summaries')
    op.drop_index(op.f('ix_clinic_visit_summaries_import_batch_id'), table_name='clinic_visit_summaries')
    op.drop_table('clinic_visit_summaries')
    op.drop_index('ix_pollution_reports_status_captured_at', table_name='pollution_reports')
    op.drop_index(op.f('ix_pollution_reports_reporter_id'), table_name='pollution_reports')
    op.drop_index('ix_pollution_reports_location', table_name='pollution_reports', postgresql_using='gist')
    op.drop_index(op.f('ix_pollution_reports_category'), table_name='pollution_reports')
    op.drop_table('pollution_reports')
    op.drop_table('clinic_import_batches')
    op.drop_table('verifiers')
    op.drop_table('system_settings')
    op.drop_table('reporters')
    op.drop_index(op.f('ix_refresh_tokens_user_id'), table_name='refresh_tokens')
    op.drop_table('refresh_tokens')
    op.drop_index('ix_audit_logs_entity', table_name='audit_logs')
    op.drop_index('ix_audit_logs_created_at', table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_actor_id'), table_name='audit_logs')
    op.drop_table('audit_logs')
    op.drop_table('agency_staff')
    op.drop_table('administrators')
    op.drop_table('users')
    op.drop_index('ix_facilities_location', table_name='facilities', postgresql_using='gist')
    op.drop_index(op.f('ix_facilities_area_code'), table_name='facilities')
    op.drop_table('facilities')
    # ### end Alembic commands ###

    for function_name in TRIGGER_FUNCTIONS:
        op.execute(f"DROP FUNCTION IF EXISTS {function_name}() CASCADE")
