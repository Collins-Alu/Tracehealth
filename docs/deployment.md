# Deployment

This guide puts TraceHealth on one Linux server for the pilot: PostgreSQL +
PostGIS, the API, a jobs process and Caddy (HTTPS and the dashboard), all with
Docker Compose. One server with 2 vCPU, 4 GB RAM and 40 GB disk is enough for
the pilot. The mobile app is built separately with Expo EAS.

> **Tested so far:** the backend image's contents, the jobs runner, the
> Caddyfile (`caddy validate`) and the compose file (`docker compose config`)
> were checked in development. A full `docker compose up` on a real server has
> **not** been run yet; do it on a staging server first and work through the
> checklist at the end.

## 1. Prepare the server

1. Ubuntu 24.04 LTS (or similar) with Docker Engine and the Compose plugin
   (https://docs.docker.com/engine/install/).
2. Two DNS A records pointing at the server's public IP, for example
   `api.tracehealth.example` and `dashboard.tracehealth.example`.
3. Firewall: allow 22 (SSH), 80 and 443 only. PostgreSQL is not published.

## 2. Configure

```bash
git clone <your repository> tracehealth && cd tracehealth
cp .env.production.example .env.production
nano .env.production
```

Fill in the two domains, `ACME_EMAIL`, and generate **different** long random
values for `POSTGRES_PASSWORD`, `JWT_SECRET_KEY` (and later
`MPESA_CALLBACK_TOKEN`):

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Keep `PUSH_PROVIDER=mock`, `SMS_PROVIDER=mock` and `PAYOUT_PROVIDER=MOCK` for
the first start. `.env.production` must never be committed (it is in
`.gitignore`).

## 3. Start

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
docker compose --env-file .env.production -f docker-compose.prod.yml ps
```

What happens:

- `db` starts and becomes healthy.
- `migrate` runs `alembic upgrade head` once and exits.
- `api` starts 4 workers (background jobs off).
- `jobs` runs `python -m scripts.run_jobs` (payouts, retries) – one copy only.
- `caddy` builds the dashboard with `VITE_API_URL=https://<API_DOMAIN>`, gets
  certificates from Let's Encrypt, and serves both sites.

Check: `https://<API_DOMAIN>/health` shows `"database": "ok"`, and the dashboard
opens at `https://<DASHBOARD_DOMAIN>`.

Swagger stays available at `https://<API_DOMAIN>/docs`. It only describes the
API; every call still needs a login.

## 4. Create the first administrator

Self-registration only creates reporters (D19). Create the first administrator
from the server:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml exec api python - <<'PY'
from app.db.session import SessionLocal
from app.core.security import hash_password
from app.models import Administrator, User
with SessionLocal() as db:
    u = User(full_name="Pilot Administrator", phone_number="+2547XXXXXXXX",
             email="admin@your-org.example", password_hash=hash_password("A-strong-temporary-password-1"))
    db.add(u); db.flush()
    db.add(Administrator(user_id=u.id, admin_level=1)); db.commit()
    print("created", u.id)
PY
```

Sign in to the dashboard, change nothing else yet, and create the verifier and
agency-staff accounts from **Users**. **Do not run `scripts/seed.py` in
production**; it refuses to run when `ENVIRONMENT=production`.

## 5. Updating

```bash
git pull
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
```

`migrate` applies new migrations before the new API starts. Take a backup first.

## 6. Backups

| What | How |
|---|---|
| Database | `docker compose ... exec db pg_dump -U tracehealth -Fc tracehealth > backup-$(date +%F).dump` daily (cron), copied off the server. |
| Photos (local storage) | the `uploads` volume: `docker run --rm -v tracehealth_uploads:/d -v $PWD:/b alpine tar czf /b/uploads-$(date +%F).tgz -C /d .` |
| Photos (S3) | enable versioning / lifecycle on the bucket. |
| Secrets | `.env.production` in a password manager. |

Restore test (do it once before the pilot):
`pg_restore -U tracehealth -d tracehealth --clean backup.dump`.

## 7. Mobile app release

1. In `mobile/.env` set `EXPO_PUBLIC_API_URL=https://<API_DOMAIN>`.
2. `npm install -g eas-cli && eas login && eas init` (once).
3. `eas build --profile preview --platform android` produces an APK that can
   be installed on pilot phones directly. Use the `production` profile for a
   Play Store build later.
4. For phone alerts set `PUSH_PROVIDER=expo` on the server (see below).

## 8. Switching on real providers

Do these one at a time, on staging first, with written approval from the
pilot partner for anything that sends money.

### Push notifications (Expo)

Set `PUSH_PROVIDER=expo`. The API sends to Expo's push service
(`https://exp.host/--/api/v2/push/send`). If you switch on "enhanced push
security" in the Expo project, also set `EXPO_ACCESS_TOKEN`. Remote push needs a
development or release build of the app; it does not work in Expo Go on Android
(D39).

### SMS (Africa's Talking)

1. Create an account at africastalking.com; open the **Sandbox** app; Settings →
   API Key → generate.
2. `SMS_PROVIDER=africastalking`, `AT_USERNAME=sandbox`, `AT_API_KEY=<key>`.
   Sandbox messages appear in the Africa's Talking simulator, not on phones.
3. For live SMS: create a live app, buy SMS credit, request a sender ID, then set
   `AT_USERNAME=<live app username>`, the live key and `AT_SENDER_ID`.

### M-Pesa payouts (Daraja B2C)

**Sandbox first.** No real money moves in the sandbox.

1. Register at the Safaricom developer portal (developer.safaricom.co.ke) and
   create an app with the **M-Pesa Sandbox** product. Note the **Consumer Key**
   and **Consumer Secret**.
2. From the portal's test credentials page, note the sandbox **B2C shortcode**
   and **initiator name**, and generate the **Security Credential** (the
   initiator password encrypted with Safaricom's certificate; the portal does
   this for you).
3. Set in `.env.production` (or your local `.env` with a public tunnel):

   ```
   PAYOUT_PROVIDER=MPESA_DARAJA
   MPESA_ENVIRONMENT=sandbox
   MPESA_CONSUMER_KEY=...
   MPESA_CONSUMER_SECRET=...
   MPESA_SHORTCODE=...
   MPESA_INITIATOR_NAME=...
   MPESA_SECURITY_CREDENTIAL=...
   MPESA_CALLBACK_BASE_URL=https://<API_DOMAIN>
   MPESA_CALLBACK_TOKEN=<long random value>
   ```

   Safaricom must be able to reach `MPESA_CALLBACK_BASE_URL` over HTTPS. Locally,
   use a tunnel such as `cloudflared tunnel --url http://localhost:8000`.
4. Restart (`up -d`), verify a test report, and watch **Payouts** on the
   dashboard: the payout goes to "Processing" (ACCEPTED by M-Pesa) and then to
   "Paid" with the M-Pesa receipt when the result callback arrives. If no
   result arrives within 24 h it becomes FAILED with a reason.
5. If anything says "check the M-Pesa portal before retrying", look the
   transaction up in the portal first. TraceHealth never retries automatically
   when a payment might already have gone through.

**Going live** needs Safaricom's go-live approval for your organisation's
B2C shortcode, a funded B2C account, live credentials, and
`MPESA_ENVIRONMENT=production`. Payouts created while `PAYOUT_PROVIDER=MOCK`
stay test payments and are always shown with the **Test** badge.

## 9. Pre-pilot checklist

- [ ] HTTPS works on both domains; `http://` redirects to `https://`.
- [ ] `/health` reports the database OK.
- [ ] First administrator created; seed accounts do not exist.
- [ ] Dashboard sign-in works in Chrome and Edge.
- [ ] A test phone (release build) can register, submit online and offline, and
      receives push for a decision.
- [ ] Clinic CSV from the partner imports; a file with a patient column is refused.
- [ ] Linkage settings and category mapping agreed with the partner (Settings).
- [ ] Kiswahili text reviewed by a native speaker (D13).
- [ ] Privacy notice text and retention periods approved (data-protection.md).
- [ ] Daily backups running and one restore tested.
- [ ] Payout provider decision recorded (MOCK for a dry run, M-Pesa sandbox, or live).
- [ ] Load test run against staging (`docs/testing.md`).
