"""SIDEARM Sports college sites (goforesters.com, loyolaramblers.com, ...).

Uses /services/responsive-calendar.ashx, which returns one week of events per
call (local Chicago times) with sport, home/away indicator, facility and a
tickets link. Richer than the site's calendar.ics feed.

Source options: base_url, home_venue {name, lat, lon} (default for home games),
facilities {"<facility title>": [lat, lon]} (overrides for specific venues).
"""
from __future__ import annotations

from datetime import datetime, timedelta

from common import CHICAGO, http_get, event, norm_gender, norm_sport


def fetch(src: dict, ctx: dict) -> list[dict]:
    base = src["base_url"].rstrip("/")
    end = ctx["now"] + timedelta(days=ctx.get("window_days", 120))
    day, seen, out = ctx["now"], set(), []
    while day <= end:
        weeks = http_get(f"{base}/services/responsive-calendar.ashx", params={
            "type": "events", "sport": 0, "location": "all", "date": day.strftime("%m/%d/%Y"),
        }).json()
        for d in weeks or []:
            for r in d.get("events") or []:
                if r["id"] in seen:
                    continue
                seen.add(r["id"])
                e = _to_event(r, src, base)
                if e:
                    out.append(e)
        day += timedelta(days=7)
    return out


# When a site's sport name has no "Men's/Women's", these college sports are single-gender.
DEFAULT_GENDER = {"Softball": "Girls/Women", "Field Hockey": "Girls/Women", "Volleyball": "Girls/Women",
                  "Baseball": "Boys/Men", "Football": "Boys/Men"}


def _to_event(r, src, base):
    if (r.get("status") or "A") != "A" or r.get("noplay_text"):  # canceled / postponed
        return None
    sport_name = (r.get("sport") or {}).get("title", "")
    time_txt = (r.get("time") or "").strip().upper()
    start = datetime.fromisoformat(r["date"]).replace(tzinfo=CHICAGO)
    all_day = not time_txt or "TBA" in time_txt or "TBD" in time_txt or "ALL DAY" in time_txt

    ind = r.get("location_indicator") or ""
    home_away = {"H": "home", "A": "away", "N": "neutral"}.get(ind, "")
    opp = (r.get("opponent") or {}).get("title") or "TBA"
    prep = r.get("at_vs") or ("vs" if home_away == "home" else "at")
    title = f"{src['name']} {prep} {opp}"

    fac = (r.get("facility") or {}).get("title") or ""
    location = " / ".join(x for x in (fac, r.get("location") or "") if x)
    lat = lon = None
    if home_away == "home":
        coords = (src.get("facilities") or {}).get(fac)
        hv = src.get("home_venue") or {}
        lat, lon = coords if coords else (hv.get("lat"), hv.get("lon"))

    sport = norm_sport(sport_name)
    gender = norm_gender(sport_name)
    if gender == "Coed/Other":
        gender = DEFAULT_GENDER.get(sport, gender)

    tickets = ((r.get("media") or {}).get("tickets") or {}).get("url")
    e = event(
        uid=f"{src['id']}:{r['id']}",
        title=title, sport=sport, gender=gender, level="Varsity",
        start=start.date() if all_day else start, all_day=all_day,
        location=location, lat=lat, lon=lon,
        url=f"{base}/calendar.aspx?id={r['id']}",
        home_away=home_away, teams=[src["name"]], src=src["id"],
    )
    if tickets:
        e["tickets"] = tickets
    return e
