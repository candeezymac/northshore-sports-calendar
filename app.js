/* Local Sports Calendar: loads data/events.json, filters it, renders list / calendar / map. */
"use strict";

const TZ = "America/Chicago";
const PAGE = 250; // list items rendered before "Show more"

const ORDER = {
  cost: ["Free", "$", "$$", "Unknown"],
  cat: ["High School", "College", "Pro / Minor", "Other"],
  level: ["Varsity", "Pro", "JV", "Frosh/Soph", "Other"],
  gender: ["Boys/Men", "Girls/Women", "Coed/Other"],
};
const WHEN = [["today", "Today"], ["weekend", "This weekend"], ["7", "Next 7 days"], ["30", "Next 30 days"], ["all", "All"]];
const DIST = [["5", "≤ 5 mi"], ["10", "≤ 10 mi"], ["15", "≤ 15 mi"], ["25", "≤ 25 mi"], ["any", "Any"]];
const COST_LABEL = { Free: "Free", $: "$ cheap", $$: "$$ ticketed", Unknown: "Cost ?" };
const DEFAULTS = { when: "30", dist: "15", level: ["Varsity", "Pro"] };
const MULTI = ["cost", "cat", "level", "gender", "sport", "team"];

const EMOJI = {
  Basketball: "🏀", Football: "🏈", "Flag Football": "🏈", Soccer: "⚽", Volleyball: "🏐",
  Baseball: "⚾", Softball: "🥎", Tennis: "🎾", Golf: "⛳", Lacrosse: "🥍", Wrestling: "🤼",
  "Swimming & Diving": "🏊", "Cross Country": "🏃", "Track & Field": "🏃", "Field Hockey": "🏑",
  "Ice Hockey": "🏒", Gymnastics: "🤸", Bowling: "🎳", Badminton: "🏸", Fencing: "🤺",
  "Water Polo": "🤽", "Cheer & Dance": "📣", Rowing: "🚣",
};
const emoji = (s) => EMOJI[s] || "🏅";

let ALL = [], HOME = null, state = {}, view = "list", shown = PAGE, calendar = null;
const $ = (s) => document.querySelector(s);

/* ---------- dates ---------- */
const todayKey = () => new Date().toLocaleDateString("en-CA", { timeZone: TZ }); // YYYY-MM-DD
function addDays(key, n) {
  const d = new Date(key + "T12:00:00Z"); d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}
function whenRange(w) {
  const t = todayKey();
  if (w === "today") return [t, t];
  if (w === "7") return [t, addDays(t, 6)];
  if (w === "30") return [t, addDays(t, 29)];
  if (w === "weekend") {
    const dow = new Date(t + "T12:00:00Z").getUTCDay(); // 0 Sun .. 6 Sat
    if (dow === 0) return [t, t];
    const fri = dow <= 5 ? addDays(t, 5 - dow) : addDays(t, -1);
    return [fri < t ? t : fri, addDays(fri, 2)];
  }
  return ["0000", "9999"];
}
const fmtDay = (key) => new Date(key + "T12:00:00Z").toLocaleDateString("en-US",
  { weekday: "long", month: "short", day: "numeric", timeZone: "UTC" });
const fmtTime = (e) => e.all_day ? "TBA" : new Date(e.start).toLocaleTimeString("en-US",
  { hour: "numeric", minute: "2-digit", timeZone: TZ });

/* ---------- state <-> URL ---------- */
function readHash() {
  const p = new URLSearchParams(location.hash.slice(1));
  const s = { when: p.get("when") || DEFAULTS.when, dist: p.get("dist") || DEFAULTS.dist, q: p.get("q") || "" };
  for (const k of MULTI) {
    s[k] = new Set(p.has(k) ? p.get(k).split("|").filter(Boolean) : DEFAULTS[k] || []);
  }
  view = ["cal", "map"].includes(p.get("view")) ? p.get("view") : "list";
  return s;
}
function writeHash() {
  const p = new URLSearchParams();
  p.set("when", state.when); p.set("dist", state.dist);
  for (const k of MULTI) {
    const v = [...state[k]].join("|");
    const d = (DEFAULTS[k] || []).join("|");
    if (v !== d) p.set(k, v);
  }
  if (state.q) p.set("q", state.q);
  if (view !== "list") p.set("view", view);
  history.replaceState(null, "", "#" + p.toString());
}

/* ---------- filtering ---------- */
function matches(e, skip) {
  const s = state;
  if (skip !== "when" && view !== "cal") { // the calendar has its own month navigation
    const [lo, hi] = whenRange(s.when); const d = e.start.slice(0, 10);
    if (d < lo || d > hi) return false;
  }
  if (skip !== "dist" && s.dist !== "any" && (e.miles == null || e.miles > +s.dist)) return false;
  if (skip !== "cost" && s.cost.size && !s.cost.has(e.cost)) return false;
  if (skip !== "cat" && s.cat.size && !s.cat.has(e.category)) return false;
  if (skip !== "level" && s.level.size && !s.level.has(e.level)) return false;
  if (skip !== "gender" && s.gender.size && !s.gender.has(e.gender)) return false;
  if (skip !== "sport" && s.sport.size && !s.sport.has(e.sport)) return false;
  if (skip !== "team" && s.team.size && !e.teams.some((t) => s.team.has(t))) return false;
  if (s.q) {
    const hay = (e.title + " " + e.location + " " + e.teams.join(" ") + " " + e.sport).toLowerCase();
    if (!s.q.toLowerCase().split(/\s+/).every((w) => hay.includes(w))) return false;
  }
  return true;
}
const fieldOf = { cost: "cost", cat: "category", level: "level", gender: "gender", sport: "sport" };
function facetCounts(key) {
  const c = {};
  for (const e of ALL) {
    if (!matches(e, key)) continue;
    const vals = key === "team" ? e.teams : [e[fieldOf[key]]];
    for (const v of vals) c[v] = (c[v] || 0) + 1;
  }
  return c;
}

/* ---------- filter chips ---------- */
let OPTIONS = {};
function buildOptions(teamOrder) {
  const uniq = (f) => [...new Set(ALL.flatMap(f))];
  const byOrder = (key, vals) => vals.sort((a, b) => ORDER[key].indexOf(a) - ORDER[key].indexOf(b));
  OPTIONS = {
    cost: byOrder("cost", uniq((e) => [e.cost])),
    cat: byOrder("cat", uniq((e) => [e.category])),
    level: byOrder("level", uniq((e) => [e.level])),
    gender: byOrder("gender", uniq((e) => [e.gender])),
    sport: uniq((e) => [e.sport]).sort(),
    team: uniq((e) => e.teams).sort((a, b) => (teamOrder.indexOf(a) + 1 || 99) - (teamOrder.indexOf(b) + 1 || 99) || a.localeCompare(b)),
  };
}
function renderChips() {
  for (const box of document.querySelectorAll(".chips")) {
    const key = box.dataset.key;
    let html = "";
    if (key === "when" || key === "dist") {
      for (const [v, label] of key === "when" ? WHEN : DIST) {
        html += `<button class="chip" data-v="${v}" aria-pressed="${state[key] === v}">${label}</button>`;
      }
    } else {
      const counts = facetCounts(key);
      for (const v of OPTIONS[key]) {
        const n = counts[v] || 0;
        const label = key === "cost" ? COST_LABEL[v] || v : key === "sport" ? `${emoji(v)} ${v}` : v;
        html += `<button class="chip" data-v="${esc(v)}" aria-pressed="${state[key].has(v)}"${n ? "" : ' style="opacity:.45"'}>${esc(label)}<span class="n">${n}</span></button>`;
      }
    }
    box.innerHTML = html;
  }
  const active = MULTI.filter((k) => state[k].size).length + (state.q ? 1 : 0);
  $("#active-count").textContent = active || "";
}
function onChip(ev) {
  const btn = ev.target.closest(".chip"); if (!btn) return;
  const key = btn.parentElement.dataset.key, v = btn.dataset.v;
  if (key === "when" || key === "dist") state[key] = v;
  else state[key].has(v) ? state[key].delete(v) : state[key].add(v);
  update();
}

/* ---------- list view ---------- */
function renderList(events) {
  if (!events.length) {
    $("#list").innerHTML = `<div class="empty">No games match these filters.<br>Try a wider distance, more days, or more levels.</div>`;
    return;
  }
  let html = "", day = "";
  for (const e of events.slice(0, shown)) {
    const d = e.start.slice(0, 10);
    if (d !== day) { html += (day ? "</div>" : "") + `<div class="day"><h2>${fmtDay(d)}</h2>`; day = d; }
    const lvl = e.category === "High School" ? `<span class="tag">${e.level}</span>` : "";
    html += `<button class="card" data-id="${esc(e.id)}">
      <div class="time">${fmtTime(e)}<small>${emoji(e.sport)}</small></div>
      <div class="what"><div class="t">${esc(e.title)}</div>
        <div class="meta">${lvl}${esc(genderWord(e))} ${esc(e.sport)} · ${esc(e.location || "Location TBA")}</div></div>
      <div class="badges"><span class="badge c-${e.cost}">${COST_LABEL[e.cost]}</span>${e.miles != null ? `<span class="miles">${e.miles} mi</span>` : ""}</div>
    </button>`;
  }
  html += "</div>";
  if (events.length > shown) html += `<button class="more" id="more">Show more (${events.length - shown} left)</button>`;
  $("#list").innerHTML = html;
}
const genderWord = (e) => ({ "Boys/Men": e.category === "High School" ? "Boys" : "Men's", "Girls/Women": e.category === "High School" ? "Girls" : "Women's" })[e.gender] || "";

/* ---------- calendar view ---------- */
function renderCal(events) {
  if (!window.FullCalendar) { $("#cal").textContent = "Calendar library failed to load."; return; }
  const items = events.map((e) => ({
    id: e.id, title: `${emoji(e.sport)} ${e.title}`, start: e.start, end: e.end || undefined,
    allDay: e.all_day, classNames: ["c-" + e.cost],
  }));
  if (!calendar) {
    const narrow = matchMedia("(max-width: 700px)").matches;
    calendar = new FullCalendar.Calendar($("#cal"), {
      initialView: narrow ? "listMonth" : "dayGridMonth", timeZone: TZ, height: "auto",
      headerToolbar: { left: "prev,next today", center: "title", right: "dayGridMonth,listMonth" },
      buttonText: { today: "Today", dayGridMonth: "Month", listMonth: "List" },
      dayMaxEvents: 4, eventDisplay: "block",
      eventTimeFormat: { hour: "numeric", minute: "2-digit", meridiem: "narrow" },
      eventClick: (info) => { info.jsEvent.preventDefault(); openDetail(info.event.id); },
    });
    calendar.render();
  }
  calendar.removeAllEvents();
  calendar.addEventSource(items);
  calendar.updateSize();
}

/* ---------- map view ---------- */
const CAT_COLOR = { "High School": "#2f7ed8", College: "#8e44ad", "Pro / Minor": "#e67e22", Other: "#16a085" };
let map = null, mapLayer = null, mapDist = null, mapFitTo = null, autoFit = true, fitting = false;
function renderMap(events) {
  if (!window.L) { $("#map").textContent = "Map library failed to load."; return; }
  if (!map) {
    map = L.map("map", { scrollWheelZoom: false, zoomSnap: 0.25 }).setView([HOME.lat, HOME.lon], 11);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map);
    L.marker([HOME.lat, HOME.lon], { title: HOME.name, icon: L.divIcon({ className: "home-pin", html: "🏠", iconSize: [24, 24] }) })
      .bindTooltip(HOME.name.split(",")[0]).addTo(map);
    mapLayer = L.layerGroup().addTo(map);
    // Once the user pans/zooms, stop auto-fitting. Programmatic fits set `fitting`.
    map.on("dragstart", () => { autoFit = false; });
    map.on("zoomstart", () => { if (!fitting) autoFit = false; });
    map.on("moveend", () => { fitting = false; });
    // The map box can change size after first paint (phone layout, scrollbar, rotation).
    // Re-measure, and re-fit if the user hasn't moved the map yet.
    new ResizeObserver(() => { map.invalidateSize(); if (autoFit) fitMap(); }).observe($("#map"));
    $("#map").addEventListener("click", (ev) => {
      const b = ev.target.closest("[data-id]"); if (b) return openDetail(b.dataset.id);
      const v = ev.target.closest("[data-venue]");
      if (v) { state.q = v.dataset.venue; $("#q").value = state.q; view = "list"; shown = PAGE; update(); }
    });
    $("#map-legend").innerHTML = Object.entries(CAT_COLOR).map(([k, c]) => `<span><i style="background:${c}"></i>${k}</span>`).join("") +
      '<span class="hint">Bigger dot = more games. Click a dot for its schedule.</span>';
  }
  map.invalidateSize();
  mapLayer.clearLayers();

  // one dot per venue (events at the same coordinates)
  const venues = new Map();
  let noLoc = 0;
  for (const e of events) {
    if (e.lat == null) { noLoc++; continue; }
    const k = e.lat.toFixed(4) + "," + e.lon.toFixed(4);
    if (!venues.has(k)) venues.set(k, []);
    venues.get(k).push(e);
  }
  for (const evs of venues.values()) {
    const e0 = evs[0];
    const names = {}; for (const e of evs) if (e.location) names[e.location] = (names[e.location] || 0) + 1;
    const vname = Object.keys(names).sort((a, b) => names[b] - names[a])[0] || "Venue";
    const cats = new Set(evs.map((e) => e.category));
    const color = cats.size === 1 ? CAT_COLOR[e0.category] || CAT_COLOR.Other : "#555";
    const rows = evs.slice(0, 12).map((e) =>
      `<button class="pop-row" data-id="${esc(e.id)}"><b>${fmtShort(e)}</b> ${emoji(e.sport)} ${esc(e.title)} <span class="badge c-${e.cost}">${COST_LABEL[e.cost]}</span></button>`).join("");
    const more = evs.length > 12 ? `<button class="pop-more" data-venue="${esc(vname)}">+${evs.length - 12} more: see all in List view</button>` : "";
    L.circleMarker([e0.lat, e0.lon], {
      radius: Math.min(6 + Math.sqrt(evs.length) * 3, 22), color: "#fff", weight: 1.5, fillColor: color, fillOpacity: 0.85,
    }).bindPopup(`<div class="pop"><div class="pop-h">${esc(vname)}</div>
        <div class="pop-sub">${evs.length} game${evs.length === 1 ? "" : "s"}${e0.miles != null ? ` · ${e0.miles} mi from ${esc(HOME.name.split(",")[0])}` : ""}</div>${rows}${more}</div>`,
      { maxWidth: 340, minWidth: 240 })
      .bindTooltip(`${esc(vname)}: ${evs.length} game${evs.length === 1 ? "" : "s"}`)
      .addTo(mapLayer);
  }

  // distance ring for the current filter; re-fit when the distance changes
  if (state.dist !== "any") {
    L.circle([HOME.lat, HOME.lon], { radius: +state.dist * 1609.34, color: "#888", weight: 1, dashArray: "4 4", fill: false, interactive: false }).addTo(mapLayer);
  }
  if (mapDist !== state.dist) {
    mapDist = state.dist;
    autoFit = true;
    const pts = [...venues.values()].map((v) => [v[0].lat, v[0].lon]).concat([[HOME.lat, HOME.lon]]);
    mapFitTo = state.dist !== "any" ? L.latLng(HOME.lat, HOME.lon).toBounds(+state.dist * 1609.34 * 2)
      : pts.length > 1 ? L.latLngBounds(pts) : null;
  }
  // wait a frame so a just-unhidden map has its real size before fitting
  requestAnimationFrame(() => { map.invalidateSize(); if (autoFit) fitMap(); });
  return { venues: venues.size, noLoc };
}
function fitMap() {
  if (!mapFitTo || !map.getSize().x) return;
  fitting = true;
  map.fitBounds(mapFitTo, { padding: [10, 10], maxZoom: 13, animate: false });
  fitting = false;
}
const fmtShort = (e) => new Date(e.start.slice(0, 10) + "T12:00:00Z").toLocaleDateString("en-US",
  { weekday: "short", month: "numeric", day: "numeric", timeZone: "UTC" }) + " " + (e.all_day ? "" : fmtTime(e).replace(":00", "").replace(" ", "").toLowerCase());

/* ---------- detail dialog ---------- */
function openDetail(id) {
  const e = ALL.find((x) => x.id === id); if (!e) return;
  const when = `${fmtDay(e.start.slice(0, 10))}, ${e.all_day ? "time TBA" : fmtTime(e)}`;
  const map = e.location ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(e.location)}` : "";
  $("#d-body").innerHTML = `
    <h3 id="d-title">${emoji(e.sport)} ${esc(e.title)}</h3>
    <div class="meta">${esc(genderWord(e))} ${esc(e.sport)} · ${esc(e.level)} · ${esc(e.category)}</div>
    <dl>
      <dt>When</dt><dd>${when}</dd>
      <dt>Where</dt><dd>${esc(e.location || "TBA")}${e.miles != null ? ` · ${e.miles} mi away` : ""}${map ? ` · <a href="${map}" target="_blank" rel="noopener">Map</a>` : ""}</dd>
      <dt>Cost</dt><dd><span class="badge c-${e.cost}">${COST_LABEL[e.cost]}</span> ${esc(e.cost_note || "")}</dd>
      <dt>Teams</dt><dd>${esc(e.teams.join(", "))}${e.home_away ? ` (${e.home_away})` : ""}</dd>
    </dl>
    <div class="actions">
      ${e.url ? `<a class="btn primary" href="${esc(e.url)}" target="_blank" rel="noopener">Event page</a>` : ""}
      ${e.tickets ? `<a class="btn" href="${esc(e.tickets)}" target="_blank" rel="noopener">Tickets</a>` : ""}
      <button class="btn" id="ics">Add to my calendar</button>
    </div>`;
  $("#ics").onclick = () => downloadIcs(e);
  $("#detail").showModal();
}
function downloadIcs(e) {
  const stamp = (iso) => new Date(iso).toISOString().replace(/[-:]/g, "").replace(/\.\d+/, "");
  const dateOnly = (k) => k.slice(0, 10).replace(/-/g, "");
  const lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//local-sports-calendar//EN", "BEGIN:VEVENT",
    `UID:${e.id}@local-sports-calendar`, `DTSTAMP:${stamp(new Date().toISOString())}`];
  if (e.all_day) {
    lines.push(`DTSTART;VALUE=DATE:${dateOnly(e.start)}`, `DTEND;VALUE=DATE:${dateOnly(addDays(e.start.slice(0, 10), 1))}`);
  } else {
    const end = e.end || new Date(new Date(e.start).getTime() + 2 * 3600e3).toISOString();
    lines.push(`DTSTART:${stamp(e.start)}`, `DTEND:${stamp(end)}`);
  }
  const txt = (s) => String(s || "").replace(/([,;\\])/g, "\\$1").replace(/\n/g, "\\n");
  lines.push(`SUMMARY:${txt(emoji(e.sport) + " " + e.title + " (" + e.sport + ")")}`, `LOCATION:${txt(e.location)}`,
    `DESCRIPTION:${txt((e.cost_note || "") + (e.url ? "\n" + e.url : ""))}`, "END:VEVENT", "END:VCALENDAR");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([lines.join("\r\n")], { type: "text/calendar" }));
  a.download = (e.title.replace(/[^\w]+/g, "-").slice(0, 50) || "event") + ".ics";
  a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

/* ---------- main ---------- */
function update() {
  writeHash();
  renderChips();
  const events = ALL.filter((e) => matches(e));
  let count = `${events.length.toLocaleString()} event${events.length === 1 ? "" : "s"}`;
  $("#when-box").hidden = view === "cal";
  document.querySelectorAll(".seg button").forEach((b) => b.setAttribute("aria-selected", b.dataset.view === view));
  $("#list").hidden = view !== "list"; $("#cal").hidden = view !== "cal"; $("#map-wrap").hidden = view !== "map";
  if (view === "list") renderList(events);
  else if (view === "cal") { renderCal(events); count += " (all dates)"; }
  else {
    const r = renderMap(events);
    if (r) count += ` at ${r.venues} venue${r.venues === 1 ? "" : "s"}` + (r.noLoc ? ` (${r.noLoc} without a location not shown)` : "");
  }
  $("#count").textContent = count;
}
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

async function init() {
  let data, status;
  try {
    [data, status] = await Promise.all(["data/events.json", "data/status.json"].map((u) => fetch(u, { cache: "no-cache" }).then((r) => r.json())));
  } catch (err) {
    $("#count").textContent = "Couldn't load data/events.json. If opening locally, run ./start.sh instead of double-clicking.";
    return;
  }
  ALL = data.events;
  HOME = data.home;
  $("#home-name").textContent = data.home.name.split(",")[0];
  buildOptions(status.sources.map((s) => s.name));
  state = readHash();

  const gen = new Date(data.generated);
  const ok = status.sources.filter((s) => s.state === "ok").length;
  $("#updated").textContent = `Last updated ${gen.toLocaleString("en-US", { dateStyle: "medium", timeStyle: "short", timeZone: TZ })} · ${ok}/${status.sources.length} sources OK`;
  $("#sources").innerHTML = status.sources.map((s) =>
    `<li${s.state === "error" ? ' class="err"' : ""}>${esc(s.name)} (${esc(s.category)}): ${s.count} events${s.error ? ` · ⚠️ ${esc(s.error)}` : ""}</li>`).join("");

  document.querySelectorAll(".chips").forEach((b) => b.addEventListener("click", onChip));
  let t; $("#q").value = state.q;
  $("#q").addEventListener("input", (ev) => { clearTimeout(t); t = setTimeout(() => { state.q = ev.target.value.trim(); shown = PAGE; update(); }, 200); });
  $("#reset").onclick = () => { location.hash = ""; state = readHash(); $("#q").value = ""; update(); };
  $("#filters-toggle").onclick = () => {
    const open = $("#filters").classList.toggle("open");
    $("#filters-toggle").setAttribute("aria-expanded", open);
  };
  document.querySelector(".seg").onclick = (ev) => { const b = ev.target.closest("button"); if (b) { view = b.dataset.view; update(); } };
  $("#list").onclick = (ev) => {
    if (ev.target.id === "more") { shown += PAGE; update(); return; }
    const c = ev.target.closest(".card"); if (c) openDetail(c.dataset.id);
  };
  // shared/bookmarked links: react when only the #... part of the URL changes
  addEventListener("hashchange", () => { state = readHash(); $("#q").value = state.q; shown = PAGE; update(); });
  $("#detail").addEventListener("click", (ev) => { if (ev.target === $("#detail")) $("#detail").close(); });
  update();
}
init();
