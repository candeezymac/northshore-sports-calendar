# Local Sports Calendar (North Shore)

One page listing the free and cheap live sports around Deerfield, IL: high school games, Northwestern Olympic sports, local colleges and minor-league teams. Filter by sport, type, cost, level, distance and date, then view the results as a list or a calendar. It's meant for quick "want to go watch a game for an hour?" outings with the kids.

## How it works

```
sources.yaml ──► pipeline/fetch.py ──► data/events.json + data/status.json ──► index.html / app.js
                  (one adapter per                (upcoming ~120 days)          (static page, filters,
                   feed type)                                                    list + calendar views)
```

- **`sources.yaml`** lists every schedule source, the home location (used for distances) and the **cost rules**.
- **`pipeline/adapters/`** holds one small module per feed type:
  - `gobound.py`: Illinois high schools on GoBound, at `gobound.com/il/schools/<slug>/calendar/ical`. Feeds are tagged with sport, level, gender and GPS. Practices, facility bookings and non-athletic activities (band, debate…) are skipped.
  - `wmt.py`: college sites on the WMT platform, such as `nusports.com/website-api/schedule-events`.
  - `sidearm.py`: college sites on SIDEARM (Lake Forest College, Loyola, UIC, DePaul), via `/services/responsive-calendar.ashx`. One week per call, with sport, home/away, facility and tickets link.
  - `hockeytech.py`: HockeyTech hockey leagues (AHL Chicago Wolves; it also covers USHL, ECHL, etc.).
  - `espn.py`: ESPN's public team-schedule API (NWSL Chicago Stars FC).
  - `ics.py`: any generic iCal feed (most college/team sites).
  - `manual.py`: one-off events typed into `manual_events.yaml`.
- **De-duplication:** a game between two tracked schools (e.g. DHS vs HPHS) appears in both feeds. It's merged into one event that's tagged with both schools.
- **Resilience:** if a source fails, its events from the previous run are kept, and the error shows in the page footer under "Sources".
- **Cost:** feeds never include prices, so cost tiers (Free / $ / $$ / Unknown) come from the editable rules in `sources.yaml`. The rules say HS regular season is free, varsity football/basketball and IHSA postseason have a small gate fee, most NU Olympic sports are free, and NU football/basketball are ticketed.

## Run locally

```bash
python3 -m venv .venv && .venv/bin/pip install -r pipeline/requirements.txt
.venv/bin/python pipeline/fetch.py            # refresh all sources
.venv/bin/python pipeline/fetch.py deerfield  # refresh just one source
./start.sh                                    # http://localhost:8000
```

Don't open `index.html` by double-clicking. The page loads its data with `fetch()`, which doesn't work from `file://`.

## Refreshing the live site

GitHub Actions (`.github/workflows/refresh.yml`) runs the pipeline nightly, and on demand from the repo's **Actions → Refresh schedules → Run workflow** button. It commits the new `data/` and GitHub Pages redeploys.

## Adding a source

- **Another high school:** find it on gobound.com, then add a line to `sources.yaml` with its slug (the part after `/schools/`).
- **A college/team with an iCal feed:** add `type: ics` with `url:`, plus optional `sport:`, `home_venue:` (lat/lon, so distance works) and `home_regex:`.
- **A one-off event:** add it to `manual_events.yaml`.

## Page features

- Filters: When, Distance from Deerfield, Cost, Type, Level (Varsity by default), Boys/Girls, Sport, School/Team, and text search. Counts on each chip show how many events that choice would give.
- Filters live in the URL, so a filtered view can be bookmarked or shared.
- List view grouped by day, or a calendar view (month grid / month list). The calendar ignores "When" and has its own month navigation.
- **Map view** (Leaflet + OpenStreetMap tiles): one dot per venue, sized by how many games it hosts and colored by type, with a dashed ring for the distance filter. Click a dot to see its games; click a game for details. Events with no known location (e.g. Northwestern away games) aren't shown on the map.
- Each event's detail card has a map link, the event page link, and an **Add to my calendar** button (.ics download).

## Live site

https://candeezymac.github.io/northshore-sports-calendar/ (GitHub Pages from `main`, root folder).

## Roadmap

1. ✅ MVP: 8 North Shore high schools (GoBound) + Northwestern.
2. ✅ Local colleges: Lake Forest College, Loyola, UIC, DePaul.
3. ✅ Pro/minor (part 1): Chicago Wolves (AHL), Chicago Stars FC (NWSL).
4. **Revisit ~Jan–Feb 2027:** Chicago Dogs, Schaumburg Boomers, Windy City ThunderBolts, Chicago Fire II. None had a clean feed as of 2026-10-05, and their seasons start in May, beyond the 120-day window. Likely options are scraping the Boomers' schedule pages, the Frontier League stats on pro.iscorecentral.com, or adding games via `manual_events.yaml`.
