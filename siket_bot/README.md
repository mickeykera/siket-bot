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

## 4. Run

```bash
python bot.py
```

Open your bot in Telegram and send `/start`.

To keep it running after you close your terminal, use `tmux`/`screen`, a
systemd service, or deploy it to a small VPS / Railway / Render / Fly.io box
that runs `python bot.py` continuously (or convert `run_polling()` to a
webhook if you're already running a web server — see the python-telegram-bot
docs for `run_webhook`).

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
