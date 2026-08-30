import logging

import httpx

from config import SITE_API_KEY, SITE_API_URL

logger = logging.getLogger("siket-bot.site_api")


async def check_duplicate(email: str = "", phone: str = ""):
    """
    Calls the Django app's read-only duplicate-check endpoint
    (GET {SITE_API_URL}?email=...&phone=...  with header X-API-Key).

    Returns a dict like {"exists": bool, "role": "parent"|"tutor"|None,
    "matched_on": ["email", "phone"]} on success.

    Returns None if the check could not be performed — e.g. the endpoint
    isn't configured yet, the site is unreachable, or it errored. Callers
    MUST treat None as "unknown" and let the user proceed rather than
    blocking them because our check failed.
    """
    if not SITE_API_URL or not SITE_API_KEY:
        return None

    params = {}
    if email:
        params["email"] = email.strip().lower()
    if phone:
        params["phone"] = phone.strip()
    if not params:
        return None

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                SITE_API_URL, params=params, headers={"X-API-Key": SITE_API_KEY}
            )
        if resp.status_code != 200:
            logger.warning("check_duplicate got HTTP %s: %s", resp.status_code, resp.text[:300])
            return None
        return resp.json()
    except Exception:
        logger.exception("check_duplicate request failed")
        return None
