"""ESPN public site API: site.api.espn.com/apis/site/v2/sports/<league>/teams/<id>/schedule

Source options: league (e.g. soccer/usa.nwsl), team_id, sport, gender,
venues {"<venue name substring>": [lat, lon]} for home-venue pins.
"""
from __future__ import annotations

from datetime import datetime

from common import CHICAGO, http_get, event, norm_sport

API = "https://site.api.espn.com/apis/site/v2/sports"


def fetch(src: dict, ctx: dict) -> list[dict]:
    url = f"{API}/{src['league']}/teams/{src['team_id']}/schedule"
    events = http_get(url, params={"fixture": "true"}).json().get("events", [])
    out = []
    for ev in events:
        comp = ev["competitions"][0]
        state = (ev.get("status") or comp.get("status") or {}).get("type", {}).get("state")
        if state == "post":
            continue
        out.append(_to_event(ev, comp, src))
    return out


def _to_event(ev, comp, src):
    teams = {c["homeAway"]: c["team"] for c in comp["competitors"]}
    home = teams.get("home", {}).get("id") == str(src["team_id"])
    start = datetime.fromisoformat(ev["date"].replace("Z", "+00:00")).astimezone(CHICAGO)
    tbd = bool(comp.get("timeValid") is False)
    v = comp.get("venue") or {}
    city = ", ".join(x for x in ((v.get("address") or {}).get("city"), (v.get("address") or {}).get("state")) if x)
    venue = " / ".join(x for x in (v.get("fullName"), city) if x)
    lat = lon = None
    for name, (la, lo) in (src.get("venues") or {}).items():
        if name.lower() in venue.lower():
            lat, lon = la, lo
            break
    title = (f"{teams['home']['displayName']} vs {teams['away']['displayName']}" if home
             else f"{teams['away']['displayName']} at {teams['home']['displayName']}")
    link = next((l["href"] for l in ev.get("links", []) if "summary" in l.get("rel", [])), src.get("link", ""))
    return event(
        uid=f"{src['id']}:{ev['id']}",
        title=title, sport=norm_sport(src.get("sport", "Other")), gender=src.get("gender", "Coed/Other"),
        level="Pro", start=start.date() if tbd else start, all_day=tbd,
        location=venue, lat=lat, lon=lon, url=link,
        home_away="home" if home else "away", teams=[src["name"]], src=src["id"],
    )
