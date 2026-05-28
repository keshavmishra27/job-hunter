from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, or_
from backend.database import get_db
from backend.models import Notice, NoticeLink, AppliedNotice, Source
from backend.modules.fetchers import InternshalaFetcher, IndeedFetcher, CompanyCareerFetcher, GovtPortalFetcher, TelegramChannelFetcher, GmailFetcher
from backend.modules.normalizer import normalize_many
from backend.modules.internship_matcher import detect_year_fit
from backend.modules.internship_scorer import score_notice_detailed
from backend.modules.alert_engine import alert_on_notice
from backend.modules.telegram_sender import send_notice_to_telegram, send_eligible_notices
from backend.modules.notice_extractor import (
    extract_from_html, extract_from_pdf_bytes, parse_text_fields,
)
from backend.modules.portal_link_extractor import clean_and_resolve_links
from backend.config import get_settings
from loguru import logger
import httpx
from datetime import datetime

router = APIRouter(prefix="/internships", tags=["Internships"])

FETCHERS = {
    "internshala": InternshalaFetcher,
    "indeed": IndeedFetcher,
    "companycareers": CompanyCareerFetcher,
    "govtportal": GovtPortalFetcher,
    "telegram": TelegramChannelFetcher,
    "gmail": GmailFetcher,
}


@router.post("/fetch")
async def fetch_internships(user_id: str, sources: list[str] = Query(default=["companycareers", "govtportal"]), db: AsyncSession = Depends(get_db)):
    # very small MVP: fetch from fetchers, normalize, detect eligibility, score, and save
    keywords = ["internship"]
    all_raw = []

    # Get applied history
    from backend.models import Application
    applied_history = await db.execute(
        select(Application.job_fingerprint, Application.canonical_url).where(Application.user_id == user_id)
    )
    rows = applied_history.fetchall()
    applied_fingerprints = {r[0] for r in rows if r[0]}
    applied_urls = {r[1] for r in rows if r[1]}

    for source in sources:
        cls = FETCHERS.get(source.lower())
        if not cls:
            continue
        fetcher = cls()
        raw = await fetcher.fetch(
            keywords, 
            applied_fingerprints=applied_fingerprints, 
            applied_urls=applied_urls
        )
        all_raw.extend(raw)

    normalized = normalize_many(all_raw)

    warnings: list[str] = []
    if "govtportal" in [s.lower() for s in sources]:
        settings = get_settings()
        if not settings.govt_portal_urls:
            warnings.append("No GOVT_PORTAL_URLS configured; govt portal fetch will be skipped.")
    if "companycareers" in [s.lower() for s in sources]:
        settings = get_settings()
        if not settings.company_career_hosts:
            warnings.append("No COMPANY_CAREER_HOSTS configured; company career fetch will be skipped.")

    # load user profile for scoring and alerts
    telegram_chat_id = None
    try:
        from backend.models.user import UserProfile
        res = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
        profile = res.scalar_one_or_none()
        profile_dict = {
            "preferred_roles": profile.preferred_roles or [],
            "skills": profile.skills or [],
            "location_rule": profile.location_rule or {},
            "preferred_companies": getattr(profile, 'preferred_companies', []) or [],
            "graduation_year": getattr(profile, 'graduation_year', None),
        } if profile else {"preferred_roles": [], "skills": [], "location_rule": {}, "preferred_companies": [], "graduation_year": None}
        telegram_chat_id = getattr(profile, 'telegram_chat_id', None) if profile else None
    except Exception:
        profile_dict = {"preferred_roles": [], "skills": [], "location_rule": {}, "preferred_companies": [], "graduation_year": None}

    # simple dedupe by title+company
    seen = set()
    added = 0
    for item in normalized:
        key = (item.get("title"), item.get("company"))
        if key in seen:
            continue
        seen.add(key)
        # initial eligibility from raw text (now with graduation year awareness)
        grad_year = profile_dict.get("graduation_year")
        eligibility = detect_year_fit((item.get("title") or "") + " " + (item.get("description") or ""), grad_year)

        # attempt to fetch the apply/source link and extract richer fields
        # Skip for Telegram and Gmail — already extracted or not applicable
        parsed = {}
        apply_link = item.get("apply_link")
        is_telegram = (item.get("source") or "").startswith("Telegram/")
        is_gmail = (item.get("source") or "") == "Gmail"
        if apply_link and not is_telegram and not is_gmail and apply_link.startswith(("http://", "https://")):
            try:
                async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                    resp = await client.get(apply_link)
                    if resp.status_code == 200:
                        if apply_link.lower().endswith(".pdf") or resp.headers.get("content-type", "").lower().startswith("application/pdf"):
                            parsed = extract_from_pdf_bytes(resp.content)
                        else:
                            parsed = extract_from_html(resp.text, base_url=apply_link)
                        # clean and resolve links (follow redirects, strip tracking params)
                        try:
                            parsed_links = parsed.get("links") or []
                            parsed["links"] = await clean_and_resolve_links(parsed_links, base_url=apply_link, follow=True)
                        except Exception:
                            pass
            except Exception:
                parsed = {}
        # fallback: parse description text if no parsed content
        if not parsed:
            parsed = parse_text_fields(item.get("description") or "")

        portal = None
        links = parsed.get("links") or []
        # prefer explicit portal links
        for l in links:
            if l.get("kind") in ("portal", "google_form"):
                portal = l.get("url")
                break

        # For government portals, require explicit eligibility and a valid future deadline
        try:
            if (item.get("source") or "").lower() == "govtportal":
                # prefer parsed eligibility_text if available
                gov_elig = parsed.get("eligibility_text") or eligibility
                gov_deadline = parsed.get("deadline")
                from datetime import timezone
                now = datetime.now(tz=timezone.utc)
                if not gov_elig:
                    # skip notices that don't mention eligibility for target students
                    continue
                if not gov_deadline:
                    # skip if no deadline found
                    continue
                # ensure deadline is in the future
                try:
                    d = gov_deadline
                    if isinstance(d, str):
                        d = datetime.fromisoformat(d)
                    if d.tzinfo is None:
                        d = d.replace(tzinfo=timezone.utc)
                    if d < now:
                        continue
                except Exception:
                    # if parsing fails, conservatively skip
                    continue

        except Exception:
            pass

        # Determine source_type
        extra = item.get("extra") or {}
        if is_gmail:
            src_type = "email"
        elif is_telegram:
            src_type = "telegram"
        else:
            src_type = "website"

        # Gmail may carry deadline in extra
        notice_deadline = parsed.get("deadline")
        if not notice_deadline and extra.get("deadline"):
            try:
                notice_deadline = datetime.fromisoformat(extra["deadline"])
            except Exception:
                pass

        notice = Notice(
            id=item["id"],
            source=item.get("source"),
            source_type=src_type,
            title=item.get("title"),
            company=item.get("company"),
            location=parsed.get("location") or item.get("location"),
            portal_link=portal or item.get("apply_link"),
            source_link=item.get("apply_link"),
            raw_text=parsed.get("raw_text") or item.get("description"),
            eligibility_text=parsed.get("eligibility_text"),
            eligibility_status=eligibility,
            deadline=notice_deadline,
            stipend=parsed.get("stipend"),
            sender_email=extra.get("sender_email"),
            subject=extra.get("subject"),
            fetched_at=datetime.utcnow(),
            content_hash=None,
        )
        db.add(notice)
        # add extracted links
        for l in links:
            try:
                nl = NoticeLink(notice_id=notice.id, url=l.get("url"), kind=l.get("kind"))
                db.add(nl)
            except Exception:
                continue

        # score the notice immediately and create alert if relevant
        try:
            notice_dict = {
                "id": notice.id,
                "title": notice.title,
                "company": notice.company,
                "description": notice.raw_text,
                "apply_link": notice.portal_link,
                "posted_date": notice.fetched_at,
                "mode": None,
                "source": notice.source,
                "eligibility_text": notice.eligibility_text,
            }
            scored = score_notice_detailed(notice_dict, profile_dict, github_repos=None)
            notice.score = scored.get("score")
            notice.score_breakdown = scored.get("breakdown")
            await alert_on_notice(db, user_id, notice, notice.score or 0.0)
        except Exception:
            pass

        added += 1

    await db.commit()

    # --- Auto-send eligible notices to Telegram ---
    tg_sent = 0
    if telegram_chat_id and added > 0:
        try:
            # Re-fetch all new notices to send to Telegram
            q = await db.execute(select(Notice).order_by(Notice.fetched_at.desc()).limit(added))
            new_notices = q.scalars().all()
            for n in new_notices:
                n_dict = {
                    "title": n.title, "company": n.company,
                    "description": n.raw_text, "source": n.source,
                    "location": n.location, "apply_link": n.portal_link,
                    "eligibility_status": n.eligibility_status,
                }
                score_info = {
                    "score": n.score or 0,
                    "breakdown": n.score_breakdown or {},
                }
                # Only send eligible notices with score >= 4.0
                if n.eligibility_status in ("eligible", "maybe", None) and (n.score or 0) >= 4.0:
                    result = await send_notice_to_telegram(telegram_chat_id, n_dict, score_info)
                    if result.get("ok"):
                        tg_sent += 1
            logger.info(f"[Internships] Sent {tg_sent}/{added} notices to Telegram chat {telegram_chat_id}")
        except Exception as e:
            logger.error(f"[Internships] Telegram send failed: {e}")

    response = {"fetched": len(all_raw), "saved": added, "telegram_sent": tg_sent}
    if warnings:
        response["warnings"] = warnings
    return response


@router.get("/ranked/{user_id}")
async def get_ranked_internships(user_id: str, limit: int = 20, sources: list[str] = Query(default=["companycareers", "govtportal"]), db: AsyncSession = Depends(get_db)):
    # load user profile to tailor scoring; reuse UserProfile if exists
    try:
        from backend.models.user import UserProfile
        res = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
        profile = res.scalar_one_or_none()
        profile_dict = {
            "preferred_roles": profile.preferred_roles or [],
            "skills": profile.skills or [],
            "location_rule": profile.location_rule or {},
            "preferred_companies": getattr(profile, 'preferred_companies', []) or [],
            "graduation_year": getattr(profile, 'graduation_year', None),
        } if profile else {"preferred_roles": [], "skills": [], "location_rule": {}, "preferred_companies": [], "graduation_year": None}
    except Exception:
        profile_dict = {"preferred_roles": [], "skills": [], "location_rule": {}, "preferred_companies": [], "graduation_year": None}

    if sources:
        lowered = [s.lower() for s in sources]
        # Build conditions: exact match + pattern match only for selected source types
        conditions = [func.lower(Notice.source).in_(lowered)]
        if "telegram" in lowered:
            conditions.append(Notice.source.like("Telegram/%"))
        if "gmail" in lowered:
            conditions.append(Notice.source.like("Gmail%"))

        q = await db.execute(
            select(Notice).where(or_(*conditions))
        )
    else:
        q = await db.execute(select(Notice))
    notices = q.scalars().all()

    scored = []
    for n in notices:
        n_dict = {
            "id": n.id,
            "title": n.title,
            "company": n.company,
            "description": n.raw_text,
            "eligibility_text": n.eligibility_text,
            "apply_link": n.portal_link,
            "posted_date": n.fetched_at,
            "mode": None,
            "source": n.source,
        }
        result = score_notice_detailed(n_dict, profile_dict, github_repos=None)
        n.score = result["score"]
        n.score_breakdown = result["breakdown"]
        # attach matched skills/roles if present
        try:
            n._matched_skills = result.get("matched_skills", [])
            n._matched_roles = result.get("matched_roles", [])
        except Exception:
            pass
        scored.append(n)

    scored.sort(key=lambda x: (x.score or 0), reverse=True)

    await db.commit()

    out = []
    for n in scored[:limit]:
        out.append({
            "notice_id": n.id,
            "title": n.title,
            "company": n.company,
            "apply_link": n.portal_link,
            "source": n.source,
            "source_type": getattr(n, "source_type", None),
            "score": n.score,
            "score_breakdown": n.score_breakdown,
            "eligibility_status": n.eligibility_status,
            "location": n.location,
            "deadline": n.deadline.isoformat() if n.deadline else None,
            "sender_email": getattr(n, "sender_email", None),
            "subject": getattr(n, "subject", None),
        })
    return out


@router.get("/{notice_id}")
async def get_notice(notice_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Notice).where(Notice.id == notice_id))
    n = res.scalar_one_or_none()
    if not n:
        raise HTTPException(404, "Notice not found")
    return n


@router.post("/send-telegram/{user_id}")
async def send_to_telegram(
    user_id: str,
    min_score: float = 4.0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """Send eligible internship notices to the user's Telegram chat."""
    from backend.models.user import UserProfile

    res = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = res.scalar_one_or_none()
    if not profile:
        raise HTTPException(404, "Profile not found. Upload a resume first.")

    chat_id = getattr(profile, "telegram_chat_id", None)
    if not chat_id:
        raise HTTPException(
            400,
            "No Telegram chat ID configured. Set it in your profile settings.",
        )

    profile_dict = {
        "preferred_roles": profile.preferred_roles or [],
        "skills": profile.skills or [],
        "location_rule": profile.location_rule or {},
        "preferred_companies": getattr(profile, 'preferred_companies', []) or [],
        "graduation_year": getattr(profile, 'graduation_year', None),
    }

    # Fetch and score notices
    q = await db.execute(select(Notice).order_by(Notice.fetched_at.desc()).limit(100))
    notices = q.scalars().all()

    sent = 0
    skipped = 0
    for n in notices:
        n_dict = {
            "id": n.id, "title": n.title, "company": n.company,
            "description": n.raw_text, "eligibility_text": n.eligibility_text,
            "apply_link": n.portal_link, "posted_date": n.fetched_at,
            "mode": None, "source": n.source, "location": n.location,
        }
        scored = score_notice_detailed(n_dict, profile_dict, github_repos=None)

        # Filter: only eligible + above min_score
        elig = n.eligibility_status or "unknown"
        score = scored.get("score", 0)
        if elig == "not_eligible" or score < min_score:
            skipped += 1
            continue
        if sent >= limit:
            break

        n_dict["eligibility_status"] = elig
        result = await send_notice_to_telegram(chat_id, n_dict, scored)
        if result.get("ok"):
            sent += 1

    return {"sent": sent, "skipped": skipped, "chat_id": chat_id}
