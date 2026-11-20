# Requirements traceability matrix

Updated at the end of every sprint. "Schema" means the database structure and
DB-level rules exist; "API", "UI" and "Tested" fill in as features are built.

| Req | Requirement | Schema | API | UI | Tested | Evidence |
|---|---|---|---|---|---|---|
| FR 1.1 | Capture report | ✅ S0 | | | ✅ DB rules | `pollution_reports`; `tests/db/test_business_rules.py` |
| FR 1.2 | Queue offline reports | ✅ S0 (`client_report_id` unique) | | | ✅ duplicate rejection | `test_same_client_report_id_cannot_be_stored_twice` |
| FR 2.1 | Confirm report | ✅ S0 | | | ✅ DB rules | self-verification + status triggers |
| FR 2.2 | Reject / flag report | ✅ S0 | | | ✅ DB rules | reason required, flag never final |
| FR 3.1 | Import clinic data | ✅ S0 | | | ✅ DB rules | counts ≥ 0, no duplicate periods, no patient tables |
| FR 3.2 | Correlate reports | ✅ S0 | | | ✅ DB rules | linkages only for VERIFIED reports |
| FR 4.1 | Report map | ✅ S0 (PostGIS) | | | ✅ distance query | `test_distance_between_report_and_facility_in_km` |
| FR 4.2 | Trends | ✅ S0 | | | | |
| FR 5.1 | Trigger payout | ✅ S0 | | | ✅ DB rules | one payout per report; none for rejected |
| NFR 1 | Authenticated RBAC | ✅ S0 (role tables) | | | | |
| NFR 2 | 200 concurrent reporters | | | | | Sprint 5 load test |
| NFR 3 | English + Swahili | ✅ S0 (`preferred_language`) | | | | |
| NFR 4 | Auditability | ✅ S0 (append-only) | | | ✅ | `test_audit_log_is_append_only` |
| NFR 5 | Chrome + Edge | | | | | Sprint 4 Playwright |
| NFR 6 | Anonymised clinic data | ✅ S0 | | | ✅ | `test_no_patient_level_table_exists` |
| 5.2 | Safety reminder | | | | | Sprint 1 |
| 5.5 | Business rules | ✅ S0 | | | ✅ | verified-only payouts and linkages; no self-verification |
