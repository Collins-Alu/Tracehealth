# Requirements traceability matrix

Updated at the end of every sprint. "Schema" means the database structure and
DB-level rules exist; "API", "UI" and "Tested" fill in as features are built.

| Req | Requirement | Schema | API | UI | Tested | Evidence |
|---|---|---|---|---|---|---|
| FR 1.1 | Capture report | ✅ S0 | ✅ S1 `POST /reports` | ✅ S1 4-step wizard (photo, GPS, category, details) | ✅ API + mobile | `tests/api/test_reports.py`; `mobile/src/app/new-report.tsx` |
| FR 1.2 | Queue offline reports | ✅ S0 (`client_report_id` unique) | ✅ S1 `POST /reports/{id}/sync` (idempotent) | ✅ S1 SQLite queue, auto-sync on reconnect | ✅ 13 sync-engine tests + API duplicate tests | `mobile/src/offline/__tests__/syncEngine.test.ts`; `test_resending_the_same_report_never_duplicates` |
| FR 2.1 | Confirm report | ✅ S0 | | | ✅ DB rules | self-verification + status triggers |
| FR 2.2 | Reject / flag report | ✅ S0 | | | ✅ DB rules | reason required, flag never final |
| FR 3.1 | Import clinic data | ✅ S0 | | | ✅ DB rules | counts ≥ 0, no duplicate periods, no patient tables |
| FR 3.2 | Correlate reports | ✅ S0 | | | ✅ DB rules | linkages only for VERIFIED reports |
| FR 4.1 | Report map | ✅ S0 (PostGIS) | | | ✅ distance query | `test_distance_between_report_and_facility_in_km` |
| FR 4.2 | Trends | ✅ S0 | | | | |
| FR 5.1 | Trigger payout | ✅ S0 | | | ✅ DB rules | one payout per report; none for rejected |
| NFR 1 | Authenticated RBAC | ✅ S0 (role tables) | ✅ S1 JWT + `require_roles` | ✅ S1 login/register, role routing | ✅ | `tests/api/test_auth.py`; `test_only_reporters_can_submit` |
| NFR 2 | 200 concurrent reporters | | | | | Sprint 5 load test |
| NFR 3 | English + Swahili | ✅ S0 (`preferred_language`) | ✅ S1 notifications in both | ✅ S1 all mobile text | ✅ key-parity tests | `mobile/src/i18n/__tests__/translations.test.ts` (Swahili needs native review, D13) |
| NFR 4 | Auditability | ✅ S0 (append-only) | ✅ S1 register/login/logout/submit audited | | ✅ | `test_audit_log_is_append_only`; `test_submission_is_audited` |
| NFR 5 | Chrome + Edge | | | | | Sprint 4 Playwright |
| NFR 6 | Anonymised clinic data | ✅ S0 | | | ✅ | `test_no_patient_level_table_exists` |
| 5.2 | Safety reminder | | | ✅ S1 on home and photo step | ✅ | `components.test.tsx` (EN + SW) |
| 5.5 | Business rules | ✅ S0 | | | ✅ | verified-only payouts and linkages; no self-verification |

## Added in Sprint 1 (not separate SRS IDs, but required by the master prompt)

| Item | Status | Evidence |
|---|---|---|
| Password hashing (Argon2id) | ✅ | `tests/unit/test_security.py` |
| Refresh-token rotation and theft detection | ✅ | `test_reusing_an_old_refresh_token_ends_all_sessions` |
| Privacy notice consent at registration (D12) | ✅ | `test_invalid_registration_is_rejected`, audit entry |
| Photo metadata (EXIF/GPS) stripped | ✅ | `test_photo_metadata_is_stripped_and_image_resized` |
| Verifiers notified of new reports (B.3 step 6) | ✅ in-app | `test_verifiers_are_notified_but_not_the_reporter` |
| Reporter sees status, rejection reason and payout state | ✅ | `test_my_reports_shows_decision_reason_and_test_payout` |
