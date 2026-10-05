"""Pull every source in sources.yaml -> data/events.json + data/status.json.

Run:  .venv/bin/python pipeline/fetch.py            (all sources)
      .venv/bin/python pipeline/fetch.py deerfield  (just one, for testing)

A failing source never breaks the run: its events from the previous run are
carried forward and the error is recorded in status.json.
"""
from __future__ import annotations

import importlib
import json
import math
import re
import sys
import traceback
from datetime import datetime, timedelta
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from common import CHICAGO  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def main(only: list[str]) -> None:
    cfg = yaml.safe_load((ROOT / "sources.yaml").read_text())
    now = datetime.now(CHICAGO)
    ctx = {"now": now, "root": ROOT}
    prev = _load_json(DATA / "events.json", {}).get("events", [])
    prev_status = {s["id"]: s for s in _load_json(DATA / "status.json", {}).get("sources", [])}

    sources = [s for s in cfg["sources"] if s.get("enabled", True)]
    by_id, status = {}, []
    for src in sources:
        if only and src["id"] not in only:
            # keep previous data for sources we didn't re-run
            _merge(by_id, [e for e in prev if src["id"] in e["src"]], src, keep_src=True)
            status.append(prev_status.get(src["id"], _status(src, "skipped", 0)))
            continue
        try:
            adapter = importlib.import_module(f"adapters.{src['type']}")
            events = adapter.fetch(src, ctx)
            _merge(by_id, events, src)
            status.append(_status(src, "ok", len(events), now=now))
            print(f"  ok    {src['id']:<16} {len(events):>5} events")
        except Exception as e:  # noqa: BLE001 -- one bad source shouldn't stop the rest
            stale = [ev for ev in prev if src["id"] in ev["src"]]
            _merge(by_id, stale, src, keep_src=True)
            last_ok = prev_status.get(src["id"], {}).get("last_ok")
            status.append(_status(src, "error", len(stale), error=f"{type(e).__name__}: {e}", last_ok=last_ok))
            print(f"  ERROR {src['id']:<16} {type(e).__name__}: {e}  (kept {len(stale)} previous)")
            traceback.print_exc(limit=2, file=sys.stderr)

    # window: from start of today through window_days ahead
    lo = now.replace(hour=0, minute=0, second=0, microsecond=0).date().isoformat()
    hi = (now + timedelta(days=cfg.get("window_days", 120))).date().isoformat()
    home = cfg["home"]
    events = []
    for e in by_id.values():
        if not (lo <= e["start"][:10] <= hi):
            continue
        if "lat" in e:  # carried-forward events from a previous run already have miles
            e["miles"] = _miles(home, e.pop("lat"), e.pop("lon"))
        if "cost" not in e:
            e["cost"], e["cost_note"] = _cost(e, cfg.get("cost_rules", []))
        events.append(e)
    events.sort(key=lambda e: (e["start"], e["title"]))

    DATA.mkdir(exist_ok=True)
    _write(DATA / "events.json", {"generated": now.isoformat(timespec="seconds"), "home": home,
                                  "count": len(events), "events": events})
    _write(DATA / "status.json", {"generated": now.isoformat(timespec="seconds"), "sources": status})
    ok = sum(1 for s in status if s["state"] == "ok")
    print(f"\n{len(events)} events in window ({lo} .. {hi}); {ok}/{len(status)} sources ok")


def _merge(by_id: dict, events: list[dict], src: dict, keep_src: bool = False) -> None:
    """Dedupe on event id; a game in two schools' feeds keeps both in `teams`/`src`."""
    for e in events:
        if not keep_src:
            e.setdefault("category", src["category"])
        cur = by_id.get(e["id"])
        if cur is None:
            by_id[e["id"]] = e
            continue
        for k in ("src", "teams"):
            cur[k] = sorted(set(cur[k]) | set(e[k]))
        if not cur.get("home_away") and e.get("home_away"):
            cur["home_away"] = e["home_away"]


def _cost(e: dict, rules: list[dict]) -> tuple[str, str]:
    for r in rules:
        if "category" in r and r["category"] != e["category"]:
            continue
        if "source" in r and r["source"] not in e["src"]:
            continue
        if "sport" in r:
            sports = r["sport"] if isinstance(r["sport"], list) else [r["sport"]]
            if e["sport"] not in sports:
                continue
        if "level" in r and r["level"] != e["level"]:
            continue
        if "title_regex" in r and not re.search(r["title_regex"], e["title"]):
            continue
        return r["tier"], r.get("note", "")
    return "Unknown", ""


def _miles(home: dict, lat, lon):
    if lat is None or lon is None:
        return None
    p1, p2 = math.radians(home["lat"]), math.radians(lat)
    dp, dl = p2 - p1, math.radians(lon - home["lon"])
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(3958.8 * 2 * math.asin(math.sqrt(a)), 1)


def _status(src, state, count, now=None, error=None, last_ok=None):
    return {"id": src["id"], "name": src["name"], "category": src["category"], "state": state,
            "count": count, "error": error,
            "last_ok": now.isoformat(timespec="seconds") if now else last_ok}


def _load_json(p: Path, default):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return default


def _write(p: Path, obj) -> None:
    p.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main(sys.argv[1:])
