"""HockeyTech leagues (AHL, ECHL, USHL, OHL...): lscluster.hockeytech.com modulekit feed.

Source options: client_code (e.g. ahl), key (the public key the league's own
stats pages use), team_id, sport (default Ice Hockey),
venues {"<venue name substring>": [lat, lon]} for home-arena pins.
Pulls every current/upcoming season (regular season + playoffs, not all-star).
"""
from __future__ import annotations

from datetime import datetime

from common import http_get, event, norm_sport

FEED = "https://lscluster.hockeytech.com/feed/"


def fetch(src: dict, ctx: dict) -> list[dict]:
    base = {"feed": "modulekit", "key": src["key"], "client_code": src["client_code"], "fmt": "json", "lang": "en"}
    today = ctx["now"].date().isoformat()
    seasons = http_get(FEED, params={**base, "view": "seasons"}).json()["SiteKit"]["Seasons"]
    current = [s for s in seasons if s.get("end_date", "") >= today and "all-star" not in s["season_name"].lower()]
    out = []
    for season in current:
        games = http_get(FEED, params={**base, "view": "schedule", "team_id": src["team_id"],
                                       "season_id": season["season_id"]}).json()["SiteKit"]["Schedule"]
        for g in games:
            if g.get("final") == "1" or g.get("if_necessary") == "1":
                continue
            out.append(_to_event(g, src))
    return out


def _to_event(g, src):
    home = g["home_team"] == str(src["team_id"])
    start = datetime.fromisoformat(g["GameDateISO8601"])
    all_day = g.get("time_tbd") == "1" or g.get("date_tbd") == "1"
    venue = g.get("venue_name") or ""
    lat = lon = None
    if home:
        for name, (la, lo) in (src.get("venues") or {}).items():
            if name.lower() in venue.lower():
                lat, lon = la, lo
                break
    title = (f"{g['home_team_name']} vs {g['visiting_team_name']}" if home
             else f"{g['visiting_team_name']} at {g['home_team_name']}")
    e = event(
        uid=f"{src['id']}:{g['game_id']}",
        title=title, sport=norm_sport(src.get("sport", "Ice Hockey")), gender=src.get("gender", "Boys/Men"),
        level="Pro", start=start.date() if all_day else start, all_day=all_day,
        location=venue, lat=lat, lon=lon, url=src.get("link", ""),
        home_away="home" if home else "away", teams=[src["name"]], src=src["id"],
    )
    if g.get("tickets_url"):
        e["tickets"] = g["tickets_url"]
    return e
