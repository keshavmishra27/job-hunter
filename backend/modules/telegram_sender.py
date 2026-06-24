"""
Telegram Bot sender – sends eligible internship notifications to a user's
Telegram chat (personal chat or channel) via the Bot API.

Setup:
  1. Create a bot via @BotFather → copy the token
  2. Add TELEGRAM_BOT_TOKEN to .env
  3. Each user stores their telegram_chat_id in their profile
     (get it by messaging the bot and calling /getUpdates)
"""

import asyncio
import httpx
from loguru import logger
from backend.config import get_settings

settings = get_settings()

TELEGRAM_API = "https://api.telegram.org/bot{token}"


def _format_notice_message(notice: dict, score_info: dict | None = None) -> str:
    """
    Build a rich Telegram message (MarkdownV2-safe plain text) for a notice.
    """
    title = notice.get("title") or "Untitled"
    company = notice.get("company") or "—"
    source = notice.get("source") or "—"
    location = notice.get("location") or ""
    apply_link = notice.get("apply_link") or notice.get("portal_link") or ""

                     
    score_text = ""
    if score_info:
        score_val = score_info.get("score", 0)
        breakdown = score_info.get("breakdown", {})
        matched_skills = score_info.get("matched_skills", [])
        matched_roles = score_info.get("matched_roles", [])
        matched_projects = score_info.get("matched_projects", [])

        score_text = f"\n📊 Score: {score_val}/10"
        if breakdown:
            parts = []
            for k, v in breakdown.items():
                label = k.replace("_", " ").title()
                pct = round(v * 100)
                parts.append(f"  • {label}: {pct}%")
            score_text += "\n" + "\n".join(parts)

        if matched_roles:
            score_text += f"\n🎯 Roles: {', '.join(matched_roles)}"
        if matched_skills:
            score_text += f"\n🛠 Skills: {', '.join(matched_skills)}"
        if matched_projects:
            score_text += f"\n📁 Projects: {', '.join(matched_projects[:3])}"

                 
    elig = notice.get("eligibility_status") or ""
    elig_emoji = {"eligible": "✅", "maybe": "🟡", "not_eligible": "❌"}.get(elig, "❓")

    lines = [
        f"🔔 *{title}*",
        f"🏢 {company}  |  📡 {source}",
    ]
    if location:
        lines.append(f"📍 {location}")
    lines.append(f"{elig_emoji} Eligibility: {elig or 'unknown'}")
    if score_text:
        lines.append(score_text)
    if apply_link:
        lines.append(f"\n🔗 [Apply Here]({apply_link})")

    return "\n".join(lines)


async def send_telegram_message(
    chat_id: str,
    text: str,
    bot_token: str | None = None,
    parse_mode: str = "Markdown",
) -> dict:
    """Send a single message to a Telegram chat."""
    token = bot_token or settings.telegram_bot_token
    if not token:
        logger.warning("[TelegramSender] No TELEGRAM_BOT_TOKEN configured – skipping")
        return {"ok": False, "error": "No bot token configured"}

    url = f"{TELEGRAM_API.format(token=token)}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": False,
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, json=payload)
            data = resp.json()
            if data.get("ok"):
                logger.success(f"[TelegramSender] Sent to chat {chat_id}")
            else:
                                                            
                logger.warning(
                    f"[TelegramSender] Markdown failed ({data.get('description')}), retrying as plain text"
                )
                payload["parse_mode"] = ""
                resp = await client.post(url, json=payload)
                data = resp.json()
                if data.get("ok"):
                    logger.success(f"[TelegramSender] Sent to chat {chat_id} (plain text)")
                else:
                    logger.error(f"[TelegramSender] Failed: {data}")
            return data
    except Exception as e:
        logger.error(f"[TelegramSender] Error sending to {chat_id}: {e}")
        return {"ok": False, "error": str(e)}


async def send_notice_to_telegram(
    chat_id: str,
    notice: dict,
    score_info: dict | None = None,
    bot_token: str | None = None,
) -> dict:
    """Format and send a single internship notice to Telegram."""
    msg = _format_notice_message(notice, score_info)
    return await send_telegram_message(chat_id, msg, bot_token)


async def send_eligible_notices(
    chat_id: str,
    notices: list[dict],
    score_infos: list[dict] | None = None,
    min_score: float = 4.0,
    bot_token: str | None = None,
) -> dict:
    """
    Filter notices by eligibility + minimum score, then send each to Telegram.
    Returns summary of what was sent.
    """
    sent = 0
    skipped = 0

    for i, notice in enumerate(notices):
        score_info = score_infos[i] if score_infos and i < len(score_infos) else None

                                           
        elig = notice.get("eligibility_status") or "unknown"
        if elig == "not_eligible":
            skipped += 1
            continue

                               
        score = 0
        if score_info:
            score = score_info.get("score", 0)
        elif notice.get("score") is not None:
            score = notice["score"]

        if score < min_score:
            skipped += 1
            continue

        result = await send_notice_to_telegram(chat_id, notice, score_info, bot_token)
        if result.get("ok"):
            sent += 1

                                                                 
        await asyncio.sleep(0.15)

    logger.info(f"[TelegramSender] Sent {sent} notices, skipped {skipped}")
    return {"sent": sent, "skipped": skipped}
