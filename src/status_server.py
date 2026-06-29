"""Live debug status server.

Serves a self-contained HTML dashboard at http://host:port/ that shows
per-zone, per-hand detection state in real time — no external dependencies,
no static files. Useful for debugging multi-hand detection and relay state
while the headless orchestrator is running.

Endpoints:
    GET /         — HTML dashboard (polls /status every 300 ms via JS)
    GET /status   — JSON snapshot of all zones + relay state
"""
from __future__ import annotations

import json
import logging
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

log = logging.getLogger("status")

# ---------------------------------------------------------------------------
# StatusStore — thread-safe; written by the engine, read by the HTTP thread
# ---------------------------------------------------------------------------

class _ZoneState:
    __slots__ = ("is_victory", "confidence", "hands", "ts", "_frame_times")

    def __init__(self):
        self.is_victory = False
        self.confidence = 0.0
        self.hands: list[dict] = []
        self.ts: float = 0.0
        self._frame_times: list[float] = []

    def record_frame(self, now: float):
        self._frame_times.append(now)
        cutoff = now - 2.0
        # trim frames older than 2 s (keep at most 120 entries)
        while self._frame_times and (self._frame_times[0] < cutoff or len(self._frame_times) > 120):
            self._frame_times.pop(0)

    @property
    def fps(self) -> float:
        n = len(self._frame_times)
        if n < 2:
            return 0.0
        span = self._frame_times[-1] - self._frame_times[0]
        return round((n - 1) / span, 1) if span > 0 else 0.0

    @property
    def stale_s(self) -> float | None:
        if not self.ts:
            return None
        return round(time.monotonic() - self.ts, 1)


class StatusStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._zones: dict[str, _ZoneState] = {}
        self._relay_on = False
        self._relay_zone: str | None = None
        self._start = time.monotonic()

    def update_zone(self, zone: str, is_victory: bool, confidence: float, hands):
        """Called for every frame from every zone (high frequency)."""
        now = time.monotonic()
        with self._lock:
            if zone not in self._zones:
                self._zones[zone] = _ZoneState()
            z = self._zones[zone]
            z.is_victory = is_victory
            z.confidence = confidence
            z.ts = now
            z.record_frame(now)
            # Convert HandResult objects to plain dicts for JSON serialisation.
            z.hands = [
                {
                    "handedness": h.handedness,
                    "is_victory": h.is_victory,
                    "confidence": round(h.confidence, 3),
                }
                for h in hands
            ]

    def update_relay(self, on: bool, zone: str | None = None):
        """Called on relay state transitions."""
        with self._lock:
            self._relay_on = on
            self._relay_zone = zone

    def snapshot(self) -> dict:
        with self._lock:
            zones_out = {}
            for name, z in self._zones.items():
                zones_out[name] = {
                    "is_victory": z.is_victory,
                    "confidence": round(z.confidence, 3),
                    "hands_detected": len(z.hands),
                    "hands": z.hands,
                    "fps": z.fps,
                    "stale_s": z.stale_s,
                }
            return {
                "relay_on": self._relay_on,
                "relay_zone": self._relay_zone,
                "uptime_s": int(time.monotonic() - self._start),
                "zones": zones_out,
            }


# ---------------------------------------------------------------------------
# Embedded HTML dashboard
# ---------------------------------------------------------------------------

_HTML = """\
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<title>VSign Status</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:monospace;background:#0d0d0d;color:#ddd;padding:1.2rem}
h1{font-size:.95rem;color:#666;margin-bottom:1.2rem;letter-spacing:.05em}
#relay{font-size:2rem;font-weight:700;margin-bottom:1.4rem;letter-spacing:.03em}
.on{color:#0f0}.off{color:#444}
.zone{border:1px solid #222;border-radius:5px;padding:.8rem 1rem;margin-bottom:.8rem}
.zone-hdr{display:flex;gap:1.5rem;align-items:center;margin-bottom:.55rem}
.z-name{font-size:1.05rem;font-weight:700;color:#88f}
.v-yes{color:#0f0;font-weight:700}.v-no{color:#444}
.fps{color:#555;font-size:.8rem}
.stale{color:#f80;font-size:.8rem}
.no-hands{color:#444;font-size:.82rem;margin-top:.3rem}
table{width:100%;border-collapse:collapse;font-size:.82rem;margin-top:.3rem}
th{text-align:left;color:#555;font-weight:normal;padding:2px 6px;border-bottom:1px solid #222}
td{padding:3px 6px;vertical-align:middle}
.bar-wrap{display:inline-flex;align-items:center;gap:5px}
.bar-bg{display:inline-block;width:70px;height:7px;background:#1a1a1a;border-radius:3px;position:relative;overflow:hidden}
.bar-fill{position:absolute;top:0;left:0;height:100%;background:#0af;border-radius:3px;transition:width .15s}
#foot{color:#333;font-size:.75rem;margin-top:1.2rem}
#err{color:#f44;font-size:.8rem;margin-bottom:.5rem;display:none}
</style>
</head>
<body>
<h1>VSign Detect &mdash; live debug status</h1>
<div id="err"></div>
<div id="relay" class="off">&middot; RELAY OFF</div>
<div id="zones"></div>
<div id="foot"></div>
<script>
var failCount = 0;
async function poll() {
  try {
    var r = await fetch('/status');
    if (!r.ok) throw new Error('HTTP ' + r.status);
    var d = await r.json();
    failCount = 0;
    document.getElementById('err').style.display = 'none';

    // relay indicator
    var rel = document.getElementById('relay');
    if (d.relay_on) {
      rel.className = 'on';
      rel.innerHTML = '&#x270c; RELAY ON' + (d.relay_zone ? '&nbsp;&nbsp;zone&nbsp;' + d.relay_zone : '');
    } else {
      rel.className = 'off';
      rel.innerHTML = '&middot; RELAY OFF';
    }

    // zones
    var html = '';
    var zones = d.zones || {};
    var zoneNames = Object.keys(zones).sort();
    if (!zoneNames.length) {
      html = '<div style="color:#444;font-size:.85rem">Waiting for frames&hellip;</div>';
    }
    for (var i = 0; i < zoneNames.length; i++) {
      var name = zoneNames[i];
      var z = zones[name];
      var stale = z.stale_s !== null && z.stale_s > 2;
      html += '<div class="zone">';
      html += '<div class="zone-hdr">';
      html += '<span class="z-name">Zone ' + name + '</span>';
      html += '<span class="' + (z.is_victory ? 'v-yes' : 'v-no') + '">'
            + (z.is_victory ? '&#x270c; V SIGN' : '&middot; no V') + '</span>';
      html += '<span class="fps">' + z.fps + ' fps</span>';
      if (stale) html += '<span class="stale">&#9888; stale ' + z.stale_s + 's</span>';
      html += '</div>'; // zone-hdr

      if (z.hands && z.hands.length) {
        html += '<table><tr>'
              + '<th>#</th><th>Hand</th><th>V?</th><th>Confidence</th>'
              + '</tr>';
        for (var j = 0; j < z.hands.length; j++) {
          var h = z.hands[j];
          var pct = Math.round(h.confidence * 100);
          html += '<tr>'
                + '<td>' + (j + 1) + '</td>'
                + '<td>' + h.handedness + '</td>'
                + '<td class="' + (h.is_victory ? 'v-yes' : 'v-no') + '">'
                + (h.is_victory ? '&#x270c; yes' : 'no') + '</td>'
                + '<td><div class="bar-wrap">'
                + '<div class="bar-bg"><div class="bar-fill" style="width:' + pct + '%"></div></div>'
                + '<span>' + pct + '%</span>'
                + '</div></td>'
                + '</tr>';
        }
        html += '</table>';
      } else {
        html += '<div class="no-hands">no hands detected</div>';
      }
      html += '</div>'; // zone
    }
    document.getElementById('zones').innerHTML = html;
    document.getElementById('foot').textContent =
      'uptime: ' + d.uptime_s + 's  ·  last update: ' + new Date().toLocaleTimeString();
  } catch(e) {
    failCount++;
    if (failCount > 3) {
      var el = document.getElementById('err');
      el.style.display = '';
      el.textContent = 'Cannot reach engine: ' + e.message;
    }
  }
}
setInterval(poll, 300);
poll();
</script>
</body>
</html>
"""

_HTML_BYTES = _HTML.encode("utf-8")


# ---------------------------------------------------------------------------
# HTTP server
# ---------------------------------------------------------------------------

class _Handler(BaseHTTPRequestHandler):
    store: StatusStore  # set on the server instance

    def log_message(self, fmt, *args):
        log.debug("%s - " + fmt, self.address_string(), *args)

    def _send(self, code: int, content_type: str, body: bytes):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, "text/html; charset=utf-8", _HTML_BYTES)
        elif self.path == "/status":
            body = json.dumps(self.server.store.snapshot()).encode("utf-8")
            self._send(200, "application/json", body)
        else:
            self._send(404, "text/plain", b"not found")

    # silence HEAD / OPTIONS noise
    def do_HEAD(self):
        if self.path in ("/", "/index.html"):
            self._send(200, "text/html; charset=utf-8", b"")
        else:
            self._send(404, "text/plain", b"")


class _Server(ThreadingHTTPServer):
    def __init__(self, addr, store: StatusStore):
        super().__init__(addr, _Handler)
        self.store = store
        self.daemon_threads = True


def start_status_server(store: StatusStore, host: str = "0.0.0.0", port: int = 8080) -> None:
    """Start the status HTTP server on a daemon thread. Returns immediately."""
    srv = _Server((host, port), store)
    t = threading.Thread(target=srv.serve_forever, name="status-http", daemon=True)
    t.start()
    log.info("status dashboard at http://%s:%d/", host if host != "0.0.0.0" else "localhost", port)
