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
| D16 | Linkage method | Follow-up vs baseline visit-rate ratio with an exact Poisson test; Spearman correlation for area trends; INSUFFICIENT_DATA when coverage is too thin. Full write-up in Sprint 3. |
| D17 | ORM style | Synchronous SQLAlchemy sessions (FastAPI runs them in a thread pool); concurrency target verified by load test in Sprint 4. |
| D18 | Frontend scaffolding | Mobile app scaffolded in Sprint 1 and dashboard in Sprint 3, when each is first used. |

## Sprint 1 decisions

| # | Topic | Decision |
|---|---|---|
| D19 | Self-registration | `/auth/register` always creates a Community Reporter. Verifier, agency-staff and administrator accounts are created by an administrator (Sprint 3), so nobody can grant themselves permissions. |
| D20 | Login identifier | Phone number (any common format, normalised to E.164) or email. Email is optional for reporters (data minimisation). |
| D21 | Token lifetimes | Access token (JWT, HS256) 15 minutes; refresh token 30 days, stored only as a SHA-256 hash, rotated on every use. Reuse of an old refresh token revokes all of that user's sessions. |
| D22 | Roles at request time | Roles are re-read from the database on every request, so deactivation or role removal applies immediately rather than at token expiry. |
| D23 | Offline-first submission | The app saves every report to its on-device SQLite queue first, then uploads it. Online and offline reports follow the same path, so no report is lost if the app closes mid-upload. |
| D24 | Duplicate prevention | The phone generates `client_report_id` (UUID) at creation. `POST /reports/{client_report_id}/sync` returns the existing report (HTTP 200, `already_received: true`) instead of storing a copy. |
| D25 | Refused reports | A report the server refuses (e.g. older than 30 days) is marked "Needs attention" on the phone and kept until the user retries or deletes it. It is never deleted automatically. |
| D26 | Photo handling | Server verifies the file is a real image, applies EXIF rotation, resizes to 1600 px max, and re-encodes as JPEG with no metadata. Photos are served only through the permission-checked `/reports/{id}/photo` endpoint. |
| D27 | Reporter identity in API | Report responses never include the reporter's id or name. Agency staff can open VERIFIED reports only. |
| D28 | Verifier notifications | Every active verifier (except the reporter) gets an in-app notification for each new report. Zone targeting and push/SMS delivery come in Sprint 2. |
| D29 | Expo SDK | Expo SDK 58 (React Native 0.88), Expo Router with routes in `mobile/src/app`. Works in Expo Go for Sprint 1; a development build is only needed for push notifications (Sprint 2). |
| D30 | Non-reporter mobile users | Until Sprint 2, accounts without the Reporter role see a holding screen in the app. Agency staff and admins use the web dashboard (Sprint 3). |

## Sprint 2 decisions (verification)

| # | Topic | Decision |
|---|---|---|
| D31 | Sprint numbering | Sprints are numbered one by one: 0 setup, 1 authentication and reporting, 2 verification, 3 health analytics and dashboard, 4 incentives and pilot readiness. |
| D32 | Verifier zones | A zone is a circle (centre + radius, max 50 km). Each new report gets the nearest active zone that contains it; reports outside every zone are "unassigned" and shown to all verifiers. A verifier's default list is their zone plus unassigned reports; they can switch to any zone or all zones. Zones are seeded for development; administrators manage them from the dashboard in Sprint 3. |
| D33 | Flagged reports (refines D7) | FLAGGED is never final. Any verifier other than the one who flagged it makes the final VERIFIED/REJECTED decision. Administrators can see the flagged queue; deciding requires the Verifier role, so an administrator who should decide is also given a verifier profile. |
| D34 | Decisions need a connection | Verify/reject/flag are never queued offline. Two verifiers could otherwise decide the same report differently without knowing, and the reporter would get conflicting messages. The app says plainly when a decision was not saved. |
| D35 | Simultaneous decisions | The report row is locked while a decision is recorded; the second verifier gets a clear "already decided" (HTTP 409). The database's one-final-decision index is the backstop. |
| D36 | Payout on confirmation | Confirming records a PENDING payout in the same transaction (only if the reporter consented, D4). Nothing is sent or paid until the Sprint 4 adapter processes PENDING payouts. Without consent, the payout is skipped and the reason is written to the audit log. |
| D37 | Notification channels | Every event goes to the in-app inbox. It is also delivered by push when the user has a registered phone. Reporters fall back to SMS when they have no phone registered or push fails. Verifiers never get SMS (cost; they use the app daily). Delivery runs after the HTTP response, and failures are stored with a reason. |
| D38 | Mock adapters | `PUSH_PROVIDER=mock` and `SMS_PROVIDER=mock` are the defaults. Mock deliveries are stored with a `MOCK-` reference so they can never be mistaken for real messages. Real providers: Expo push service, and the Africa's Talking SMS sandbox. |
| D39 | Push in Expo Go | Remote push is not available in Expo Go on Android (since SDK 53). The app detects this and uses the inbox only; push needs a development or release build with an EAS project id. |
| D40 | Who is notified of a new report | Active verifiers assigned to the report's zone, plus verifiers with no zone. The reporter is never notified about their own report, even if they are also a verifier. |
| D41 | Duplicate check | The review screen lists other reports within 250 m and ±7 days of the one being reviewed, with distance and status, to help spot duplicates. |
| D42 | Mobile permissions | The microphone permission that the photo picker adds by default is removed: TraceHealth never records audio (data minimisation). |

### Known limitations after Sprint 2

- A push/SMS delivery queued in the moment before the server stops is left PENDING and not retried automatically. A retry job is planned with the payout processing in Sprint 4.
- Notification messages are stored in the language the user had when the event happened; switching language later does not translate old messages.
