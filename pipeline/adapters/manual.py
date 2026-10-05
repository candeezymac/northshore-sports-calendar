"""Hand-entered one-off events from manual_events.yaml."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import yaml

from common import CHICAGO, event, norm_gender, norm_level, norm_sport


def fetch(src: dict, ctx: dict) -> list[dict]:
    path = Path(ctx["root"]) / src.get("file", "manual_events.yaml")
    items = yaml.safe_load(path.read_text()) or []
    out = []
    for i, it in enumerate(items):
        start = _dt(it["start"])
        e = event(
            uid=f"manual:{it.get('id') or i}:{it['title']}",
            title=it["title"], sport=norm_sport(it.get("sport", "Other")),
            gender=norm_gender(it.get("gender", "")), level=norm_level(it.get("level", "Varsity")),
            start=start, end=_dt(it["end"]) if it.get("end") else None,
            all_day=not isinstance(start, datetime),
            location=it.get("location", ""), lat=it.get("lat"), lon=it.get("lon"),
            url=it.get("url", ""), teams=[it.get("team", src["name"])], src=src["id"],
        )
        e["category"] = it.get("category", src["category"])
        if it.get("cost"):
            e["cost"], e["cost_note"] = it["cost"], it.get("cost_note", "")
        out.append(e)
    return out


def _dt(v):
    if isinstance(v, datetime):
        return v.replace(tzinfo=CHICAGO) if v.tzinfo is None else v
    if isinstance(v, str):
        d = datetime.fromisoformat(v)
        return d.replace(tzinfo=CHICAGO) if "T" in v else d.date()
    return v  # a date
