"""Every memory and all of it, on a map, for us.

Ungated on purpose, so it is a local tool and never a route on the API: it
reads the database directly and binds to 127.0.0.1 only. Hidden memories are
shown, faded. A pin is a place; the list beside the map is every memory, and
the filter box narrows both.

    python -m pipeline.browse            # http://127.0.0.1:8765
    python -m pipeline.browse --port 9000
"""

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from sqlalchemy import text

from api.card import source_href
from pipeline.db import get_session

QUERY = """
SELECT m.id, m.summary, m.quote, m.quote_by, m.tags, m.layer, m.hidden,
       m.walk_score, m.extraction_confidence, m.happened_at, m.happened_precision,
       m.contrast_note, m.attribution, m.source_url, m.timestamp_start,
       m.links, m.enrichment, m.created_at, m.place_id,
       p.name AS place, ST_Y(p.coordinates::geometry) AS lat, ST_X(p.coordinates::geometry) AS lng,
       c.title, c.source_name, c.url AS content_url
FROM memories m
JOIN places p ON p.id = m.place_id
LEFT JOIN content c ON c.id = m.content_id
ORDER BY m.id DESC
"""

# The app's palette (mobile/src/theme.ts) and fonts; OSM's tiles, drained by a
# filter, stand in for Apple's mutedStandard: the map is a backdrop.
PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Memory Lane Admin</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Gloock&family=Newsreader:ital,opsz,wght@0,6..72,400;1,6..72,400&display=swap">
<style>
:root{--paper:#F6F1E7;--raised:#FFFCF6;--ink:#1E1626;--soft:#4A3F52;--faint:#6B6172;
  --rule:#E2D8CA;--quiet:#ECE4D7;--gold:#7E5E14;--goldline:rgba(184,142,54,.55);--seal:#1C6A4D;--danger:#9B2C2C}
@media (prefers-color-scheme:dark){:root{--paper:#14101A;--raised:#211A29;--ink:#F3ECE0;--soft:#C5BAC9;
  --faint:#9B90A3;--rule:#362C3F;--quiet:#2A2233;--gold:#E3BE6B;--goldline:rgba(227,190,107,.6);--seal:#4CC196;--danger:#F09A9A}}
*{box-sizing:border-box}
html,body{margin:0;height:100%;background:var(--paper);color:var(--ink);
  font:15px/1.4 ui-rounded,system-ui,-apple-system,sans-serif}
body{display:grid;grid-template-columns:420px 1fr}
#side{display:flex;flex-direction:column;height:100vh;border-right:1px solid var(--rule);min-width:0}
#map{height:100vh}
header{padding:16px 16px 10px;border-bottom:1px solid var(--rule)}
h1{font:28px Gloock,serif;margin:0 0 8px}
#q{width:100%;padding:10px 14px;border-radius:999px;border:1px solid var(--goldline);
  background:var(--raised);color:var(--ink);font:inherit;outline:none}
#count{color:var(--faint);font-size:13px;margin-top:6px}
#list,#detail{overflow:auto;flex:1}
.row{padding:12px 16px;border-bottom:1px solid var(--rule);cursor:pointer}
.row:hover{background:var(--raised)}
.row b{font:17px Gloock,serif;font-weight:400}
.row p{margin:4px 0 0;color:var(--soft);font:15px/1.35 Newsreader,serif;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.meta{color:var(--faint);font-size:13px}
.faded{opacity:.45}
.score{color:var(--gold);font-weight:600}
#detail{display:none;padding:0 0 24px}
#detail .back{position:sticky;top:0;background:var(--paper);padding:12px 16px;border-bottom:1px solid var(--rule);
  color:var(--gold);cursor:pointer;font-weight:500}
.mem{padding:16px;border-bottom:1px solid var(--rule)}
.mem h2{font:26px Gloock,serif;font-weight:400;margin:0 0 4px}
.story{font:18px/1.55 Newsreader,serif;white-space:pre-wrap;margin:12px 0}
.quote{border-left:3px solid var(--gold);padding:2px 0 2px 12px;margin:12px 0;
  font:italic 18px/1.45 Newsreader,serif}
.quote small{display:block;font:13px ui-rounded,system-ui;color:var(--faint);font-style:normal;margin-top:4px}
.chip{display:inline-block;padding:2px 9px;margin:2px 4px 2px 0;border-radius:999px;background:var(--quiet);
  font-size:12px;color:var(--soft)}
.chip.hidden{background:var(--danger);color:var(--paper)}
a{color:var(--gold)}
.pics img{width:100%;border-radius:10px;margin-top:8px;display:block}
.pics figcaption{font-size:12px;color:var(--faint)}
details{margin-top:10px} summary{cursor:pointer;color:var(--faint);font-size:13px}
pre{background:var(--raised);border:1px solid var(--rule);padding:8px;overflow:auto;font-size:12px;border-radius:8px}
.leaflet-container{background:var(--paper);font:inherit}
.leaflet-tile-pane{filter:grayscale(1) sepia(.18) contrast(.85) brightness(1.06)}
@media (prefers-color-scheme:dark){.leaflet-tile-pane{filter:invert(1) hue-rotate(180deg) grayscale(1) sepia(.2) brightness(.8) contrast(.9)}}
.leaflet-tooltip{font:15px Gloock,serif}
@media (max-width:800px){body{grid-template-columns:1fr;grid-template-rows:45vh 55vh}
  #map{height:45vh;order:-1}#side{height:55vh}}
</style></head><body>
<div id="side">
  <header><h1>Memory Lane</h1>
    <input id="q" placeholder="Filter: place, words, tag, source, 'hidden', 'score 10'" autofocus>
    <div id="count"></div></header>
  <div id="list"></div>
  <div id="detail"></div>
</div>
<div id="map"></div>
<script>
const MEMORIES = __DATA__;
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]);

const map = L.map('map', {preferCanvas: true}).setView([55.6761, 12.5683], 13);
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',
  {maxZoom: 19, attribution: '&copy; OpenStreetMap contributors'}).addTo(map);

const places = new Map();
for (const m of MEMORIES) {
  m.text = [m.place, m.summary, m.quote, m.quote_by, m.contrast_note, m.source_name, m.title,
    m.attribution, (m.tags || []).join(' '), m.layer, m.hidden ? 'hidden' : '', 'score ' + m.walk_score,
    '#' + m.id].join(' ').toLowerCase();
  if (m.lat == null) continue;
  if (!places.has(m.place_id)) places.set(m.place_id, {name: m.place, lat: m.lat, lng: m.lng, mems: []});
  places.get(m.place_id).mems.push(m);
}

for (const [id, p] of places) {
  p.marker = L.circleMarker([p.lat, p.lng], {radius: 6, weight: 1.5})
    .bindTooltip(esc(p.name), {direction: 'top', offset: [0, -6]})
    .on('click', () => openPlace(id)).addTo(map);
}

const meta = m => [
  m.walk_score != null ? `<span class=score>${m.walk_score}/12</span>` : '',
  m.happened_at ? esc(m.happened_at.slice(0, {year: 4, decade: 3}[m.happened_precision] || 10)) + (m.happened_precision === 'decade' ? '0s' : '') : '',
  esc(m.source_name), m.layer === 'stranger' ? 'filed by a person' : ''
].filter(Boolean).join(' · ');

function card(m) {
  const pics = (m.enrichment?.pictures || []).map(p =>
    `<figure><img src="${esc(p.url)}" loading=lazy><figcaption>${esc(p.caption)} · ${esc(p.author)} · ${esc(p.license)}</figcaption></figure>`).join('');
  const links = (m.links || []).map(l => `<a class=chip href="${esc(l.url)}" target=_blank>${esc(l.text)}</a>`).join('');
  return `<div class="mem${m.hidden ? ' faded' : ''}">
    <h2>${esc(m.place)}</h2>
    <div class=meta>#${m.id} · ${meta(m)}</div>
    <div>${m.hidden ? '<span class="chip hidden">hidden</span>' : ''}${(m.tags || []).map(t => `<span class=chip>#${esc(t)}</span>`).join('')}</div>
    <div class=story>${esc(m.summary)}</div>
    ${m.quote ? `<div class=quote>${esc(m.quote)}<small>${esc(m.quote_by)}</small></div>` : ''}
    ${m.contrast_note ? `<p class=meta><b>Then and now:</b> ${esc(m.contrast_note)}</p>` : ''}
    ${links ? `<div>${links}</div>` : ''}
    <p class=meta>${esc(m.title)}${m.attribution ? ' · ' + esc(m.attribution) : ''}
      ${m.link ? ` · <a href="${esc(m.link)}" target=_blank>source</a>` : ''}
      · confidence ${esc(m.extraction_confidence)} · created ${esc(m.created_at.slice(0, 10))}</p>
    <div class=pics>${pics}</div>
    <details><summary>Raw enrichment</summary><pre>${esc(JSON.stringify(m.enrichment, null, 2))}</pre></details>
  </div>`;
}

const list = document.getElementById('list'), detail = document.getElementById('detail');
let selected = null;

function style(p) {
  const shown = p.mems.some(m => m.shown);
  const allHidden = p.mems.every(m => m.hidden);
  const on = selected === p;
  p.marker.setStyle({
    radius: on ? 10 : 4 + Math.min(p.mems.length, 6),
    color: css('--paper'), fillColor: allHidden ? css('--faint') : on ? css('--seal') : css('--gold'),
    fillOpacity: shown ? (allHidden ? .5 : .9) : 0, opacity: shown ? 1 : 0, interactive: shown,
  });
  if (on) p.marker.bringToFront();
}

function filter() {
  const words = q.value.toLowerCase().split(/\\s+/).filter(Boolean);
  let n = 0;
  for (const m of MEMORIES) { m.shown = words.every(w => m.text.includes(w)); n += m.shown; }
  list.innerHTML = MEMORIES.filter(m => m.shown).slice(0, 400).map(m =>
    `<div class="row${m.hidden ? ' faded' : ''}" data-id="${m.id}"><b>${esc(m.place)}</b>
     <div class=meta>${meta(m)}</div><p>${esc(m.summary)}</p></div>`).join('');
  document.getElementById('count').textContent = `${n} of ${MEMORIES.length} memories` + (n > 400 ? ' · list shows 400' : '');
  places.forEach(style);
}

function openPlace(id, memId) {
  const p = places.get(id);
  const prev = selected; selected = p;
  if (prev) style(prev); style(p);
  const mems = memId ? [p.mems.find(m => m.id === memId), ...p.mems.filter(m => m.id !== memId)] : p.mems;
  detail.innerHTML = `<div class=back>‹ All memories</div>` +
    (mems.length > 1 ? `<div class="meta" style="padding:10px 16px 0">${mems.length} memories here</div>` : '') +
    mems.map(card).join('');
  detail.querySelector('.back').onclick = closeDetail;
  list.style.display = 'none'; detail.style.display = 'block'; detail.scrollTop = 0;
  map.flyTo([p.lat, p.lng], Math.max(map.getZoom(), 16), {duration: .6});
}

function closeDetail() {
  const prev = selected; selected = null; if (prev) style(prev);
  detail.style.display = 'none'; list.style.display = 'block';
}

list.onclick = e => {
  const row = e.target.closest('.row'); if (!row) return;
  const m = MEMORIES.find(m => m.id === +row.dataset.id);
  if (m.lat == null) { detail.innerHTML = '<div class=back>‹ All memories</div>' + card(m);
    detail.querySelector('.back').onclick = closeDetail; list.style.display = 'none'; detail.style.display = 'block'; return; }
  openPlace(m.place_id, m.id);
};
list.onmouseover = e => {
  const row = e.target.closest('.row'); if (!row) return;
  places.get(MEMORIES.find(m => m.id === +row.dataset.id).place_id)?.marker.openTooltip();
};
q.oninput = () => { closeDetail(); filter(); };
addEventListener('keydown', e => { if (e.key === 'Escape') closeDetail(); });
filter();
</script></body></html>"""


def _memory(row) -> dict:
    return {**row._mapping, "link": source_href(row)}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/":
            self.send_error(404)
            return
        with get_session() as session:
            rows = session.execute(text(QUERY)).all()
        # "</" escaped so a summary can never close the <script> it sits in.
        data = json.dumps([_memory(r) for r in rows], default=str, ensure_ascii=False)
        body = PAGE.replace("__DATA__", data.replace("</", "<\\/")).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    print(f"http://127.0.0.1:{args.port}")
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
