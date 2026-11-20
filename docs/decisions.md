# Approved design decisions

Decisions agreed before implementation (plan approved on 3 Nov 2026). Where the
SRS was silent, these defaults were proposed and accepted.

| # | Topic | Decision |
|---|---|---|
| D1 | Roles | Role profile tables keyed by user id; one person may hold several roles (e.g. reporter + verifier). |
| D2 | Mobile money | Safaricom M-Pesa Daraja B2C sandbox; a clearly labelled MOCK adapter is the default until credentials exist. |
| D3 | Incentive amount | Configurable setting `payout.amount`, default KES 50 per verified report. |
| D4 | Payout phone | Registration phone by default, editable; stored only after explicit payout consent (DB constraint). |
| D5 | SMS fallback | Africa's Talking sandbox; mock adapter by default. |
| D6 | Photo storage | Local disk in development; S3-compatible adapter for deployment. EXIF metadata stripped on upload. |
| D7 | Flag review | A FLAGGED decision is never final; an admin or second verifier later records the final VERIFIED/REJECTED decision. |
| D8 | Public dashboard | No anonymous public view in v1; the dashboard is login-only for agency staff and administrators. |
| D9 | Category mapping | OPEN_BURNING→RESPIRATORY; ILLEGAL_DUMPING→SKIN, DIARRHOEAL; BLOCKED_DRAINAGE→DIARRHOEAL, MALARIA; MEDICAL_WASTE→INJURY, INFECTION. Editable; to be confirmed with the partner clinic. |
| D10 | Clinic cadence | Weekly and monthly periods accepted; analysis defaults to weekly. |
| D11 | Small counts | Counts below 5 are stored but shown as "<5" on the dashboard. |
| D12 | Reporter privacy | EXIF stripping, reporter identity hidden from agency staff, privacy notice and consent at registration. |
| D13 | Swahili | Translations drafted by the developer; native-speaker review before the pilot. |
| D14 | HTTPS | HTTP locally; TLS via a reverse proxy (e.g. Caddy) in deployment. |
| D15 | Database extras | PostGIS for distance queries; business rules enforced by DB constraints and triggers as well as in the API. |
| D16 | Linkage method | Follow-up vs baseline visit-rate ratio with an exact Poisson test; Spearman correlation for area trends; INSUFFICIENT_DATA when coverage is too thin. Full write-up in Sprint 4. |
| D17 | ORM style | Synchronous SQLAlchemy sessions (FastAPI runs them in a thread pool); concurrency target verified by load test in Sprint 5. |
| D18 | Frontend scaffolding | Mobile app scaffolded in Sprint 1 and dashboard in Sprint 4, when each is first used. |
