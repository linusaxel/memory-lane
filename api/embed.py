"""The embeddable map - Phase 2. Two routes and no build step.

`/embed.js` is the snippet a customer pastes; it writes an <iframe> pointing at
`/embed`, which renders nearby memories and calls render_card on the server so
the attribution cannot be stripped. Why an iframe:
docs/10-decisions.md#the-embed-is-an-iframe-not-injected-markup.
"""

import json

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse, Response

router = APIRouter()

# ponytail: OSM's public tiles are fine for a demo and NOT fine for a customer's
# traffic - the OSMF usage policy forbids it and they can block without notice.
# DO NOT put this embed on a public host until this line changes.
#
# Reviewed 2026-09-20 and deliberately left alone: the embed has no users, and
# tiles are not its blocker - there is no public API host for the iframe to
# point at. Providers compared in docs/09-visual-design.md; Stadia Maps is one
# URL and a key, Protomaps is ~$3/mo of object storage. Both are a one-line
# change here, which is the whole reason this is a constant.
TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
TILE_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'

EMBED_JS = """(function () {
  var s = document.currentScript;
  var q = new URLSearchParams({
    lat: s.getAttribute('data-lat') || '',
    lng: s.getAttribute('data-lng') || '',
    radius_km: s.getAttribute('data-radius-km') || '2',
    layer: s.getAttribute('data-layer') || ''
  });
  var f = document.createElement('iframe');
  f.src = new URL('/embed?' + q, s.src).href;
  f.width = s.getAttribute('data-width') || '100%';
  f.height = s.getAttribute('data-height') || '480';
  f.style.border = '0';
  f.loading = 'lazy';
  f.title = 'Memory Lane map';
  s.parentNode.insertBefore(f, s);
})();"""

EMBED_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Memory Lane</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Figtree:wght@400;500&family=Fraunces:opsz,wght,SOFT,WONK@9..144,400,100,0&display=swap">
<style>
  :root {{ color-scheme: light dark; }}
  /* Typography only. `Canvas` and `color-scheme` stay: this widget lives in
     other people's pages and adapting to the host is the right behaviour -
     the card inside the panel carries the full palette. */
  html, body {{
    margin: 0; height: 100%;
    font-family: Figtree, system-ui, -apple-system, "Segoe UI", sans-serif;
  }}
  #map {{ position: absolute; inset: 0; }}
  /* z-index 600 is deliberate and is the attribution rule, not a stacking
     accident. Leaflet puts its panes at 400 and its controls at 800, so this
     sits above the tiles and markers and *below* the "Leaflet | (c) OpenStreetMap"
     credit - which has to stay visible whatever is on top of the map. It was
     already behaving this way by falling through to `auto`; saying it out loud
     stops the next person "fixing" the overlap by raising the card.
     ponytail: the credit then reads as part of the card, because the sheet
     covers the map's own bottom edge. The real fix is a flex column - map
     above, card below, map.invalidateSize() on toggle - which is worth doing
     the day the embed has a customer and not before. */
  #card {{
    position: absolute; inset: auto 0 0 0; max-height: 60%; overflow: auto;
    z-index: 600;
    background: Canvas; border-top: 1px solid rgba(128,128,128,.4);
    transform: translateY(100%); transition: transform .18s ease-out;
  }}
  #card[data-open] {{ transform: none; }}
  #card iframe {{ width: 100%; border: 0; display: block; min-height: 220px; }}
  #close {{
    position: sticky; top: 0; float: right; margin: .4rem; border: 0;
    background: transparent; font-size: 1.4rem; line-height: 1; cursor: pointer;
    color: inherit;
  }}
  #empty {{
    position: absolute; inset: 0; display: none; place-items: center; padding: 2rem;
    text-align: center; pointer-events: none;
  }}
  #empty[data-show] {{ display: grid; }}
  #empty p {{
    background: Canvas; padding: .6rem 1rem; border-radius: 999px; margin: 0;
    font-family: Fraunces, Georgia, "Times New Roman", serif; font-size: 1rem;
  }}
</style>
</head><body>
<div id="map"></div>
<div id="empty"><p>No memories recorded here yet.</p></div>
<div id="card"><button id="close" aria-label="Close">&times;</button><iframe title="Memory"></iframe></div>
<script>
  var CFG = {cfg};
  var map = L.map('map').setView([CFG.lat, CFG.lng], CFG.zoom);
  L.tileLayer({tile_url}, {{ attribution: {tile_attr}, maxZoom: 19 }}).addTo(map);

  var card = document.getElementById('card');
  var frame = card.querySelector('iframe');
  document.getElementById('close').onclick = function () {{ card.removeAttribute('data-open'); }};

  function show(id) {{
    frame.src = CFG.base + '/v1/memories/' + id + '/card';
    card.setAttribute('data-open', '');
  }}

  var url = CFG.base + '/v1/memories/nearby?lat=' + CFG.lat + '&lng=' + CFG.lng +
            '&radius_km=' + CFG.radius_km + (CFG.layer ? '&layer=' + CFG.layer : '');

  fetch(url).then(function (r) {{ return r.json(); }}).then(function (data) {{
    var memories = (data.memories || []).filter(function (m) {{ return m.place.coordinates; }});
    if (!memories.length) {{
      document.getElementById('empty').setAttribute('data-show', '');
      return;
    }}
    var group = [];
    memories.forEach(function (m) {{
      var c = m.place.coordinates;
      var marker = L.marker([c.lat, c.lng]).addTo(map);
      marker.bindTooltip(m.place.name);
      marker.on('click', function () {{ show(m.id); }});
      group.push([c.lat, c.lng]);
    }});
    if (group.length > 1) {{ map.fitBounds(group, {{ padding: [30, 30] }}); }}
    // Contrast order is what the API returned; opening the first one makes the
    // best card the one a screenshot catches.
    show(memories[0].id);
  }}).catch(function () {{
    document.getElementById('empty').setAttribute('data-show', '');
  }});
</script>
</body></html>"""


@router.get("/embed.js")
def embed_snippet():
    """The paste-in snippet. Cached hard: it changes far less often than the data."""
    return Response(
        EMBED_JS,
        media_type="application/javascript",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.get("/embed", response_class=HTMLResponse)
def embed_page(
    lat: float = Query(55.6759, ge=-90, le=90),
    lng: float = Query(12.5655, ge=-180, le=180),
    radius_km: float = Query(2, ge=0.1, le=100),
    zoom: int = Query(14, ge=1, le=20),
    layer: str | None = Query(None, pattern="^(historical|friend|stranger)$"),
):
    """The iframe body. Defaults to Copenhagen, which is the launch city.

    Every value reaching the page is a bounded number or a pattern-matched
    enum, and all of it goes in through json.dumps rather than string
    interpolation - this document is assembled on the server and served to
    somebody else's visitors.
    """
    cfg = {
        "lat": lat,
        "lng": lng,
        "radius_km": radius_km,
        "zoom": zoom,
        "layer": layer,
        "base": "",
    }
    return HTMLResponse(
        EMBED_HTML.format(
            cfg=json.dumps(cfg),
            tile_url=json.dumps(TILE_URL),
            tile_attr=json.dumps(TILE_ATTRIBUTION),
        )
    )
