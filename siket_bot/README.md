# Siket Tutoring — Telegram Bot

A Telegram bot version of siketutoring.com.et: browse verified tutors, request a
free trial lesson, send a general enquiry, apply to become a tutor, and take a
quick matching quiz — all from Telegram. Data is stored locally in a SQLite
file (`siket.db`), and you (the admin) get a DM for every enquiry, tutor
application, and booking request.

## 1. Get a bot token from BotFather

1. Open Telegram, message **@BotFather**.
2. Send `/newbot`, give it a name and a username (must end in `bot`, e.g. `SiketTutoringBot`).
3. BotFather replies with an API token like `123456789:AAExample...`. Copy it.
4. Message **@userinfobot** to get your own numeric Telegram user id — you'll
   need this so the bot knows where to send admin notifications.

## 2. Install

Requires Python 3.10+.

```bash
cd siket_bot
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 3. Configure

```bash
cp .env.example .env
```

Edit `.env`:

```
BOT_TOKEN=<paste the token from BotFather>
ADMIN_CHAT_ID=<your numeric Telegram user id>
```

## 4. Run locally (optional, to test)

```bash
python bot.py
```

Open your bot in Telegram and send `/start`.

## 5. Deploy to Railway (keeps it running 24/7)

This repo already includes a `Procfile` and `runtime.txt` so Railway can run
it with no extra config.

1. Push this folder to a new GitHub repo (drag-and-drop into a new repo on
   github.com works fine if you don't use git on the command line).
2. On [railway.app](https://railway.app), sign up, then **New Project →
   Deploy from GitHub repo** and pick your repo.
3. Railway will detect Python and install `requirements.txt` automatically.
   Under the service's **Settings → Deploy**, make sure the start command
   uses the `worker` process from the `Procfile` (Railway usually detects
   this automatically since there's no web server listening on a port here).
4. Go to the service's **Variables** tab and add:
   - `BOT_TOKEN` — from BotFather
   - `ADMIN_CHAT_ID` — your numeric Telegram id
   (Do **not** upload `.env` — Railway's Variables tab replaces it, and
   `.gitignore` already keeps `.env` out of git.)
5. Railway redeploys automatically whenever variables change. Open
   **Deployments → View Logs** and confirm you see `Siket Tutoring bot
   starting…` with no errors.
6. Message your bot on Telegram and send `/start` — it's now live 24/7.

**Note on the database:** `siket.db` (SQLite) lives on Railway's ephemeral
filesystem by default, which is fine to start but can reset on redeploy. Once
you have real tutors/enquiries you care about keeping, ask me to switch
storage to a Railway **Postgres** or **persistent volume** — it's a small
change to `db.py`.

## 6. Duplicate-check against the real website (optional)

To warn when someone applying to tutor (or sending an enquiry) already has an
account on siketutoring.com.et, the bot can call a small read-only endpoint
on the Django app instead of connecting to the production database directly.

1. Have your dev add the endpoint described in
   `django_check_duplicate_snippet.py` to the Django `core` app (verify field
   names against your real `models.py` first — see the warnings at the top
   of that file).
2. Set `BOT_API_KEY` on Render (the Django app) to a random secret.
3. Set these two Railway variables on the bot to the same secret + your live URL:
   - `SITE_API_URL=https://siketutoring.com.et/api/check-duplicate/`
   - `SITE_API_KEY=<same value as BOT_API_KEY>`

Until both variables are set, the bot works exactly as before — the
duplicate check silently no-ops rather than blocking anyone.

Once live:
- **Tutor signup** — if a match is found, the applicant sees a warning and
  must confirm before the application is submitted (flagged for you too).
- **Enquiry form** — a match doesn't block the parent, but adds a note to
  your admin notification so you know to check before following up.

### Other hosting options
The same `Procfile` approach works on **Render** (as a Background Worker,
not a Web Service) or **Fly.io**. On a plain **VPS**, skip the Procfile and
instead run `python bot.py` inside `tmux`/`screen`, or set it up as a
systemd service so it restarts automatically on reboot/crash.

## What it does

**For parents / students**
- 🔍 **Find a Tutor** — filter by subject and teaching mode (online / in-person /
  hybrid), browse verified tutor cards, and request a trial lesson in-chat.
- 🎯 **Matching Quiz** — 4 quick tap-through questions (subject, budget, mode,
  learning style) that recommend a tutor or save your preferences as a lead.
- 📝 **Send an Enquiry** — mirrors the site's contact form (name, email, phone,
  student level, subject, message).
- ℹ️ **How It Works** / 📞 **Contact Us** — static info pages.

**For tutors**
- 🧑‍🏫 **Become a Tutor** — collects name, email, phone, subjects taught
  (multi-select), teaching mode, experience, hourly rate, and bio. Applications
  go to the admin for approval before they appear publicly.

**For you (admin)**

You'll get a DM for every enquiry, tutor application, and booking request.
Admin-only commands (must be sent from the `ADMIN_CHAT_ID` account):

| Command | Description |
|---|---|
| `/admin` | Show this list of admin commands |
| `/pending` | List tutor applications awaiting review |
| `/approve <id>` | Approve an application — the tutor goes live immediately |
| `/reject <id>` | Reject an application |
| `/leads` | Recent parent enquiries |
| `/bookings` | Recent booking requests |
| `/tutors` | List every tutor (verified and unverified) |

## Data

Everything is stored in `siket.db` (SQLite) next to `bot.py` — no external
database needed. One tutor (Michael Andualem, matching the live site) is
seeded automatically the first time the bot runs. Delete `siket.db` to reset.

## Notes / next steps

- This is a standalone bot with its own database — it does **not** read or
  write to the real siketutoring.com.et backend. If you want it to show the
  *actual* live tutor list or push real bookings into your existing site,
  I can wire it up to your site's API/database instead — just share the API
  details or database access.
- Payments aren't wired up (the site mentions "local payment options" but
  doesn't process payment on these pages) — bookings are request-only, same
  as the site's "Request tutor" flow, and confirmed manually by you.
