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

## Sprint 1 decisions

| # | Topic | Decision |
|---|---|---|
| D19 | Self-registration | `/auth/register` always creates a Community Reporter. Verifier, agency-staff and administrator accounts are created by an administrator (Sprint 4), so nobody can grant themselves permissions. |
| D20 | Login identifier | Phone number (any common format, normalised to E.164) or email. Email is optional for reporters (data minimisation). |
| D21 | Token lifetimes | Access token (JWT, HS256) 15 minutes; refresh token 30 days, stored only as a SHA-256 hash, rotated on every use. Reuse of an old refresh token revokes all of that user's sessions. |
| D22 | Roles at request time | Roles are re-read from the database on every request, so deactivation or role removal applies immediately rather than at token expiry. |
| D23 | Offline-first submission | The app saves every report to its on-device SQLite queue first, then uploads it. Online and offline reports follow the same path, so no report is lost if the app closes mid-upload. |
| D24 | Duplicate prevention | The phone generates `client_report_id` (UUID) at creation. `POST /reports/{client_report_id}/sync` returns the existing report (HTTP 200, `already_received: true`) instead of storing a copy. |
| D25 | Refused reports | A report the server refuses (e.g. older than 30 days) is marked "Needs attention" on the phone and kept until the user retries or deletes it. It is never deleted automatically. |
| D26 | Photo handling | Server verifies the file is a real image, applies EXIF rotation, resizes to 1600 px max, and re-encodes as JPEG with no metadata. Photos are served only through the permission-checked `/reports/{id}/photo` endpoint. |
| D27 | Reporter identity in API | Report responses never include the reporter's id or name. Agency staff can open VERIFIED reports only. |
| D28 | Verifier notifications | Every active verifier (except the reporter) gets an in-app notification for each new report. Zone targeting and push/SMS delivery come in Sprint 3. |
| D29 | Expo SDK | Expo SDK 58 (React Native 0.88), Expo Router with routes in `mobile/src/app`. Works in Expo Go for Sprint 1; a development build is only needed for push notifications (Sprint 3). |
| D30 | Non-reporter mobile users | Until Sprint 3, accounts without the Reporter role see a holding screen in the app. Agency staff and admins use the web dashboard (Sprint 4). |
