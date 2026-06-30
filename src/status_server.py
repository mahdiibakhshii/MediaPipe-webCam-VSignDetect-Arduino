"""Live monitor + control server.

Serves a self-contained web UI (no external files/deps) for the on-site operator:

    GET  /              — monitor page (live video, relay state, per-hand detail, controls)
    GET  /status        — JSON snapshot: zones, per-hand detail, relay state, settings
    GET  /settings      — JSON live-editable settings + their bounds
    POST /settings      — apply settings changes (pulse_s / hold_ms / cooldown_s)
    GET  /video/<zone>  — MJPEG stream of that camera with the skeleton overlay

The video stream only consumes CPU while a browser is actually watching (the
vision agents encode frames only when this server reports viewers > 0).
"""
from __future__ import annotations

import json
import logging
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .runtime_settings import LIVE_KEYS

log = logging.getLogger("status")


# ---------------------------------------------------------------------------
# StatusStore — per-zone detection state (written by engine, read by HTTP)
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
        now = time.monotonic()
        with self._lock:
            z = self._zones.setdefault(zone, _ZoneState())
            z.is_victory = is_victory
            z.confidence = confidence
            z.ts = now
            z.record_frame(now)
            z.hands = [
                {"handedness": h.handedness, "is_victory": h.is_victory,
                 "confidence": round(h.confidence, 3)}
                for h in hands
            ]

    def update_relay(self, on: bool, zone: str | None = None):
        with self._lock:
            self._relay_on = on
            self._relay_zone = zone

    def snapshot(self) -> dict:
        with self._lock:
            zones_out = {
                name: {
                    "is_victory": z.is_victory,
                    "confidence": round(z.confidence, 3),
                    "hands_detected": len(z.hands),
                    "hands": z.hands,
                    "fps": z.fps,
                    "stale_s": z.stale_s,
                }
                for name, z in self._zones.items()
            }
            return {
                "relay_on": self._relay_on,
                "relay_zone": self._relay_zone,
                "uptime_s": int(time.monotonic() - self._start),
                "zones": zones_out,
            }


# ---------------------------------------------------------------------------
# FrameStore — latest annotated JPEG per zone + viewer count
# ---------------------------------------------------------------------------

class FrameStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._jpeg: dict[str, bytes] = {}
        self._viewers = 0

    def put(self, zone: str, jpeg_bytes: bytes):
        with self._lock:
            self._jpeg[zone] = jpeg_bytes

    def get(self, zone: str):
        with self._lock:
            return self._jpeg.get(zone)

    def add_viewer(self):
        with self._lock:
            self._viewers += 1

    def remove_viewer(self):
        with self._lock:
            self._viewers = max(0, self._viewers - 1)

    @property
    def viewers(self) -> int:
        with self._lock:
            return self._viewers


# ---------------------------------------------------------------------------
# Embedded monitor page
# ---------------------------------------------------------------------------

_HTML = """\
<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>VSign Monitor</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,monospace;background:#0d0d0d;color:#ddd;padding:1.2rem;max-width:1100px;margin:0 auto}
h1{font-size:.95rem;color:#666;margin-bottom:1rem;letter-spacing:.05em}
#relay{font-size:1.8rem;font-weight:700;margin-bottom:1.2rem}
.on{color:#0f0}.off{color:#444}
#err{color:#f44;font-size:.8rem;margin-bottom:.6rem;display:none}
.grid{display:flex;flex-wrap:wrap;gap:1rem;margin-bottom:1.4rem}
.zone{flex:1 1 380px;border:1px solid #222;border-radius:6px;padding:.7rem;background:#111}
.zhdr{display:flex;gap:1rem;align-items:center;margin-bottom:.5rem}
.zname{font-size:1.05rem;font-weight:700;color:#88f}
.v-yes{color:#0f0;font-weight:700}.v-no{color:#555}
.fps{color:#555;font-size:.8rem}.stale{color:#f80;font-size:.8rem}
img.cam{width:100%;border-radius:4px;background:#000;display:block;aspect-ratio:4/3;object-fit:contain}
table{width:100%;border-collapse:collapse;font-size:.8rem;margin-top:.5rem}
th{text-align:left;color:#555;font-weight:normal;padding:2px 5px;border-bottom:1px solid #222}
td{padding:3px 5px}
.bar-bg{display:inline-block;width:60px;height:7px;background:#222;border-radius:3px;position:relative;vertical-align:middle}
.bar-fill{position:absolute;top:0;left:0;height:100%;background:#0af;border-radius:3px}
.panel{border:1px solid #222;border-radius:6px;padding:1rem;background:#111}
.panel h2{font-size:.85rem;color:#888;margin-bottom:.8rem;letter-spacing:.04em}
.ctl{display:flex;align-items:center;gap:.6rem;margin-bottom:.7rem;flex-wrap:wrap}
.ctl label{width:230px;font-size:.85rem;color:#bbb}
.ctl input[type=number]{width:90px;background:#000;border:1px solid #333;color:#eee;padding:.35rem;border-radius:4px;font-family:inherit}
.ctl .rng{flex:1;min-width:120px}
.hint{color:#555;font-size:.72rem}
button{background:#1b5;border:0;color:#000;font-weight:700;padding:.5rem 1.2rem;border-radius:5px;cursor:pointer;font-family:inherit}
button:disabled{background:#333;color:#777;cursor:default}
#saved{color:#0f0;font-size:.8rem;margin-left:.8rem;opacity:0;transition:opacity .2s}
#foot{color:#333;font-size:.72rem;margin-top:1rem}
</style></head><body>
<h1>VSign Detect &mdash; monitor &amp; control</h1>
<div id="err"></div>
<div id="relay" class="off">&middot; RELAY OFF</div>
<div class="grid" id="zones"></div>

<div class="panel">
  <h2>LIVE SETTINGS</h2>
  <div id="controls"></div>
  <button id="apply" disabled>Apply</button><span id="saved">saved &#10003;</span>
  <p class="hint" style="margin-top:.7rem">Changes take effect immediately and persist across restarts. Other settings (camera index, min confidence, relay mode) need a config edit + restart.</p>
</div>
<div id="foot"></div>

<script>
var seenZones = {};
var bounds = {};
var dirty = false;

var LABELS = {
  pulse_s:   ["Relay ON duration", "seconds the relay stays on per V detection"],
  hold_ms:   ["Hold time", "ms a V must persist before it fires"],
  cooldown_s:["Cooldown", "min seconds between fires"]
};

async function loadSettings() {
  var r = await fetch('/settings');
  var d = await r.json();
  bounds = d.bounds || {};
  var c = document.getElementById('controls');
  c.innerHTML = '';
  Object.keys(d.values).forEach(function(k){
    var b = bounds[k] || [0, 1000];
    var lab = LABELS[k] || [k, ''];
    var row = document.createElement('div');
    row.className = 'ctl';
    row.innerHTML =
      '<label>' + lab[0] + '<br><span class="hint">' + lab[1] + '</span></label>' +
      '<input type="range" class="rng" id="r_'+k+'" min="'+b[0]+'" max="'+b[1]+'" step="any" value="'+d.values[k]+'">' +
      '<input type="number" id="n_'+k+'" min="'+b[0]+'" max="'+b[1]+'" step="any" value="'+d.values[k]+'">';
    c.appendChild(row);
    var rng = row.querySelector('#r_'+k), num = row.querySelector('#n_'+k);
    rng.addEventListener('input', function(){ num.value = rng.value; markDirty(); });
    num.addEventListener('input', function(){ rng.value = num.value; markDirty(); });
  });
}
function markDirty(){ dirty = true; document.getElementById('apply').disabled = false; }

async function apply() {
  var body = {};
  Object.keys(LABELS).forEach(function(k){
    var n = document.getElementById('n_'+k);
    if (n) body[k] = parseFloat(n.value);
  });
  var r = await fetch('/settings', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
  var d = await r.json();
  Object.keys(d.values).forEach(function(k){
    var n = document.getElementById('n_'+k), rng = document.getElementById('r_'+k);
    if (n) n.value = d.values[k];
    if (rng) rng.value = d.values[k];
  });
  dirty = false;
  document.getElementById('apply').disabled = true;
  var s = document.getElementById('saved'); s.style.opacity = 1;
  setTimeout(function(){ s.style.opacity = 0; }, 1200);
}

function ensureZone(name) {
  if (seenZones[name]) return;
  seenZones[name] = true;
  var div = document.createElement('div');
  div.className = 'zone';
  div.id = 'zone_' + name;
  div.innerHTML =
    '<div class="zhdr"><span class="zname">Zone ' + name + '</span>' +
    '<span id="v_'+name+'" class="v-no">&middot; no V</span>' +
    '<span id="fps_'+name+'" class="fps"></span>' +
    '<span id="stale_'+name+'" class="stale"></span></div>' +
    '<img class="cam" src="/video/' + name + '" alt="zone ' + name + '">' +
    '<div id="hands_'+name+'"></div>';
  document.getElementById('zones').appendChild(div);
}

async function poll() {
  try {
    var r = await fetch('/status');
    if (!r.ok) throw new Error('HTTP ' + r.status);
    var d = await r.json();
    document.getElementById('err').style.display = 'none';

    var rel = document.getElementById('relay');
    if (d.relay_on) { rel.className='on'; rel.innerHTML='&#x270c; RELAY ON' + (d.relay_zone?'&nbsp;&nbsp;zone '+d.relay_zone:''); }
    else { rel.className='off'; rel.innerHTML='&middot; RELAY OFF'; }

    var names = Object.keys(d.zones||{}).sort();
    names.forEach(function(name){
      ensureZone(name);
      var z = d.zones[name];
      var v = document.getElementById('v_'+name);
      v.className = z.is_victory ? 'v-yes' : 'v-no';
      v.innerHTML = z.is_victory ? '&#x270c; V SIGN' : '&middot; no V';
      document.getElementById('fps_'+name).textContent = z.fps + ' fps';
      var st = document.getElementById('stale_'+name);
      st.textContent = (z.stale_s !== null && z.stale_s > 2) ? ('⚠ stale '+z.stale_s+'s') : '';
      var h = '';
      if (z.hands && z.hands.length) {
        h = '<table><tr><th>#</th><th>Hand</th><th>V?</th><th>Conf</th></tr>';
        z.hands.forEach(function(hd, j){
          var pct = Math.round(hd.confidence*100);
          h += '<tr><td>'+(j+1)+'</td><td>'+hd.handedness+'</td>'+
               '<td class="'+(hd.is_victory?'v-yes':'v-no')+'">'+(hd.is_victory?'&#x270c;':'no')+'</td>'+
               '<td><span class="bar-bg"><span class="bar-fill" style="width:'+pct+'%"></span></span> '+pct+'%</td></tr>';
        });
        h += '</table>';
      } else { h = '<div class="hint" style="margin-top:.4rem">no hands detected</div>'; }
      document.getElementById('hands_'+name).innerHTML = h;
    });
    document.getElementById('foot').textContent = 'uptime ' + d.uptime_s + 's  ·  ' + new Date().toLocaleTimeString();
  } catch(e) {
    var el = document.getElementById('err'); el.style.display=''; el.textContent = 'Cannot reach engine: ' + e.message;
  }
}

document.getElementById('apply').addEventListener('click', apply);
loadSettings();
setInterval(poll, 300);
poll();
</script></body></html>
"""

_HTML_BYTES = _HTML.encode("utf-8")


# ---------------------------------------------------------------------------
# HTTP server
# ---------------------------------------------------------------------------

class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        log.debug("%s - " + fmt, self.address_string(), *args)

    def _send(self, code, content_type, body: bytes):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        n = int(self.headers.get("Content-Length", 0) or 0)
        if n <= 0:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8") or "{}")
        except Exception:
            return {}

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, "text/html; charset=utf-8", _HTML_BYTES)
        elif self.path == "/status":
            self._send(200, "application/json",
                       json.dumps(self.server.status.snapshot()).encode("utf-8"))
        elif self.path == "/settings":
            self._send(200, "application/json", self._settings_json())
        elif self.path.startswith("/video/"):
            self._stream_video(self.path[len("/video/"):])
        else:
            self._send(404, "text/plain", b"not found")

    def do_POST(self):
        if self.path == "/settings":
            changes = self._read_json()
            self.server.settings.update(changes)
            self._send(200, "application/json", self._settings_json())
        else:
            self._send(404, "text/plain", b"not found")

    def _settings_json(self) -> bytes:
        return json.dumps({
            "values": self.server.settings.live_values(),
            "bounds": {k: list(v) for k, v in LIVE_KEYS.items()},
        }).encode("utf-8")

    def _stream_video(self, zone: str):
        fs = self.server.frames
        if fs is None:
            return self._send(404, "text/plain", b"no video")
        self.send_response(200)
        self.send_header("Age", "0")
        self.send_header("Cache-Control", "no-cache, private")
        self.send_header("Pragma", "no-cache")
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.end_headers()
        fs.add_viewer()
        try:
            while True:
                jpeg = fs.get(zone)
                if jpeg is None:
                    time.sleep(0.05)
                    continue
                self.wfile.write(b"--frame\r\n")
                self.wfile.write(b"Content-Type: image/jpeg\r\n")
                self.wfile.write(("Content-Length: %d\r\n\r\n" % len(jpeg)).encode("ascii"))
                self.wfile.write(jpeg)
                self.wfile.write(b"\r\n")
                time.sleep(0.07)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        finally:
            fs.remove_viewer()


class _Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, addr, status, frames, settings):
        super().__init__(addr, _Handler)
        self.status = status
        self.frames = frames
        self.settings = settings


def start_monitor_server(status: StatusStore, frames: FrameStore, settings,
                         host: str = "0.0.0.0", port: int = 8080) -> None:
    """Start the monitor HTTP server on a daemon thread. Returns immediately."""
    srv = _Server((host, port), status, frames, settings)
    t = threading.Thread(target=srv.serve_forever, name="monitor-http", daemon=True)
    t.start()
    shown = "localhost" if host in ("0.0.0.0", "") else host
    log.info("monitor UI at http://%s:%d/", shown, port)
