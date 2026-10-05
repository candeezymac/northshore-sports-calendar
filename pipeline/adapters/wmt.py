"""WMT Digital athletics sites (e.g. nusports.com): /website-api/schedule-events JSON.

The API ignores date filters, so we page newest-first and stop once we're past today.
Datetimes are UTC; midnight Central with tba/all-day flags means "time TBA".
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from common import CHICAGO, http_get, event, norm_gender, norm_sport


def fetch(src: dict, ctx: dict) -> list[dict]:
    base = src["base_url"].rstrip("/")
    hv = src.get("home_venue", {})
    cutoff = ctx["now"] - timedelta(days=1)
    out, page = [], 1
    while page <= 40:
        data = http_get(f"{base}/website-api/schedule-events", params={
            "sort": "-datetime", "per_page": 100, "page": page, "include": "schedule.sport",
        }).json()
        rows = data.get("data", [])
        if not rows:
            break
        for r in rows:
            if not r.get("datetime"):
                continue
            start = datetime.fromisoformat(r["datetime"].replace("Z", "+00:00").replace(".000000", ""))
            if start < cutoff:
                return out
            if r.get("hide_from_all_sports_schedule") or r.get("status") in ("canceled", "cancelled", "postponed"):
                continue
            out.append(_to_event(r, start, src, hv, base))
        if page >= data.get("meta", {}).get("last_page", page):
            break
        page += 1
    return out


def _to_event(r, start, src, hv, base):
    sport_obj = ((r.get("schedule") or {}).get("sport") or {})
    sport_name = sport_obj.get("name", "")
    local = start.astimezone(CHICAGO)
    all_day = bool(r.get("is_all_day") or r.get("tba")) or (local.hour == 0 and local.minute == 0)

    venue = r.get("venue_type") or ""
    opp = r.get("opponent_name") or "TBA"
    if r.get("second_opponent_name"):
        opp += f" & {r['second_opponent_name']}"
    prep = "vs" if venue == "home" else (r.get("neutral_event_preposition") or "vs") if venue == "neutral" else "at"
    title = f"{src['name']} {prep} {opp}"

    lat = lon = None
    location = r.get("location") or ""
    if venue == "home" and hv:
        lat, lon = hv.get("lat"), hv.get("lon")
        location = location or hv.get("name", "")

    end = None
    if r.get("datetime_end"):
        end = datetime.fromisoformat(r["datetime_end"].replace("Z", "+00:00").replace(".000000", ""))

    return event(
        uid=f"{src['id']}:{r['id']}",
        title=title,
        sport=norm_sport(sport_name),
        gender=norm_gender(sport_obj.get("gender") or sport_name),
        level="Varsity",
        start=local.date() if all_day else local,
        end=end, all_day=all_day,
        location=location, lat=lat, lon=lon,
        url=f"{base}/sports/{sport_obj['slug']}/schedule" if sport_obj.get("slug") else f"{base}/calendar",
        home_away=venue,
        teams=[src["name"]],
        src=src["id"],
    )
