# Putting the TraceHealth demo online (free hosting)

This guide takes you from the project folder on your laptop to:

- a **public GitHub repository** with the sprint history as pull requests,
- the **API** running on Render,
- the **database** on Neon,
- the **web dashboard** on Netlify,
- the **Android app** as a downloadable APK on GitHub Releases.

Everything is on free plans. Allow about two hours the first time, most of it
waiting for builds. Do the steps in order: each one needs the address from the
one before.

For a real pilot on your own server, use `deployment.md` instead.

## 0. Tools on your laptop (Manjaro)

```bash
sudo pacman -S --needed git github-cli rsync unzip nodejs-lts-jod npm
git config --global user.name "Your Name"
git config --global user.email "the-email-on-your-github-account@example.com"
gh auth login        # GitHub.com > HTTPS > Login with a web browser
```

## 1. Publish the code to GitHub

Use the history kit (`tracehealth-github-kit.zip`). It rebuilds the repository
from the real sprint packages, one branch and pull request per sprint, so the
history shows how the project was actually built. All commits carry today's
date and your name.

```bash
mkdir -p ~/projects && cd ~/projects
unzip ~/Downloads/tracehealth-github-kit.zip
cd tracehealth-github-kit
bash publish.sh tracehealth          # "tracehealth" = the repository name
```

The script creates the public repository `github.com/<you>/tracehealth`, then
merges pull requests for Sprint 1, Sprint 2, Sprint 3–4 and the free-hosting
setup. It stops with a clear message if something is missing. Your working
copy ends up in `~/projects/tracehealth-github-kit/tracehealth`. Work there
from now on.

Open the repository on GitHub and check the **Pull requests → Closed** tab and
the **Actions** tab (CI runs on each pull request).

From now on, make changes the same way: create a branch, commit, push, open a
pull request, merge. Small regular commits with clear messages are what the
rubric looks for:

```bash
git switch -c docs/demo-links
# ...edit...
git add -A && git commit -m "Add live demo links to README"
git push -u origin docs/demo-links
gh pr create --fill && gh pr merge --merge --delete-branch
git switch main && git pull
```

## 2. Database: Neon

1. Go to https://neon.tech and sign up with GitHub.
2. Create a project: name `tracehealth`, PostgreSQL **16**, region
   **AWS Europe Central 1 (Frankfurt)** (same region as the API).
3. On the project dashboard click **Connect**. Switch **Connection pooling
   off**, so you get the direct connection string. Copy it. It looks like:
   `postgresql://neondb_owner:...@ep-xxxx.eu-central-1.aws.neon.tech/neondb?sslmode=require`

You don't need to create tables: the API does that when it first starts
(including the PostGIS extension).

## 3. API: Render

1. Go to https://render.com and sign up with GitHub.
2. **New + → Blueprint**, connect your GitHub account, and choose the
   `tracehealth` repository. Render finds `render.yaml`.
3. It asks for two values:
   - `DATABASE_URL`: the Neon string from step 2.
   - `CORS_ORIGINS`: for now type `https://example.netlify.app`. You'll put
     the real dashboard address here in step 4.
4. Click **Apply**. The first build takes 5–10 minutes. When it says **Live**,
   copy the service address, e.g. `https://tracehealth-api.onrender.com`. If
   that name was taken, Render adds letters; use whatever it shows.
5. Open `<API address>/health`. You should see `"status": "ok"` and
   `"database": "ok"`. Open `<API address>/docs` to see Swagger.

On first start the API builds the database and loads the **synthetic demo
data** with the demo accounts. Restarts don't load it again.

Free services sleep after 15 minutes without visitors and take up to a minute
to wake. The dashboard and the app wake the server as soon as they open.

## 4. Web dashboard: Netlify

1. Go to https://app.netlify.com and sign up with GitHub.
2. **Add new site → Import an existing project → GitHub**, choose `tracehealth`.
   Netlify reads `netlify.toml` (base `dashboard`, build `npm run build`,
   publish `dist`). Don't change those.
3. Before deploying, under **Environment variables**, add
   `VITE_API_URL` = your Render address (no trailing slash). Then **Deploy**.
4. **Site configuration → Change site name**: choose e.g. `tracehealth-demo`,
   giving `https://tracehealth-demo.netlify.app`.
5. Back in **Render → tracehealth-api → Environment**, set `CORS_ORIGINS` to the
   Netlify address exactly (https, no trailing slash) and **Save**. Render
   redeploys in a few minutes.
6. Open the Netlify address and sign in as `admin@example.org` /
   `ChangeMe123!`. If sign-in says the server can't be reached, check that
   `CORS_ORIGINS` matches the address in the browser bar exactly.

If you change `VITE_API_URL` later, trigger **Deploys → Trigger deploy**:
the address is built into the page.

## 5. Android app: Expo EAS build

```bash
cd ~/projects/tracehealth-github-kit/tracehealth/mobile
npm install
npx eas-cli@latest login             # create a free account at expo.dev if needed
npx eas-cli@latest init              # "Create a project" > yes. Adds the project id to app.json
```

Open `mobile/eas.json` and check that `build.preview.env.EXPO_PUBLIC_API_URL`
is your Render address. Then build:

```bash
npx eas-cli@latest build --platform android --profile preview
```

- Answer **yes** when it offers to generate an Android keystore.
- The build runs on Expo's servers. On the free plan it may wait in a queue;
  allow 15–60 minutes. The terminal prints a link to follow it.
- When it finishes, download the `.apk` from the link it prints.

Install it on your own phone first and log in as `0700000005`.

Commit the project id (step 1's branch → pull request routine):

```bash
cd ..
git switch -c build/android-apk
git add mobile/app.json mobile/eas.json
git commit -m "Configure EAS project for the Android demo build"
git push -u origin build/android-apk
gh pr create --fill && gh pr merge --merge --delete-branch
git switch main && git pull
```

## 6. Publish the APK on GitHub Releases

```bash
mv ~/Downloads/*.apk ~/Downloads/TraceHealth-1.0.0.apk
gh release create v1.0.0 ~/Downloads/TraceHealth-1.0.0.apk \
  --title "TraceHealth 1.0.0 (demo)" \
  --notes "Android app for the TraceHealth demo. Install steps are in the README. Demo data is synthetic; payouts are test payments."
```

The download link is
`https://github.com/<you>/tracehealth/releases/download/v1.0.0/TraceHealth-1.0.0.apk`.

## 7. Put the links in the README

At the top of `README.md`, replace `DASHBOARD_URL`, `API_URL`, `APK_URL`,
`SRS_URL` and `GITHUB_USER` with your real addresses (your SRS as a Google
Docs link shared with "Anyone with the link"). Commit through a branch and
pull request as above.

## 8. Check everything as a grader would

Use a private/incognito window, not signed in to anything:

- [ ] The GitHub repository opens and is **public**; the README shows the links.
- [ ] The dashboard opens; `admin@example.org` and `agency@example.org` sign in.
      Map, trends, reports, clinic data, payouts, users, audit log, settings all load.
- [ ] `<API>/docs` opens.
- [ ] The APK link downloads; the app installs on a second phone; a reporter
      can register, submit a report with a photo; `verifier1@example.org`
      sees it under Review and confirms it; the report then appears on the
      dashboard map and in Payouts as a test payment.
- [ ] The SRS link opens without asking for access.
- [ ] The Google Doc (`<names>_[Summative]_[MMDDYYYY]`) is shared as
      "Anyone with the link: Viewer" and every link in it opens.

## If something goes wrong

| Problem | Fix |
|---|---|
| Render build fails | Render → service → **Events / Logs**. Most often `DATABASE_URL` was pasted incompletely. |
| `/health` shows `"database": "error"` | Neon string wrong, or pooling was on. Copy the direct string again. |
| Dashboard: "Can't reach the server" | `CORS_ORIGINS` on Render must equal the Netlify address exactly; `VITE_API_URL` on Netlify must be the Render address; redeploy after changes. |
| App: "Can't reach the server" on first try | The server was asleep. Wait 30 seconds and try again. |
| Photos missing | Check `STORAGE_BACKEND=database` in Render's environment. |
| Want fresh demo data | Neon → **Branches → Reset from parent**, or delete and recreate the database, then restart the Render service. |
