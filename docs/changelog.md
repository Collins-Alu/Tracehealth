# Changelog

What each sprint delivered and which files it added or changed. File lists are
paths from the repository root. "Changed" means a file from an earlier sprint
that was edited.

## Sprint 4: incentives and pilot readiness

**Delivered**

- Payouts sent through payment adapters: clearly labelled MOCK (default) and
  Safaricom M-Pesa Daraja B2C (sandbox-ready), with result callbacks, retries
  with backoff, no automatic retry when the outcome is unknown, expiry of
  requests with no result, and administrator retry (D52–D55).
- Payout notifications to reporters (in-app, push, SMS fallback) in English
  and Kiswahili; periodic jobs also retry stuck notifications.
- Dashboard *Payouts* page; reporters manage reward consent and M-Pesa number
  in the app; app language saved to the account (D57, D58).
- Photo storage on local disk or S3-compatible object storage.
- Load test for 200 concurrent reporters; database pool fix and 503 handling
  found by it (D59).
- Playwright end-to-end tests (Chrome locally, Chrome + Edge in CI).
- Production deployment: Dockerfile, jobs process, Caddy with HTTPS and the
  built dashboard, production compose file and environment template (D56, D60).
- Final documentation: architecture, API, data protection, deployment,
  testing, user guide, as-built UML, final traceability matrix, this changelog.

**Added (48)**

- `.env.production.example`
- `backend/.dockerignore`
- `backend/Dockerfile`
- `backend/app/api/routes/payouts.py`
- `backend/app/core/background.py`
- `backend/app/integrations/payments/__init__.py`
- `backend/app/integrations/payments/base.py`
- `backend/app/integrations/payments/mock.py`
- `backend/app/integrations/payments/mpesa_daraja.py`
- `backend/app/schemas/payout.py`
- `backend/app/storage/__init__.py`
- `backend/app/storage/base.py`
- `backend/app/storage/local.py`
- `backend/app/storage/s3_compatible.py`
- `backend/requirements-load.txt`
- `backend/scripts/run_jobs.py`
- `backend/tests/integration/test_payouts.py`
- `backend/tests/load/locustfile.py`
- `backend/tests/unit/test_mpesa_adapter.py`
- `backend/tests/unit/test_storage.py`
- `dashboard/e2e/access.spec.ts`
- `dashboard/e2e/clinic-import.spec.ts`
- `dashboard/e2e/fixtures/synthetic-photo.jpg`
- `dashboard/e2e/fixtures/with-patient-column.csv`
- `dashboard/e2e/helpers.ts`
- `dashboard/e2e/lifecycle.spec.ts`
- `dashboard/playwright.config.ts`
- `dashboard/src/features/payouts/PayoutsPage.tsx`
- `dashboard/tests/PayoutsPage.test.tsx`
- `docker-compose.prod.yml`
- `docs/api.md`
- `docs/architecture.md`
- `docs/changelog.md`
- `docs/data-protection.md`
- `docs/deployment.md`
- `docs/testing.md`
- `docs/uml/README.md`
- `docs/uml/b3-submit-report.md`
- `docs/uml/b4-verify-report.md`
- `docs/uml/b5-health-linkage.md`
- `docs/uml/b6-payout.md`
- `docs/uml/class-diagram.md`
- `docs/uml/states.md`
- `docs/user-guide.md`
- `infra/caddy/Caddyfile`
- `infra/caddy/Dockerfile`
- `mobile/src/components/PayoutSettings.tsx`
- `mobile/src/components/__tests__/account.test.tsx`

**Changed (34)**

- `.env.example`
- `.github/workflows/ci.yml`
- `.gitignore`
- `README.md`
- `backend/alembic/versions/0003_payout_attempts_import_summary_linkage_coverage.py`
- `backend/app/api/routes/admin.py`
- `backend/app/api/routes/auth.py`
- `backend/app/api/routes/verification.py`
- `backend/app/core/config.py`
- `backend/app/db/session.py`
- `backend/app/main.py`
- `backend/app/models/payout.py`
- `backend/app/schemas/auth.py`
- `backend/app/services/auth_service.py`
- `backend/app/services/notification_service.py`
- `backend/app/services/payout_service.py`
- `backend/app/services/photo_storage.py`
- `backend/app/services/setting_service.py`
- `backend/requirements.txt`
- `backend/scripts/seed.py`
- `backend/tests/conftest.py`
- `backend/tests/integration/test_admin.py`
- `backend/tests/unit/test_phone_and_tokens.py`
- `docs/decisions.md`
- `docs/traceability-matrix.md`
- `mobile/src/api/auth.ts`
- `mobile/src/api/types.ts`
- `mobile/src/app/(tabs)/account.tsx`
- `mobile/src/auth/AuthContext.tsx`
- `mobile/src/components/LanguageToggle.tsx`
- `mobile/src/i18n/en.json`
- `mobile/src/i18n/sw.json`
- `mobile/src/notifications/__tests__/notifications.test.ts`
- `mobile/src/notifications/routing.ts`

## Sprint 3: health analytics and dashboard

**Delivered**

- Clinic data import (all-or-nothing CSV, personal-data detection, template,
  history) (D46).
- Health-linkage engine: radius search, exact Poisson rate test, Spearman
  correlation, INSUFFICIENT_DATA, evidence and parameter snapshots, automatic
  recalculation (D43–D45).
- Dashboard API: overview, map points, heatmap, weekly trends with small-count
  suppression; linkage results and clusters.
- Administration API: users and roles, audit log, settings with validation,
  verifier zones (D50, D51).
- Web dashboard (React): sign-in, overview, pollution map with heatmap, health
  trends, reports, clinic data, users, audit log, settings; English and
  Kiswahili (D47–D49).
- Migration 0003; backend tests moved from `backend/tests/api/` to
  `backend/tests/integration/` to match the planned folder structure.

**Added (73)**

- `backend/alembic/versions/0003_payout_attempts_import_summary_linkage_coverage.py`
- `backend/app/api/routes/admin.py`
- `backend/app/api/routes/clinic_data.py`
- `backend/app/api/routes/dashboard.py`
- `backend/app/api/routes/health_linkage.py`
- `backend/app/schemas/admin.py`
- `backend/app/schemas/clinic.py`
- `backend/app/schemas/dashboard.py`
- `backend/app/services/clinic_import_service.py`
- `backend/app/services/linkage_engine.py`
- `backend/app/services/linkage_stats.py`
- `backend/app/services/settings_rules.py`
- `backend/tests/integration/test_admin.py`
- `backend/tests/integration/test_clinic_import.py`
- `backend/tests/integration/test_dashboard.py`
- `backend/tests/integration/test_health_linkage.py`
- `backend/tests/unit/test_linkage_stats.py`
- `dashboard/.env.example`
- `dashboard/.gitignore`
- `dashboard/index.html`
- `dashboard/package-lock.json`
- `dashboard/package.json`
- `dashboard/public/favicon.svg`
- `dashboard/src/App.tsx`
- `dashboard/src/api/client.ts`
- `dashboard/src/api/endpoints.ts`
- `dashboard/src/auth/AuthContext.tsx`
- `dashboard/src/components/Dialog.tsx`
- `dashboard/src/components/Filters.tsx`
- `dashboard/src/components/LanguageSwitch.tsx`
- `dashboard/src/components/Layout.tsx`
- `dashboard/src/components/PageHeader.tsx`
- `dashboard/src/components/Pagination.tsx`
- `dashboard/src/components/Pill.tsx`
- `dashboard/src/components/ReportPhoto.tsx`
- `dashboard/src/components/State.tsx`
- `dashboard/src/features/audit/AuditPage.tsx`
- `dashboard/src/features/auth/LoginPage.tsx`
- `dashboard/src/features/clinic-import/ClinicImportPage.tsx`
- `dashboard/src/features/map/HeatLayer.tsx`
- `dashboard/src/features/map/MapPage.tsx`
- `dashboard/src/features/overview/OverviewPage.tsx`
- `dashboard/src/features/reports/ReportDetail.tsx`
- `dashboard/src/features/reports/ReportsPage.tsx`
- `dashboard/src/features/settings/SettingsPage.tsx`
- `dashboard/src/features/settings/ZonesSection.tsx`
- `dashboard/src/features/trends/LinkageTable.tsx`
- `dashboard/src/features/trends/TrendsPage.tsx`
- `dashboard/src/features/users/UserDialog.tsx`
- `dashboard/src/features/users/UsersPage.tsx`
- `dashboard/src/i18n/en.json`
- `dashboard/src/i18n/index.ts`
- `dashboard/src/i18n/sw.json`
- `dashboard/src/index.css`
- `dashboard/src/lib/categories.ts`
- `dashboard/src/lib/format.ts`
- `dashboard/src/lib/leafletGlobal.ts`
- `dashboard/src/main.tsx`
- `dashboard/src/types/api.ts`
- `dashboard/src/vite-env.d.ts`
- `dashboard/tests/ClinicImport.test.tsx`
- `dashboard/tests/LinkageTable.test.tsx`
- `dashboard/tests/LoginPage.test.tsx`
- `dashboard/tests/RoleAccess.test.tsx`
- `dashboard/tests/format.test.ts`
- `dashboard/tests/helpers.tsx`
- `dashboard/tests/i18n.test.ts`
- `dashboard/tests/setup.ts`
- `dashboard/tsconfig.app.json`
- `dashboard/tsconfig.json`
- `dashboard/tsconfig.node.json`
- `dashboard/vite.config.ts`
- `docs/health-linkage-method.md`

**Moved** (same tests, new folder)

- `backend/tests/api/__init__.py → backend/tests/integration/__init__.py`
- `backend/tests/api/test_auth.py → backend/tests/integration/test_auth.py`
- `backend/tests/api/test_health.py → backend/tests/integration/test_health.py`
- `backend/tests/api/test_notifications.py → backend/tests/integration/test_notifications.py`
- `backend/tests/api/test_reports.py → backend/tests/integration/test_reports.py`
- `backend/tests/api/test_verification.py → backend/tests/integration/test_verification.py`

**Changed (12)**

- `.env.example`
- `.gitignore`
- `backend/app/api/routes/reports.py`
- `backend/app/api/routes/verification.py`
- `backend/app/core/config.py`
- `backend/app/main.py`
- `backend/app/models/clinic.py`
- `backend/app/models/health_linkage.py`
- `backend/app/services/setting_service.py`
- `backend/requirements.txt`
- `backend/scripts/seed.py`
- `backend/tests/conftest.py`

## Sprint 2: verification

**Delivered:** verifier review screens with zone filter, confirm / reject /
flag with reasons, second review of flagged reports, duplicate check, audit
log, PENDING payout on confirmation, notifications (inbox, push, SMS fallback)
with mock, Expo and Africa's Talking adapters, migration 0002.

**Added (46)**

- `backend/alembic/versions/0002_zones_push_tokens_notification_delivery.py`
- `backend/app/api/routes/notifications.py`
- `backend/app/api/routes/verification.py`
- `backend/app/core/notifications.py`
- `backend/app/integrations/__init__.py`
- `backend/app/integrations/push/__init__.py`
- `backend/app/integrations/push/base.py`
- `backend/app/integrations/push/expo.py`
- `backend/app/integrations/push/mock.py`
- `backend/app/integrations/sms/__init__.py`
- `backend/app/integrations/sms/africastalking.py`
- `backend/app/integrations/sms/base.py`
- `backend/app/integrations/sms/mock.py`
- `backend/app/models/device.py`
- `backend/app/models/zone.py`
- `backend/app/schemas/notification.py`
- `backend/app/services/notification_dispatch.py`
- `backend/app/services/payout_service.py`
- `backend/app/services/setting_service.py`
- `backend/app/services/verification_service.py`
- `backend/app/services/zone_service.py`
- `backend/tests/api/test_notifications.py`
- `backend/tests/api/test_verification.py`
- `backend/tests/unit/test_adapters.py`
- `mobile/eas.json`
- `mobile/src/api/notifications.ts`
- `mobile/src/api/verification.ts`
- `mobile/src/app/(tabs)/_layout.tsx`
- `mobile/src/app/(tabs)/account.tsx`
- `mobile/src/app/(tabs)/home.tsx`
- `mobile/src/app/(tabs)/inbox.tsx`
- `mobile/src/app/(tabs)/reports.tsx`
- `mobile/src/app/(tabs)/review.tsx`
- `mobile/src/app/other-roles.tsx`
- `mobile/src/app/review/[id].tsx`
- `mobile/src/components/AuthImage.tsx`
- `mobile/src/components/ChipRow.tsx`
- `mobile/src/components/DecisionPanel.tsx`
- `mobile/src/components/__tests__/DecisionPanel.test.tsx`
- `mobile/src/notifications/InboxContext.tsx`
- `mobile/src/notifications/__tests__/notifications.test.ts`
- `mobile/src/notifications/push.ts`
- `mobile/src/notifications/pushSupport.ts`
- `mobile/src/notifications/routing.ts`
- `mobile/src/review/__tests__/decision.test.ts`
- `mobile/src/review/decision.ts`

**Changed (29)**

- `.env.example`
- `README.md`
- `backend/app/api/routes/reports.py`
- `backend/app/core/config.py`
- `backend/app/db/session.py`
- `backend/app/main.py`
- `backend/app/models/__init__.py`
- `backend/app/models/health_linkage.py`
- `backend/app/models/notification.py`
- `backend/app/models/report.py`
- `backend/app/models/user.py`
- `backend/app/schemas/report.py`
- `backend/app/services/notification_service.py`
- `backend/app/services/report_service.py`
- `backend/scripts/seed.py`
- `backend/tests/api/test_auth.py`
- `backend/tests/conftest.py`
- `backend/tests/factories.py`
- `docs/decisions.md`
- `docs/traceability-matrix.md`
- `mobile/app.json`
- `mobile/package-lock.json`
- `mobile/package.json`
- `mobile/src/api/types.ts`
- `mobile/src/app/_layout.tsx`
- `mobile/src/app/index.tsx`
- `mobile/src/auth/AuthContext.tsx`
- `mobile/src/i18n/en.json`
- `mobile/src/i18n/sw.json`

**Removed (4)**

- `mobile/src/app/(reporter)/_layout.tsx`
- `mobile/src/app/(reporter)/home.tsx`
- `mobile/src/app/(reporter)/reports.tsx`
- `mobile/src/app/verifier.tsx`

## Sprint 1: authentication and reporting

**Delivered:** registration and login (Argon2id, JWT, refresh rotation),
role-based access, report submission with photo cleaning, offline queue and
idempotent sync on the phone, reporter's report list, Expo mobile app in
English and Kiswahili.

**Added (76)**

- `backend/app/api/routes/__init__.py`
- `backend/app/api/routes/auth.py`
- `backend/app/api/routes/reports.py`
- `backend/app/core/deps.py`
- `backend/app/core/phone.py`
- `backend/app/schemas/__init__.py`
- `backend/app/schemas/auth.py`
- `backend/app/schemas/report.py`
- `backend/app/services/__init__.py`
- `backend/app/services/audit_service.py`
- `backend/app/services/auth_service.py`
- `backend/app/services/notification_service.py`
- `backend/app/services/photo_storage.py`
- `backend/app/services/report_service.py`
- `backend/tests/api/test_auth.py`
- `backend/tests/api/test_reports.py`
- `backend/tests/photos.py`
- `backend/tests/unit/test_phone_and_tokens.py`
- `mobile/.env.example`
- `mobile/.gitignore`
- `mobile/app.json`
- `mobile/assets/android-icon-background.png`
- `mobile/assets/android-icon-foreground.png`
- `mobile/assets/android-icon-monochrome.png`
- `mobile/assets/favicon.png`
- `mobile/assets/icon.png`
- `mobile/assets/splash-icon.png`
- `mobile/package-lock.json`
- `mobile/package.json`
- `mobile/src/api/__tests__/client.test.ts`
- `mobile/src/api/auth.ts`
- `mobile/src/api/client.ts`
- `mobile/src/api/index.ts`
- `mobile/src/api/reports.ts`
- `mobile/src/api/types.ts`
- `mobile/src/app/(reporter)/_layout.tsx`
- `mobile/src/app/(reporter)/home.tsx`
- `mobile/src/app/(reporter)/reports.tsx`
- `mobile/src/app/_layout.tsx`
- `mobile/src/app/index.tsx`
- `mobile/src/app/login.tsx`
- `mobile/src/app/new-report.tsx`
- `mobile/src/app/register.tsx`
- `mobile/src/app/report/[id].tsx`
- `mobile/src/app/submitted.tsx`
- `mobile/src/app/verifier.tsx`
- `mobile/src/app/welcome.tsx`
- `mobile/src/auth/AuthContext.tsx`
- `mobile/src/auth/tokenStore.ts`
- `mobile/src/components/Button.tsx`
- `mobile/src/components/CategoryPicker.tsx`
- `mobile/src/components/LanguageToggle.tsx`
- `mobile/src/components/Message.tsx`
- `mobile/src/components/OfflineBanner.tsx`
- `mobile/src/components/SafetyNotice.tsx`
- `mobile/src/components/Screen.tsx`
- `mobile/src/components/StatusBadge.tsx`
- `mobile/src/components/TextField.tsx`
- `mobile/src/components/__tests__/components.test.tsx`
- `mobile/src/config.ts`
- `mobile/src/i18n/__tests__/translations.test.ts`
- `mobile/src/i18n/en.json`
- `mobile/src/i18n/index.ts`
- `mobile/src/i18n/sw.json`
- `mobile/src/offline/SyncContext.tsx`
- `mobile/src/offline/__tests__/helpers/memoryQueueStore.ts`
- `mobile/src/offline/__tests__/syncEngine.test.ts`
- `mobile/src/offline/photoStore.ts`
- `mobile/src/offline/sqliteQueueStore.ts`
- `mobile/src/offline/syncEngine.ts`
- `mobile/src/offline/types.ts`
- `mobile/src/offline/useOptionalSync.ts`
- `mobile/src/theme.ts`
- `mobile/src/utils/errors.ts`
- `mobile/src/utils/format.ts`
- `mobile/tsconfig.json`

**Changed (12)**

- `.env.example`
- `.github/workflows/ci.yml`
- `README.md`
- `backend/app/core/config.py`
- `backend/app/core/security.py`
- `backend/app/main.py`
- `backend/requirements.txt`
- `backend/scripts/seed.py`
- `backend/tests/conftest.py`
- `backend/tests/factories.py`
- `docs/decisions.md`
- `docs/traceability-matrix.md`

## Sprint 0: setup

**Delivered:** repository structure, PostgreSQL + PostGIS in Docker, all
entities and business-rule constraints/triggers (migration 0001), default
settings, synthetic seed data, health check, CI, decisions and traceability
matrix.

**Added (54)**

- `.env.example`
- `.gitattributes`
- `.github/workflows/ci.yml`
- `.gitignore`
- `.vscode/extensions.json`
- `.vscode/settings.json`
- `README.md`
- `backend/alembic.ini`
- `backend/alembic/env.py`
- `backend/alembic/script.py.mako`
- `backend/alembic/versions/0001_initial_schema.py`
- `backend/app/__init__.py`
- `backend/app/api/__init__.py`
- `backend/app/api/health.py`
- `backend/app/core/__init__.py`
- `backend/app/core/config.py`
- `backend/app/core/security.py`
- `backend/app/db/__init__.py`
- `backend/app/db/base.py`
- `backend/app/db/session.py`
- `backend/app/main.py`
- `backend/app/models/__init__.py`
- `backend/app/models/audit.py`
- `backend/app/models/auth_token.py`
- `backend/app/models/clinic.py`
- `backend/app/models/enums.py`
- `backend/app/models/geo.py`
- `backend/app/models/health_linkage.py`
- `backend/app/models/mixins.py`
- `backend/app/models/notification.py`
- `backend/app/models/payout.py`
- `backend/app/models/report.py`
- `backend/app/models/setting.py`
- `backend/app/models/user.py`
- `backend/app/models/verification.py`
- `backend/pyproject.toml`
- `backend/requirements.txt`
- `backend/scripts/__init__.py`
- `backend/scripts/seed.py`
- `backend/tests/__init__.py`
- `backend/tests/api/__init__.py`
- `backend/tests/api/test_health.py`
- `backend/tests/conftest.py`
- `backend/tests/db/__init__.py`
- `backend/tests/db/test_business_rules.py`
- `backend/tests/db/test_migrations.py`
- `backend/tests/db/test_seed.py`
- `backend/tests/factories.py`
- `backend/tests/unit/__init__.py`
- `backend/tests/unit/test_security.py`
- `docker-compose.yml`
- `docs/decisions.md`
- `docs/traceability-matrix.md`
- `infra/postgres/init/20-create-test-db.sql`
