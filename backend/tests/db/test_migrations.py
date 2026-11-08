"""The migrations build the schema the models describe, and can be reversed."""

from sqlalchemy import inspect

import app.models  # noqa: F401
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from app.db.base import Base

EXPECTED_TABLES = {
    "users",
    "reporters",
    "verifiers",
    "agency_staff",
    "administrators",
    "pollution_reports",
    "verifications",
    "payouts",
    "facilities",
    "clinic_import_batches",
    "clinic_visit_summaries",
    "health_linkages",
    "health_linkage_evidence",
    "audit_logs",
    "notifications",
    "refresh_tokens",
    "system_settings",
}


def _include(obj, name, type_, reflected, compare_to):
    return not (type_ == "table" and name == "spatial_ref_sys")


def test_all_entities_exist(engine):
    tables = set(inspect(engine).get_table_names())
    assert EXPECTED_TABLES <= tables


def test_models_and_migrations_are_in_sync(engine):
    """Fails if someone changes a model without writing a migration."""
    with engine.connect() as conn:
        context = MigrationContext.configure(
            conn, opts={"include_object": _include, "compare_type": True}
        )
        differences = compare_metadata(context, Base.metadata)
    assert differences == []


def test_downgrade_and_upgrade_round_trip(engine, alembic_config):
    command.downgrade(alembic_config, "base")
    assert "users" not in inspect(engine).get_table_names()
    command.upgrade(alembic_config, "head")
    assert EXPECTED_TABLES <= set(inspect(engine).get_table_names())

