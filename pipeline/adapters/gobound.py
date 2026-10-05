"""GoBound (Illinois high schools): gobound.com/il/schools/<slug>/calendar/ical

SUMMARY looks like "Girls Tennis: Deerfield vs Highland Park (F/S)" -- away team
first, home team second. Invites/meets have no "vs" and just a meet name.
"""
from __future__ import annotations

import re
from datetime import date, datetime

import icalendar

from common import http_get, event, norm_gender, norm_level, norm_sport

# Activity keys that aren't spectator sports. Events with no key at all are
# facility bookings / practices (e.g. "NTA Practice") and are skipped too.
NON_SPORTS = {"academic", "band", "choir", "orchestra", "speech", "mentors", "theatre", "theater", "yearbook", "chess"}


def fetch(src: dict, ctx: dict) -> list[dict]:
    url = f"https://www.gobound.com/{src.get('state', 'il')}/schools/{src['slug']}/calendar/ical"
    cal = icalendar.Calendar.from_ical(http_get(url).content)
    out = []
    for ve in cal.walk("VEVENT"):
        if str(ve.get("STATUS", "")).upper() == "CANCELLED":
            continue
        key = str(ve.get("X-BND-ACTIVITYKEY", "")).lower()
        name = str(ve.get("X-BND-ACTIVITYNAME", ""))
        if not key or key in NON_SPORTS:
            continue
        summary = str(ve.get("SUMMARY", ""))
        body = summary.split(":", 1)[1].strip() if ":" in summary else summary
        title = re.sub(r"\s*\([^)]*\)\s*$", "", body).strip()  # drop trailing "(Varsity)"

        start = ve.decoded("DTSTART")
        end = ve.decoded("DTEND") if ve.get("DTEND") else None
        all_day = isinstance(start, date) and not isinstance(start, datetime)

        lat = lon = None
        if ve.get("GEO"):
            g = ve.get("GEO")
            lat, lon = (g.latitude, g.longitude) if hasattr(g, "latitude") else map(float, str(g).split(";"))
            if not lat and not lon:
                lat = lon = None

        level_raw = str(ve.get("X-BND-ACTIVITYLEVEL", ""))
        if not level_raw:  # some tournaments only carry the level in the summary
            m = re.search(r"\(([^)]*)\)\s*$", body)
            level_raw = m.group(1) if m else ""

        out.append(event(
            uid=f"gb:{ve.get('UID')}",
            title=title,
            sport="Flag Football" if "flag" in name.lower() else norm_sport(key),
            gender=norm_gender(str(ve.get("X-BND-ACTIVITYSEX", ""))),
            level=norm_level(level_raw),
            start=start, end=end, all_day=all_day,
            location=str(ve.get("LOCATION", "")),
            lat=lat, lon=lon,
            url=str(ve.get("URL", "")),
            home_away=_home_away(title, src),
            teams=[src["name"]],
            src=src["id"],
        ))
    return out


def _home_away(title: str, src: dict) -> str:
    if " vs " not in title:
        return ""
    home = title.rsplit(" vs ", 1)[1].lower()
    school = src["name"].lower().replace(" hs", "")
    return "home" if school in home or home in school else "away"
