# CLAUDE.md

See README.md for the full picture. Quick notes:

- Static site (index.html/app.js/styles.css, vanilla JS + FullCalendar from jsDelivr) + Python pipeline in `pipeline/`.
- Python deps live in `.venv` (local Python is 3.9, so keep code 3.9-compatible; CI uses 3.12). Run `.venv/bin/python -W ignore pipeline/fetch.py`.
- Serve with `./start.sh` (port 8000). Never test via file://.
- New sources go in `sources.yaml`. Only write a new adapter if no existing `type` fits. Each adapter returns `common.event(...)` dicts.
- `data/` is generated; it's committed because Pages serves it. Don't hand-edit it.
- Cost tiers come from `cost_rules` in sources.yaml (first match wins). Keep notes honest that they're estimates.
- Project log lives in the Notion page "Local sports calendar project" (Log entries most-recent-first).
