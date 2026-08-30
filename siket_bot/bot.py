import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

import db
from config import (
    ADMIN_CHAT_ID,
    BOT_TOKEN,
    BUDGET_BANDS,
    LEARNING_STYLES,
    MODES,
    STUDENT_LEVELS,
    SUBJECTS,
    WEBSITE_URL,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger("siket-bot")

# ---------------------------------------------------------------------------
# Conversation states
# ---------------------------------------------------------------------------
(
    ENQ_NAME, ENQ_EMAIL, ENQ_PHONE, ENQ_LEVEL, ENQ_SUBJECT, ENQ_MESSAGE,
) = range(6)

(
    TSIG_NAME, TSIG_EMAIL, TSIG_PHONE, TSIG_SUBJECTS, TSIG_MODE,
    TSIG_EXPERIENCE, TSIG_RATE, TSIG_BIO,
) = range(6, 14)

(
    BOOK_NAME, BOOK_CONTACT, BOOK_TIME, BOOK_MESSAGE,
) = range(14, 18)

(
    QUIZ_SUBJECT, QUIZ_BUDGET, QUIZ_MODE, QUIZ_STYLE,
) = range(18, 22)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def main_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Find a Tutor", callback_data="menu:find")],
        [InlineKeyboardButton("🎯 Take the Matching Quiz", callback_data="menu:quiz")],
        [InlineKeyboardButton("📝 Send an Enquiry", callback_data="menu:enquiry")],
        [InlineKeyboardButton("🧑‍🏫 Become a Tutor", callback_data="menu:tutorsignup")],
        [InlineKeyboardButton("ℹ️ How It Works", callback_data="menu:howitworks")],
        [InlineKeyboardButton("📞 Contact Us", callback_data="menu:contact")],
    ])


def back_to_menu_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Main Menu", callback_data="menu:root")]])


def chunk_buttons(items, prefix, per_row=2, extra_row=None):
    buttons = [InlineKeyboardButton(item, callback_data=f"{prefix}{item}") for item in items]
    rows = [buttons[i:i + per_row] for i in range(0, len(buttons), per_row)]
    if extra_row:
        rows.append(extra_row)
    return InlineKeyboardMarkup(rows)


def tutor_card(t):
    subjects = t["subjects"].replace(",", ", ")
    stars = "✓ Verified" if t["verified"] else "Pending verification"
    return (
        f"*{t['name']}*\n"
        f"{stars}\n"
        f"Subjects: {subjects}\n"
        f"Mode: {t['mode']} · {t['experience_years']} yr(s) experience\n"
        f"Rate: ETB {t['rate_etb']}/hour\n\n"
        f"{t['bio']}"
    )


async def notify_admin(context: ContextTypes.DEFAULT_TYPE, text: str):
    if ADMIN_CHAT_ID:
        try:
            await context.bot.send_message(ADMIN_CHAT_ID, text, parse_mode=ParseMode.MARKDOWN)
        except Exception:
            logger.exception("Failed to notify admin")


# ---------------------------------------------------------------------------
# /start and main menu routing
# ---------------------------------------------------------------------------

WELCOME = (
    "👋 *Welcome to Siket Tutoring!*\n\n"
    "Find trusted, verified tutors in Ethiopia for Math, English, Physics, "
    "Amharic & more — personalised matching, local payments, and a free trial lesson.\n\n"
    "What would you like to do?"
)

HOW_IT_WORKS = (
    "*From search to first lesson in four simple steps:*\n\n"
    "1️⃣ *Search* — Filter by subject, price, and learning style.\n"
    "2️⃣ *Choose* — Compare verified profiles, ratings, and availability.\n"
    "3️⃣ *Book* — Pick a tutor, choose your goal, request a trial lesson.\n"
    "4️⃣ *Learn* — Start with a free trial, then continue with your perfect match."
)

CONTACT_TEXT = (
    "📞 *Contact Siket Tutoring*\n\n"
    f"🌐 {WEBSITE_URL}\n"
    "Or use *Send an Enquiry* from the menu and we'll get back to you within one business day."
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(WELCOME, parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu_kb())


async def menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the static, non-conversation menu buttons."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "menu:root":
        context.user_data.clear()
        await query.edit_message_text(WELCOME, parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu_kb())
    elif data == "menu:howitworks":
        await query.edit_message_text(HOW_IT_WORKS, parse_mode=ParseMode.MARKDOWN, reply_markup=back_to_menu_kb())
    elif data == "menu:contact":
        await query.edit_message_text(CONTACT_TEXT, parse_mode=ParseMode.MARKDOWN, reply_markup=back_to_menu_kb())
    elif data == "menu:find":
        await show_subject_filter(query)


# ---------------------------------------------------------------------------
# Find a Tutor (pure inline-button flow, no free text needed)
# ---------------------------------------------------------------------------

async def show_subject_filter(query):
    kb = chunk_buttons(
        SUBJECTS, "find:subj:", per_row=2,
        extra_row=[InlineKeyboardButton("All subjects", callback_data="find:subj:All")],
    )
    kb.inline_keyboard.append([InlineKeyboardButton("⬅️ Main Menu", callback_data="menu:root")])
    await query.edit_message_text(
        "🔍 *Find a Tutor*\n\nWhich subject does your learner need?",
        parse_mode=ParseMode.MARKDOWN, reply_markup=kb,
    )


async def find_subject_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    subject = query.data.split("find:subj:", 1)[1]
    context.user_data["find_subject"] = subject

    kb = chunk_buttons(
        MODES, f"find:mode:{subject}:", per_row=3,
        extra_row=[InlineKeyboardButton("Any mode", callback_data=f"find:mode:{subject}:Any")],
    )
    kb.inline_keyboard.append([InlineKeyboardButton("⬅️ Main Menu", callback_data="menu:root")])
    await query.edit_message_text(
        f"Subject: *{subject}*\n\nOnline, in-person, or hybrid?",
        parse_mode=ParseMode.MARKDOWN, reply_markup=kb,
    )


async def find_mode_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, _, rest = query.data.partition("find:mode:")
    subject, mode = rest.split(":", 1)

    subj_filter = None if subject == "All" else subject
    mode_filter = None if mode == "Any" else mode
    tutors = db.list_tutors(subject=subj_filter, mode=mode_filter, verified_only=True)

    if not tutors:
        await query.edit_message_text(
            "No verified tutors match that yet — try *All subjects* / *Any mode*, "
            "or send an enquiry and we'll personally find someone for you.",
            parse_mode=ParseMode.MARKDOWN, reply_markup=back_to_menu_kb(),
        )
        return

    await query.edit_message_text(
        f"✨ {len(tutors)} tutor(s) ready to help.", parse_mode=ParseMode.MARKDOWN,
    )
    for t in tutors:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📩 Request this tutor →", callback_data=f"book:{t['id']}")],
        ])
        await query.message.reply_text(tutor_card(t), parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    await query.message.reply_text("Looking for someone else?", reply_markup=back_to_menu_kb())


# ---------------------------------------------------------------------------
# Enquiry form (mirrors the website's "Send us a quick enquiry" box)
# ---------------------------------------------------------------------------

async def enquiry_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["enquiry"] = {}
    await query.edit_message_text(
        "📝 *Quick Enquiry*\n\nWe'll get back to you within one business day.\n\n"
        "What's your name?",
        parse_mode=ParseMode.MARKDOWN,
    )
    return ENQ_NAME


async def enquiry_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["enquiry"]["name"] = update.message.text.strip()
    await update.message.reply_text("What's your email address?")
    return ENQ_EMAIL


async def enquiry_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["enquiry"]["email"] = update.message.text.strip()
    await update.message.reply_text("What's your phone number?")
    return ENQ_PHONE


async def enquiry_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["enquiry"]["phone"] = update.message.text.strip()
    kb = chunk_buttons(STUDENT_LEVELS, "enq:level:", per_row=1)
    await update.message.reply_text("What's the student's level?", reply_markup=kb)
    return ENQ_LEVEL


async def enquiry_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    level = query.data.split("enq:level:", 1)[1]
    context.user_data["enquiry"]["level"] = level
    kb = chunk_buttons(SUBJECTS, "enq:subj:", per_row=2)
    await query.edit_message_text("Which subject?", reply_markup=kb)
    return ENQ_SUBJECT


async def enquiry_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    subject = query.data.split("enq:subj:", 1)[1]
    context.user_data["enquiry"]["subject"] = subject
    await query.edit_message_text(f"Subject: *{subject}*\n\nAnything else you'd like us to know?", parse_mode=ParseMode.MARKDOWN)
    return ENQ_MESSAGE


async def enquiry_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    e = context.user_data["enquiry"]
    message = update.message.text.strip()
    chat_id = update.effective_chat.id
    db.add_enquiry(chat_id, e["name"], e["email"], e["phone"], e["level"], e["subject"], message)

    await update.message.reply_text(
        "✅ Thanks! Your enquiry has been sent — we'll get back to you within one business day.",
        reply_markup=back_to_menu_kb(),
    )
    await notify_admin(
        context,
        "📝 *New enquiry*\n"
        f"Name: {e['name']}\nEmail: {e['email']}\nPhone: {e['phone']}\n"
        f"Level: {e['level']}\nSubject: {e['subject']}\nMessage: {message}",
    )
    context.user_data.pop("enquiry", None)
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Become a Tutor signup
# ---------------------------------------------------------------------------

async def tutorsignup_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["tsig"] = {"subjects": set()}
    await query.edit_message_text(
        "🧑‍🏫 *Teach with Siket*\n\nBuild your profile and start growing your teaching practice.\n\n"
        "What's your full name?",
        parse_mode=ParseMode.MARKDOWN,
    )
    return TSIG_NAME


async def tsig_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["tsig"]["name"] = update.message.text.strip()
    await update.message.reply_text("Your email address?")
    return TSIG_EMAIL


async def tsig_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["tsig"]["email"] = update.message.text.strip()
    await update.message.reply_text("Your phone number?")
    return TSIG_PHONE


def subjects_kb(selected: set):
    rows = []
    row = []
    for i, s in enumerate(SUBJECTS, 1):
        label = f"✅ {s}" if s in selected else s
        row.append(InlineKeyboardButton(label, callback_data=f"tsig:subj:{s}"))
        if i % 2 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("✔️ Done", callback_data="tsig:subj:DONE")])
    return InlineKeyboardMarkup(rows)


async def tsig_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["tsig"]["phone"] = update.message.text.strip()
    await update.message.reply_text(
        "Which subjects do you teach? Tap all that apply, then *Done*.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=subjects_kb(context.user_data["tsig"]["subjects"]),
    )
    return TSIG_SUBJECTS


async def tsig_subjects(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = query.data.split("tsig:subj:", 1)[1]
    selected = context.user_data["tsig"]["subjects"]

    if choice == "DONE":
        if not selected:
            await query.answer("Pick at least one subject first.", show_alert=True)
            return TSIG_SUBJECTS
        kb = chunk_buttons(MODES, "tsig:mode:", per_row=3)
        await query.edit_message_text("How will you teach?", reply_markup=kb)
        return TSIG_MODE

    if choice in selected:
        selected.remove(choice)
    else:
        selected.add(choice)
    await query.edit_message_reply_markup(reply_markup=subjects_kb(selected))
    return TSIG_SUBJECTS


async def tsig_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    mode = query.data.split("tsig:mode:", 1)[1]
    context.user_data["tsig"]["mode"] = mode
    await query.edit_message_text("How many years of tutoring/teaching experience do you have? (number)")
    return TSIG_EXPERIENCE


async def tsig_experience(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("Please reply with a number, e.g. 2")
        return TSIG_EXPERIENCE
    context.user_data["tsig"]["experience"] = int(text)
    await update.message.reply_text("What's your hourly rate in ETB? (number)")
    return TSIG_RATE


async def tsig_rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("Please reply with a number, e.g. 400")
        return TSIG_RATE
    context.user_data["tsig"]["rate"] = int(text)
    await update.message.reply_text("Finally, a short bio (your experience, style, subjects you love teaching):")
    return TSIG_BIO


async def tsig_bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = context.user_data["tsig"]
    bio = update.message.text.strip()
    chat_id = update.effective_chat.id
    subjects_str = ",".join(sorted(t["subjects"]))

    app_id = db.add_tutor_application(
        chat_id, t["name"], t["email"], t["phone"], subjects_str, t["mode"],
        t["experience"], t["rate"], bio,
    )
    await update.message.reply_text(
        "✅ Thanks! Your tutor profile has been submitted for verification. "
        "We'll be in touch once it's approved.",
        reply_markup=back_to_menu_kb(),
    )
    await notify_admin(
        context,
        f"🧑‍🏫 *New tutor application* (#{app_id})\n"
        f"Name: {t['name']}\nEmail: {t['email']}\nPhone: {t['phone']}\n"
        f"Subjects: {subjects_str}\nMode: {t['mode']}\nExperience: {t['experience']} yrs\n"
        f"Rate: ETB {t['rate']}/hr\nBio: {bio}\n\n"
        f"Approve with /approve {app_id} or reject with /reject {app_id}",
    )
    context.user_data.pop("tsig", None)
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Booking a specific tutor (entered from the Find a Tutor results)
# ---------------------------------------------------------------------------

async def booking_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tutor_id = int(query.data.split("book:", 1)[1])
    tutor = db.get_tutor(tutor_id)
    if not tutor:
        await query.edit_message_text("Sorry, that tutor is no longer available.", reply_markup=back_to_menu_kb())
        return ConversationHandler.END

    context.user_data["booking"] = {"tutor_id": tutor_id}
    await query.message.reply_text(
        f"Requesting *{tutor['name']}*. What's your name?", parse_mode=ParseMode.MARKDOWN,
    )
    return BOOK_NAME


async def booking_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["booking"]["name"] = update.message.text.strip()
    await update.message.reply_text("Best phone number or Telegram username to reach you?")
    return BOOK_CONTACT


async def booking_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["booking"]["contact"] = update.message.text.strip()
    await update.message.reply_text("What day/time works best for a free trial lesson?")
    return BOOK_TIME


async def booking_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["booking"]["time"] = update.message.text.strip()
    await update.message.reply_text("Anything the tutor should know beforehand? (or send \"-\" to skip)")
    return BOOK_MESSAGE


async def booking_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    b = context.user_data["booking"]
    message = update.message.text.strip()
    chat_id = update.effective_chat.id
    tutor = db.get_tutor(b["tutor_id"])

    db.add_booking(b["tutor_id"], chat_id, b["name"], b["contact"], b["time"], message)
    await update.message.reply_text(
        f"✅ Request sent to *{tutor['name']}*! We'll confirm your free trial lesson shortly.",
        parse_mode=ParseMode.MARKDOWN, reply_markup=back_to_menu_kb(),
    )
    await notify_admin(
        context,
        f"📩 *New booking request* — tutor: {tutor['name']} (#{tutor['id']})\n"
        f"Parent: {b['name']}\nContact: {b['contact']}\nPreferred time: {b['time']}\nNote: {message}",
    )
    context.user_data.pop("booking", None)
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Matching Quiz
# ---------------------------------------------------------------------------

async def quiz_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["quiz"] = {}
    kb = chunk_buttons(SUBJECTS, "quiz:subj:", per_row=2)
    await query.edit_message_text(
        "🎯 *Matching Quiz*\n\nAnswer a few quick questions and we'll recommend a tutor.\n\n"
        "1/4 — Which subject?",
        parse_mode=ParseMode.MARKDOWN, reply_markup=kb,
    )
    return QUIZ_SUBJECT


async def quiz_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    subject = query.data.split("quiz:subj:", 1)[1]
    context.user_data["quiz"]["subject"] = subject
    kb = chunk_buttons(BUDGET_BANDS, "quiz:budget:", per_row=1)
    await query.edit_message_text("2/4 — What's your budget?", reply_markup=kb)
    return QUIZ_BUDGET


async def quiz_budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    budget = query.data.split("quiz:budget:", 1)[1]
    context.user_data["quiz"]["budget"] = budget
    kb = chunk_buttons(MODES, "quiz:mode:", per_row=3)
    await query.edit_message_text("3/4 — Online, in-person, or hybrid?", reply_markup=kb)
    return QUIZ_MODE


async def quiz_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    mode = query.data.split("quiz:mode:", 1)[1]
    context.user_data["quiz"]["mode"] = mode
    kb = chunk_buttons(LEARNING_STYLES, "quiz:style:", per_row=2)
    await query.edit_message_text("4/4 — What learning style fits best?", reply_markup=kb)
    return QUIZ_STYLE


async def quiz_style(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    style = query.data.split("quiz:style:", 1)[1]
    q = context.user_data["quiz"]
    q["style"] = style
    chat_id = update.effective_chat.id

    db.add_quiz_lead(chat_id, q["subject"], q["budget"], q["mode"], style)

    tutors = db.list_tutors(subject=q["subject"], mode=None if q["mode"] == "Any" else q["mode"], verified_only=True)
    if tutors:
        await query.edit_message_text(
            f"🎯 Based on your answers, here's a great match for *{q['subject']}*:",
            parse_mode=ParseMode.MARKDOWN,
        )
        for t in tutors[:3]:
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("📩 Request this tutor →", callback_data=f"book:{t['id']}")]])
            await query.message.reply_text(tutor_card(t), parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        await query.message.reply_text("Want to see more options?", reply_markup=back_to_menu_kb())
    else:
        await query.edit_message_text(
            "Thanks! We don't have a verified tutor matching that exact combination yet, "
            "but we've saved your preferences and our team will personally find you a match "
            "within one business day.",
            reply_markup=back_to_menu_kb(),
        )
    await notify_admin(
        context,
        f"🎯 *New quiz lead*\nSubject: {q['subject']}\nBudget: {q['budget']}\n"
        f"Mode: {q['mode']}\nStyle: {style}",
    )
    context.user_data.pop("quiz", None)
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Cancel (works inside any conversation)
# ---------------------------------------------------------------------------

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    if update.message:
        await update.message.reply_text("Cancelled.", reply_markup=back_to_menu_kb())
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Cancelled.", reply_markup=back_to_menu_kb())
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Admin-only tools
# ---------------------------------------------------------------------------

def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_chat.id != ADMIN_CHAT_ID:
            await update.message.reply_text("This command is for the Siket admin only.")
            return
        return await func(update, context)
    return wrapper


@admin_only
async def cmd_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    apps = db.list_pending_applications()
    if not apps:
        await update.message.reply_text("No pending tutor applications.")
        return
    for a in apps:
        text = (
            f"#{a['id']} — {a['name']}\n{a['email']} · {a['phone']}\n"
            f"Subjects: {a['subjects']}\nMode: {a['mode']} · {a['experience_years']} yrs · "
            f"ETB {a['rate_etb']}/hr\nBio: {a['bio']}\n\n"
            f"/approve {a['id']}  or  /reject {a['id']}"
        )
        await update.message.reply_text(text)


@admin_only
async def cmd_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /approve <application_id>")
        return
    app_id = int(context.args[0])
    tutor_id = db.approve_application(app_id)
    if tutor_id is None:
        await update.message.reply_text("Application not found or already processed.")
        return
    app = db.get_application(app_id)
    await update.message.reply_text(f"✅ Approved. Tutor #{tutor_id} is now live in Find a Tutor.")
    try:
        await context.bot.send_message(
            app["chat_id"],
            "🎉 Great news — your tutor profile on Siket Tutoring has been verified and is now live!",
        )
    except Exception:
        logger.exception("Could not notify tutor of approval")


@admin_only
async def cmd_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /reject <application_id>")
        return
    app_id = int(context.args[0])
    db.reject_application(app_id)
    await update.message.reply_text(f"Application #{app_id} rejected.")


@admin_only
async def cmd_leads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    enquiries = db.list_recent_enquiries(10)
    if not enquiries:
        await update.message.reply_text("No enquiries yet.")
        return
    lines = ["📝 *Recent enquiries:*"]
    for e in enquiries:
        lines.append(
            f"#{e['id']} {e['parent_name']} ({e['phone']}) — {e['subject']} / {e['student_level']}"
        )
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


@admin_only
async def cmd_bookings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bookings = db.list_recent_bookings(10)
    if not bookings:
        await update.message.reply_text("No booking requests yet.")
        return
    lines = ["📩 *Recent booking requests:*"]
    for b in bookings:
        lines.append(
            f"#{b['id']} {b['parent_name']} → {b['tutor_name']} — {b['preferred_time']} ({b['status']})"
        )
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


@admin_only
async def cmd_tutors(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tutors = db.list_tutors(verified_only=False)
    if not tutors:
        await update.message.reply_text("No tutors yet.")
        return
    lines = ["🧑‍🏫 *All tutors:*"]
    for t in tutors:
        flag = "✓" if t["verified"] else "unverified"
        lines.append(f"#{t['id']} {t['name']} — {t['subjects']} ({flag})")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


ADMIN_HELP = (
    "*Admin commands*\n"
    "/pending — list tutor applications awaiting review\n"
    "/approve <id> — approve a tutor application\n"
    "/reject <id> — reject a tutor application\n"
    "/leads — recent parent enquiries\n"
    "/bookings — recent booking requests\n"
    "/tutors — list all tutors"
)


@admin_only
async def cmd_admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(ADMIN_HELP, parse_mode=ParseMode.MARKDOWN)


# ---------------------------------------------------------------------------
# App wiring
# ---------------------------------------------------------------------------

def build_app() -> Application:
    db.init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("admin", cmd_admin_help))
    app.add_handler(CommandHandler("pending", cmd_pending))
    app.add_handler(CommandHandler("approve", cmd_approve))
    app.add_handler(CommandHandler("reject", cmd_reject))
    app.add_handler(CommandHandler("leads", cmd_leads))
    app.add_handler(CommandHandler("bookings", cmd_bookings))
    app.add_handler(CommandHandler("tutors", cmd_tutors))

    # Static menu items (root, how it works, contact) + entry point for find-tutor
    app.add_handler(CallbackQueryHandler(menu_router, pattern="^menu:(root|howitworks|contact|find)$"))
    app.add_handler(CallbackQueryHandler(find_subject_chosen, pattern="^find:subj:"))
    app.add_handler(CallbackQueryHandler(find_mode_chosen, pattern="^find:mode:"))

    enquiry_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(enquiry_start, pattern="^menu:enquiry$")],
        states={
            ENQ_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, enquiry_name)],
            ENQ_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, enquiry_email)],
            ENQ_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enquiry_phone)],
            ENQ_LEVEL: [CallbackQueryHandler(enquiry_level, pattern="^enq:level:")],
            ENQ_SUBJECT: [CallbackQueryHandler(enquiry_subject, pattern="^enq:subj:")],
            ENQ_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enquiry_message)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(enquiry_conv)

    tutorsignup_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(tutorsignup_start, pattern="^menu:tutorsignup$")],
        states={
            TSIG_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, tsig_name)],
            TSIG_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, tsig_email)],
            TSIG_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, tsig_phone)],
            TSIG_SUBJECTS: [CallbackQueryHandler(tsig_subjects, pattern="^tsig:subj:")],
            TSIG_MODE: [CallbackQueryHandler(tsig_mode, pattern="^tsig:mode:")],
            TSIG_EXPERIENCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, tsig_experience)],
            TSIG_RATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, tsig_rate)],
            TSIG_BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, tsig_bio)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(tutorsignup_conv)

    booking_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(booking_start, pattern="^book:")],
        states={
            BOOK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, booking_name)],
            BOOK_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, booking_contact)],
            BOOK_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, booking_time)],
            BOOK_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, booking_message)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(booking_conv)

    quiz_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(quiz_start, pattern="^menu:quiz$")],
        states={
            QUIZ_SUBJECT: [CallbackQueryHandler(quiz_subject, pattern="^quiz:subj:")],
            QUIZ_BUDGET: [CallbackQueryHandler(quiz_budget, pattern="^quiz:budget:")],
            QUIZ_MODE: [CallbackQueryHandler(quiz_mode, pattern="^quiz:mode:")],
            QUIZ_STYLE: [CallbackQueryHandler(quiz_style, pattern="^quiz:style:")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(quiz_conv)

    return app


def main():
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN is not set. Put it in a .env file (see .env.example).")
    app = build_app()
    logger.info("Siket Tutoring bot starting…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
