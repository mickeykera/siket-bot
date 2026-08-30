import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
# Your personal Telegram numeric user id (not @username).
# The bot will DM this id whenever a parent sends an enquiry,
# a tutor applies, or a booking request comes in.
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0") or 0)

DB_PATH = os.getenv("DB_PATH", "siket.db")

# Optional: read-only duplicate-check endpoint on the Django site.
# Leave both unset and the bot works exactly as before (no duplicate checks).
SITE_API_URL = os.getenv("SITE_API_URL", "")  # e.g. https://siketutoring.com.et/api/check-duplicate/
SITE_API_KEY = os.getenv("SITE_API_KEY", "")  # shared secret, must match the Django view

SUBJECTS = [
    "Mathematics", "Physics", "Chemistry", "Biology", "English",
    "Amharic", "History", "Geography", "ICT / Computer",
    "Languages", "Exam preparation",
]

MODES = ["Online", "In-person", "Hybrid"]

STUDENT_LEVELS = [
    "Primary school", "Secondary school", "Exam preparation", "Adult learner",
]

BUDGET_BANDS = ["Under 300 ETB/hr", "300–600 ETB/hr", "600–1000 ETB/hr", "1000+ ETB/hr"]

LEARNING_STYLES = ["Visual", "Hands-on", "Exam-focused", "Not sure"]

WEBSITE_URL = "https://siketutoring.com.et"
