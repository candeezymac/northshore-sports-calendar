"""Generic iCal feed (Sidearm/Presto college sites, team calendars).

Source options: url (required), sport (fixed sport if the feed is one team),
gender, level (default Varsity), home_venue {name, lat, lon}, home_regex (a
regex on LOCATION that means "home", so home games get the venue's coordinates).
"""
from __future__ import annotations

import re
from datetime import date, datetime

import icalendar

from common import http_get, event, norm_gender, norm_level, norm_sport


def fetch(src: dict, ctx: dict) -> list[dict]:
    cal = icalendar.Calendar.from_ical(http_get(src["url"]).content)
    hv = src.get("home_venue", {})
    out = []
    for ve in cal.walk("VEVENT"):
        if str(ve.get("STATUS", "")).upper() == "CANCELLED":
            continue
        title = str(ve.get("SUMMARY", "")).strip()
        start = ve.decoded("DTSTART")
        end = ve.decoded("DTEND") if ve.get("DTEND") else None
        all_day = isinstance(start, date) and not isinstance(start, datetime)
        location = str(ve.get("LOCATION", ""))

        sport = src.get("sport") or _guess_sport(title + " " + str(ve.get("CATEGORIES", "")))
        home = bool(src.get("home_regex") and re.search(src["home_regex"], location, re.I))
        lat = lon = None
        if ve.get("GEO"):
            g = ve.get("GEO")
            lat, lon = g.latitude, g.longitude
        elif home and hv:
            lat, lon = hv.get("lat"), hv.get("lon")

        out.append(event(
            uid=f"{src['id']}:{ve.get('UID') or title + str(start)}",
            title=title, sport=norm_sport(sport),
            gender=norm_gender(src.get("gender") or title),
            level=norm_level(src.get("level", "Varsity")),
            start=start, end=end, all_day=all_day,
            location=location, lat=lat, lon=lon,
            url=str(ve.get("URL", "")) or src.get("link", ""),
            home_away="home" if home else "",
            teams=[src["name"]], src=src["id"],
        ))
    return out


def _guess_sport(text: str) -> str:
    from common import SPORTS
    low = re.sub(r"[^a-z ]", "", text.lower())
    for key in sorted(SPORTS, key=len, reverse=True):
        if key in low.replace(" ", ""):
            return key
    return "Other"
