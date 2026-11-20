# Requirements traceability matrix

Updated at the end of every sprint. "Schema" means the database structure and
DB-level rules exist; "API", "UI" and "Tested" fill in as features are built.

| Req | Requirement | Schema | API | UI | Tested | Evidence |
|---|---|---|---|---|---|---|
| FR 1.1 | Capture report | ✅ S0 | ✅ S1 `POST /reports` | ✅ S1 4-step wizard (photo, GPS, category, details) | ✅ API + mobile | `tests/api/test_reports.py`; `mobile/src/app/new-report.tsx` |
| FR 1.2 | Queue offline reports | ✅ S0 (`client_report_id` unique) | ✅ S1 `POST /reports/{id}/sync` (idempotent) | ✅ S1 SQLite queue, auto-sync on reconnect | ✅ 13 sync-engine tests + API duplicate tests | `mobile/src/offline/__tests__/syncEngine.test.ts`; `test_resending_the_same_report_never_duplicates` |
| FR 2.1 | Confirm report | ✅ S0 | ✅ S2 `POST /reports/{id}/verify` | ✅ S2 review screen + confirm prompt | ✅ | `tests/api/test_verification.py` (confirm, payout request, audit, notify) |
| FR 2.2 | Reject / flag report | ✅ S0 | ✅ S2 `/reject`, `/flag` (reason required); flagged queue | ✅ S2 reason form with quick reasons | ✅ API + mobile | `test_reject_requires_a_reason_and_never_pays`; `test_flagged_report_needs_a_second_verifier`; `DecisionPanel.test.tsx` |
| FR 3.1 | Import clinic data | ✅ S0 | | | ✅ DB rules | counts ≥ 0, no duplicate periods, no patient tables |
| FR 3.2 | Correlate reports | ✅ S0 | | | ✅ DB rules | linkages only for VERIFIED reports |
| FR 4.1 | Report map | ✅ S0 (PostGIS) | | | ✅ distance query | `test_distance_between_report_and_facility_in_km` |
| FR 4.2 | Trends | ✅ S0 | | | | |
| FR 5.1 | Trigger payout | ✅ S0 | ⏳ S2 PENDING payout recorded on confirm; sending in S4 | ✅ S1 reporter sees payout status | ✅ request side | `test_confirm_marks_verified_requests_payout_audits_and_notifies`; `test_no_payout_without_consent_but_report_still_verified` |
| NFR 1 | Authenticated RBAC | ✅ S0 (role tables) | ✅ S1 JWT + `require_roles` | ✅ S1 login/register, role routing | ✅ | `tests/api/test_auth.py`; `test_only_reporters_can_submit` |
| NFR 2 | 200 concurrent reporters | | | | | Sprint 4 load test |
| NFR 3 | English + Swahili | ✅ S0 (`preferred_language`) | ✅ S1 notifications in both | ✅ S1 all mobile text | ✅ key-parity tests | `mobile/src/i18n/__tests__/translations.test.ts` (Swahili needs native review, D13) |
| NFR 4 | Auditability | ✅ S0 (append-only) | ✅ S1 auth/submit; S2 every decision, same transaction | | ✅ | `test_every_decision_is_audited`; `test_audit_log_is_append_only` |
| NFR 5 | Chrome + Edge | | | | | Sprint 3 Playwright |
| NFR 6 | Anonymised clinic data | ✅ S0 | | | ✅ | `test_no_patient_level_table_exists` |
| 5.2 | Safety reminder | | | ✅ S1 on home and photo step | ✅ | `components.test.tsx` (EN + SW) |
| 5.5 | Business rules | ✅ S0 | ✅ S2 no self-verification (403), verified-only for agency staff, one payout per report | ✅ S2 explains why a verifier can't decide | ✅ | `test_reporter_cannot_verify_own_report`; `test_confirming_twice_creates_one_payout`; `test_search_filters_and_agency_staff_restriction` |

## Added in Sprint 1 (not separate SRS IDs, but required by the master prompt)

| Item | Status | Evidence |
|---|---|---|
| Password hashing (Argon2id) | ✅ | `tests/unit/test_security.py` |
| Refresh-token rotation and theft detection | ✅ | `test_reusing_an_old_refresh_token_ends_all_sessions` |
| Privacy notice consent at registration (D12) | ✅ | `test_invalid_registration_is_rejected`, audit entry |
| Photo metadata (EXIF/GPS) stripped | ✅ | `test_photo_metadata_is_stripped_and_image_resized` |
| Verifiers notified of new reports (B.3 step 6) | ✅ in-app | `test_verifiers_are_notified_but_not_the_reporter` |
| Reporter sees status, rejection reason and payout state | ✅ | `test_my_reports_shows_decision_reason_and_test_payout` |

## Added in Sprint 2

| Item | Status | Evidence |
|---|---|---|
| Verifier: view pending reports, filter by zone (UML B.4 steps 1-2) | ✅ | `test_pending_queue_defaults_to_my_zone_plus_unassigned`; `mobile/src/app/(tabs)/review.tsx` |
| Verifier: inspect photo, location, category, description, time | ✅ | `mobile/src/app/review/[id].tsx` |
| Flagged reports reviewed by a second verifier (D33) | ✅ | `test_flagged_queue_shows_who_may_decide` |
| Duplicate check: nearby reports (D41) | ✅ | `test_nearby_reports_help_spot_duplicates` |
| Simultaneous decisions handled (D35) | ✅ | `test_final_decisions_cannot_be_changed`; row lock in `verification_service.decide` |
| Reporter notified of verification/rejection/flag with reason (B.4 steps 9, 12) | ✅ in-app; push and SMS via adapters | `test_inbox_lists_marks_read_and_counts_unread`; `test_reporter_with_a_phone_registered_gets_push_not_sms` |
| Verifiers notified of new reports in their zone (B.3 step 6) | ✅ | `test_new_report_alerts_only_verifiers_for_that_zone` |
| SMS fallback where push is unavailable (SRS 3.4) | ✅ mock + Africa's Talking sandbox adapter | `test_failed_push_falls_back_to_sms_and_drops_dead_tokens`; `tests/unit/test_adapters.py` |
| Notifications in English and Swahili | ✅ | `test_notifications_are_in_the_reporters_language` |
