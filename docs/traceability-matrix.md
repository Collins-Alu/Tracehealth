# Requirements traceability matrix (final, end of Sprint 4)

Every SRS requirement, where it is implemented, and the test that shows it
works. Test paths are relative to `backend/` unless they start with
`mobile/` or `dashboard/`. Sprint numbers: S0 setup, S1 authentication and
reporting, S2 verification, S3 health analytics and dashboard, S4 incentives
and pilot readiness.

## Functional requirements

| Req | Requirement | Implementation | Tests / evidence |
|---|---|---|---|
| FR 1.1 | Capture a pollution report (photo, GPS, category, description) | S1 `POST /reports`; `report_service.submit_report`; mobile 4-step wizard `mobile/src/app/new-report.tsx` | `tests/integration/test_reports.py`; `test_photo_metadata_is_stripped_and_image_resized`; E2E `dashboard/e2e/lifecycle.spec.ts` step 1 |
| FR 1.2 | Queue reports offline and sync later | S1 SQLite queue + sync engine `mobile/src/offline/`; idempotent `POST /reports/{client_report_id}/sync` | `mobile/src/offline/__tests__/syncEngine.test.ts`; `test_resending_the_same_report_never_duplicates`; DB `test_same_client_report_id_cannot_be_stored_twice` |
| FR 2.1 | Verifier confirms a report | S2 `POST /reports/{id}/verify`; review screens `mobile/src/app/(tabs)/review.tsx`, `review/[id].tsx` | `tests/integration/test_verification.py`; DB `test_reporter_cannot_verify_own_report`, `test_only_one_final_decision_per_report`; E2E lifecycle step 2 |
| FR 2.2 | Verifier rejects or flags with a reason | S2 `/reject`, `/flag`, flagged queue for a second verifier | `test_reject_requires_a_reason_and_never_pays`; `test_flagged_report_needs_a_second_verifier`; `mobile/src/components/__tests__/DecisionPanel.test.tsx` |
| FR 3.1 | Import aggregated clinic data | S3 `POST /clinic-data/import`; `clinic_import_service`; dashboard *Clinic data* page | `tests/integration/test_clinic_import.py` (12 tests incl. `test_patient_columns_reject_the_whole_file`, `test_personal_data_hidden_in_allowed_columns_is_caught`); `dashboard/tests/ClinicImport.test.tsx`; E2E `clinic-import.spec.ts` |
| FR 3.2 | Correlate verified reports with clinic visits | S3 `linkage_engine` + `linkage_stats`; `/health-linkage`, `/health-linkage/trends`, `/health-linkage/compute` | `tests/integration/test_health_linkage.py`; `tests/unit/test_linkage_stats.py`; DB `test_linkage_rejected_for_unverified_report`; method: `docs/health-linkage-method.md` |
| FR 4.1 | Map of verified reports (markers, heatmap, filters) | S3 `/dashboard/reports`, `/dashboard/heatmap`; dashboard *Pollution map* | `test_map_and_heatmap_show_verified_reports_only`; manual check (testing.md) |
| FR 4.2 | Trends: reports vs clinic visits, clusters | S3 `/dashboard/trends`, `/health-linkage/trends`; dashboard *Health trends* and *Overview* | `test_trends_weekly_with_small_counts_hidden`; `test_monthly_counts_are_spread_across_weeks`; `test_overview_counts`; `dashboard/tests/RoleAccess.test.tsx`, `LinkageTable.test.tsx` |
| FR 5.1 | Trigger incentive payout for verified reports | S2 PENDING payout on confirmation; S4 `payout_service.process_payouts`, mock + M-Pesa Daraja B2C adapters, callbacks, retries; dashboard *Payouts*; app reward consent | `tests/integration/test_payouts.py` (13 tests); `tests/unit/test_mpesa_adapter.py`; DB `test_verified_report_can_be_paid_once`, `test_rejected_report_cannot_be_paid`; `dashboard/tests/PayoutsPage.test.tsx`; `mobile/src/components/__tests__/account.test.tsx`; E2E lifecycle steps 3–4 |

## Non-functional requirements

| Req | Requirement | Implementation | Tests / evidence |
|---|---|---|---|
| NFR 1 | Authenticated, role-based access | S1 JWT + refresh rotation, `require_roles`, roles re-read per request; S3 dashboard role guard | `tests/integration/test_auth.py`; `test_dashboard_is_for_agency_staff_and_admins`; `test_admin_area_is_administrators_only`; `dashboard/tests/LoginPage.test.tsx`; E2E `access.spec.ts` |
| NFR 2 | 200 concurrent reporters | S4 Locust scenario `tests/load/locustfile.py`; DB pool sizing and 503 handling (D59) | `docs/testing.md` § Load test: p95 ≤ 61 ms for app requests at 200 users; login burst limitation documented |
| NFR 3 | English and Kiswahili | S1 mobile, S2 notifications, S3 dashboard, S4 language saved to account | `mobile/src/i18n/__tests__/translations.test.ts`; `dashboard/tests/i18n.test.ts`; `test_notifications_are_in_the_reporters_language`. Kiswahili needs native review (D13) |
| NFR 4 | Auditability | Append-only audit log written in the same transaction as each change; dashboard *Audit log* | DB `test_audit_log_is_append_only`; `test_every_decision_is_audited`; `test_audit_log_listing_and_filters`; E2E lifecycle step 5 |
| NFR 5 | Works in Chrome and Edge | S3/S4 Playwright projects `chrome` and `msedge` | `dashboard/playwright.config.ts`; 4 E2E tests pass in Chrome locally; Chrome + Edge in CI (`e2e` job) |
| NFR 6 | Clinic data anonymised and aggregated | S0 schema has no patient table; S3 import allow-list and personal-data detection; small-count suppression | DB `test_no_patient_level_table_exists`; `tests/integration/test_clinic_import.py`; `test_small_counts_are_suppressed_when_listed`; `docs/data-protection.md` |

## Business rules and safety (SRS 5.2, 5.5)

| Rule | Where enforced | Tests |
|---|---|---|
| Safety reminder before taking photos | mobile home and photo step | `mobile/src/components/__tests__/components.test.tsx` (EN + SW) |
| No self-verification | DB trigger + API | `test_reporter_cannot_verify_own_report` (DB and API) |
| Agency staff see verified reports only | API (`list_reports`, dashboard endpoints) + dashboard | `test_search_filters_and_agency_staff_restriction`; E2E `access.spec.ts` |
| One payout per report, never for rejected reports | DB unique index + trigger + service | `test_verified_report_can_be_paid_once`; `test_verifying_pays_once_even_if_triggered_again` |
| No payout without consent | DB constraint + service | `test_payout_phone_requires_consent`; `test_trigger_rejects_unverified_or_unconsented_reports` |
| Linkages only for verified reports | DB trigger + engine | `test_linkage_rejected_for_unverified_report`; `test_unverified_reports_are_never_linked` |
| Association, not causation | every linkage response and page | `test_linkage_endpoints` (notice); `dashboard/tests/RoleAccess.test.tsx` |
| No fabricated results | INSUFFICIENT_DATA has no statistics (DB check) | `test_insufficient_data_linkage_needs_no_statistics`; `test_missing_clinic_data_gives_insufficient_data_without_statistics` |
| Mock payments never shown as real | `MOCK-` references, Test badge | `test_payout_list_masks_phone_numbers_and_flags_test_payments`; `PayoutsPage.test.tsx` |

## Master-prompt items beyond the SRS

| Item | Status | Evidence |
|---|---|---|
| Argon2id passwords, refresh-token rotation and theft detection | ✅ S1 | `tests/unit/test_security.py`; `test_reusing_an_old_refresh_token_ends_all_sessions` |
| Photo metadata stripped | ✅ S1 | `test_photo_metadata_is_stripped_and_image_resized` |
| Push + SMS fallback with mock adapters | ✅ S2 | `tests/unit/test_adapters.py`; `test_failed_push_falls_back_to_sms_and_drops_dead_tokens` |
| Undelivered notifications retried | ✅ S4 | `test_periodic_jobs_send_due_payouts_and_stuck_notifications` |
| User, role, zone and settings administration | ✅ S3 | `tests/integration/test_admin.py` (14 tests) |
| Photo storage local or S3-compatible | ✅ S4 | `tests/unit/test_storage.py` |
| Migrations, seed, Swagger | ✅ | `tests/db/test_migrations.py`, `tests/db/test_seed.py`; `/docs` |
| Deployment instructions | ✅ S4 (not yet run on a real server) | `docs/deployment.md`, `docker-compose.prod.yml`, `infra/caddy/` |
