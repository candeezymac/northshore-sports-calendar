"""Shared helpers: HTTP, normalization of sport/level names, the event record."""
from __future__ import annotations

import re
import time
from datetime import date, datetime
from zoneinfo import ZoneInfo

import requests

CHICAGO = ZoneInfo("America/Chicago")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128 Safari/537.36 deerfield-sports-calendar")


def http_get(url: str, params: dict | None = None, retries: int = 2) -> requests.Response:
    last = None
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, params=params, headers={"User-Agent": UA}, timeout=45)
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            last = e
            time.sleep(2 * (attempt + 1))
    raise last


# Canonical sport names. Keys are lowercased, punctuation-free variants seen in feeds.
SPORTS = {
    "basketball": "Basketball", "football": "Football", "soccer": "Soccer",
    "volleyball": "Volleyball", "baseball": "Baseball", "softball": "Softball",
    "tennis": "Tennis", "golf": "Golf", "lacrosse": "Lacrosse", "wrestling": "Wrestling",
    "swimming": "Swimming & Diving", "swimmingdiving": "Swimming & Diving",
    "swimminganddiving": "Swimming & Diving", "diving": "Swimming & Diving",
    "crosscountry": "Cross Country", "crosscountrytrack": "Cross Country", "track": "Track & Field", "trackfield": "Track & Field",
    "trackandfield": "Track & Field", "indoortrackfield": "Track & Field",
    "outdoortrackfield": "Track & Field", "indoortrack": "Track & Field",
    "fieldhockey": "Field Hockey", "hockey": "Ice Hockey", "icehockey": "Ice Hockey",
    "gymnastics": "Gymnastics", "bowling": "Bowling", "badminton": "Badminton",
    "fencing": "Fencing", "waterpolo": "Water Polo", "cheer": "Cheer & Dance",
    "cheerleading": "Cheer & Dance", "dance": "Cheer & Dance", "rowing": "Rowing",
    "crew": "Rowing", "boysvolleyball": "Volleyball", "flagfootball": "Flag Football",
}


def norm_sport(raw: str) -> str:
    s = re.sub(r"(?i)\b(men'?s|women'?s|boys'?|girls'?|coed)\b", "", raw or "")
    key = re.sub(r"[^a-z]", "", s.lower())
    return SPORTS.get(key, s.strip().title() or "Other")


def norm_gender(raw: str) -> str:
    r = (raw or "").lower()
    if r in ("male", "boys", "men") or re.search(r"\b(boys|men'?s)\b", r):
        return "Boys/Men"
    if r in ("female", "girls", "women") or re.search(r"\b(girls|women'?s)\b", r):
        return "Girls/Women"
    return "Coed/Other"


def norm_level(raw: str) -> str:
    r = (raw or "").lower()
    if re.search(r"\bjv|junior varsity", r):
        return "JV"
    if "varsity" in r:
        return "Varsity"
    if re.search(r"fresh|frosh|soph|f/s", r):
        return "Frosh/Soph"
    return "Other"


def iso(dt: datetime | date) -> str:
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=CHICAGO)
        return dt.astimezone(CHICAGO).isoformat(timespec="minutes")
    return dt.isoformat()


def event(*, uid, title, sport, gender, level, start, end=None, all_day=False,
          location="", lat=None, lon=None, url="", home_away="", teams=None, src) -> dict:
    """One normalized event. `src` is the source id; `teams` = tracked schools/teams involved."""
    return {
        "id": uid, "title": title, "sport": sport, "gender": gender, "level": level,
        "start": iso(start), "end": iso(end) if end else None, "all_day": all_day,
        "location": location or "", "lat": lat, "lon": lon, "url": url,
        "home_away": home_away, "src": [src], "teams": teams or [],
    }
