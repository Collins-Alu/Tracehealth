# Data protection

TraceHealth handles three kinds of data: community members' accounts and
reports, aggregated clinic visit counts, and mobile-money payout details. This
page lists what is collected, why, who can see it, and how it is protected, so
the pilot partner and the data protection officer can review it against the
Kenya Data Protection Act, 2019 (DPA). It describes the system as built; it is
not legal advice, and the pilot needs the partner's own DPA review (and
registration with the ODPC where required) before real data is used.

## What is collected

| Data | From | Why | Kept as |
|---|---|---|---|
| Name, phone number, optional email, password | reporter at registration | log in, send notifications | password as an Argon2id hash only |
| Preferred language | user | messages in English or Kiswahili | |
| Privacy-notice consent | reporter at registration | lawful basis, recorded in the audit log | timestamp |
| Pollution report: photo, GPS position, category, description, time | reporter | the core evidence | photo re-encoded without metadata |
| Payout phone and consent time | reporter, only after opting in | send rewards by M-Pesa (D4) | database constraint: no payout phone without a consent time |
| Verification decisions and reasons | verifier | accountability | append-only audit log |
| Clinic visit counts per clinic, condition and week/month | partner clinic (administrator upload) | health linkage | **aggregated counts only** |
| Push token | phone, if the user allows notifications | phone alerts | removed on logout or when Expo reports it invalid |

**Not collected:** patient names, ages, sex, diagnoses of individuals, ID
numbers, or any record about a single patient. The database has no table
that could hold one (checked by `test_no_patient_level_table_exists`).
The app never records audio (microphone permission removed, D42).

## Clinic data: aggregated only

The CSV importer (`clinic_import_service.py`) is the only way clinic data gets
in, and it refuses a file **as a whole**, storing nothing, if:

- any column is not on the allow-list (`facility_code`, `facility_name`,
  `area_code`, `latitude`, `longitude`, `condition_category`, `period_start`,
  `period_end`, `visit_count`);
- a column name suggests personal data (patient, name, dob, birth, age, sex,
  gender, phone, mobile, email, id number…). The message says why;
- a cell contains something that looks like a phone number or email address;
- a period is longer than 31 days, counts are negative, or rows repeat.

Small counts can still identify people in a small community. Counts below
`dashboard.small_count_threshold` (default 5) are stored but never sent to the
dashboard: the API returns them as hidden and the charts show a gap with a
note (D11).

## Who can see what

| | Reporter | Verifier | Agency staff | Administrator |
|---|---|---|---|---|
| Own reports, status, reward | ✅ | | | |
| Pending/flagged reports and photos | | ✅ (not their own) | | ✅ |
| Verified reports, map, trends, linkages | | | ✅ | ✅ |
| Rejected / pending reports | | ✅ | ❌ (API returns verified only) | ✅ |
| Reporter's name or phone on a report | ❌ | ❌ | ❌ | payouts page only, phone masked (`+2547****678`) |
| Clinic visit counts | | | aggregated, small counts hidden | same |
| Users, audit log, settings, payouts | | | | ✅ |

- Report responses never include who submitted the report (D27).
- Photos are served only through `/reports/{id}/photo`, which applies the same
  permission check as the report itself; there are no public photo URLs.
- A verifier cannot see or decide their own reports (database trigger + API).

## Photos

On upload the server checks that the file really is an image, applies the
camera's rotation, shrinks it to at most 1600 px and re-encodes it as JPEG
**without any metadata**: GPS tags, camera model and timestamps embedded by
the phone are removed (`test_photo_metadata_is_stripped_and_image_resized`).
The report's location comes only from the separate location field the reporter
saw and confirmed in the app.

Note: reports are about places, but a photo can still show faces, number
plates or homes. The app's safety reminder asks reporters to photograph from a
safe distance; before the pilot, add "photograph the pollution, not people" to
the reporter guidance and the verifier training, and have verifiers reject
photos that clearly identify a person.

## Security measures

- HTTPS in production (Caddy with automatic certificates, HSTS) (D14).
- Passwords hashed with Argon2id; short-lived access tokens (15 min); refresh
  tokens stored hashed, rotated on each use, with theft detection (D21).
- Roles re-checked on every request; deactivating a user revokes their sessions.
- The dashboard keeps tokens in `sessionStorage` (cleared when the tab closes),
  sends a strict Content-Security-Policy, and forbids framing.
- Mobile tokens live in the phone's secure storage (Keychain / Keystore).
- Secrets only in environment variables, never in Git (`.env*` ignored).
- Business rules enforced in the database as well as the API: no
  self-verification, one payout per report, no payout without consent,
  linkages only for verified reports, append-only audit log.
- Every decision, import, setting change, role change and payout attempt is
  written to the audit log in the same transaction as the change.

## Data subject rights (what the system supports today)

| Right | Support |
|---|---|
| Information | Privacy notice shown and accepted at registration (text to be finalised with the partner). |
| Access | Reporters see their reports, decisions and rewards in the app. A full export is done by an administrator on request (manual, via SQL). |
| Correction | Users change their name, language and payout number in the app; administrators can correct accounts. |
| Withdraw payout consent | Account tab → "Rewards by mobile money" → off. The payout number is deleted immediately. |
| Deletion | An administrator deactivates the account (immediate). Full erasure of reports is a manual procedure because verified reports feed published statistics; agree the approach with the partner. |

## Retention (to be agreed before the pilot)

The system does not yet delete data automatically. Suggested starting point
for the partner to approve:

- Rejected reports and their photos: delete after 90 days.
- Photos of verified reports: keep for the pilot plus 12 months, then delete
  the photo and keep the report record.
- Audit log: keep for the pilot plus 24 months.
- Deactivated accounts: anonymise after 12 months.

## Mock data and test payments

All development data is synthetic and labelled so (facility names end in
"(SYNTHETIC)", photos say "SYNTHETIC SEED PHOTO"). Mock payouts and messages
carry `MOCK-` references and a **Test** badge everywhere they appear. They are
never presented as real payments or real health data.

## If something goes wrong

If personal data may have been exposed (lost laptop with a database copy,
leaked secret, unauthorised access in the audit log): rotate `JWT_SECRET_KEY`
(logs everyone out), rotate database and provider credentials, deactivate
affected accounts, preserve the audit log, and inform the partner's data
protection officer at once. Under the DPA, the ODPC must be notified within
72 hours of becoming aware of a breach that poses a real risk to people.
