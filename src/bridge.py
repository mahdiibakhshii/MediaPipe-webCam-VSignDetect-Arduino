"""Web -> relay bridge.

Serves the browser control panel (web/) AND a tiny HTTP API so the panel can
fire the relay through the SAME output sinks (serial/OSC/console) as the engine.
Detection still happens in the browser; this just lets the browser's triggers
reach the hardware.

    python -m src.bridge --config config/config.yaml --port 8000

Then open http://localhost:8000/ and toggle "Drive relay".

Endpoints (same origin as the panel, so no CORS needed):
    GET  /api/status   -> {"serial_connected": true|false|null}
    POST /api/ping     -> {"ok": true|false}
    POST /api/fire     -> {"ok": true, "served": ["SerialSink", ...]}  (body: {zone, confidence})
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from .config import load_config
from .logging_setup import setup_logging
from .sinks import build_sinks
from .types import TriggerEvent

log = logging.getLogger("bridge")


class BridgeServer(ThreadingHTTPServer):
    def __init__(self, addr, handler, sinks, min_interval):
        super().__init__(addr, handler)
        self.sinks = sinks
        self.min_interval = float(min_interval)
        self._last_fire = 0.0
        self._lock = threading.Lock()

    # find the serial sink (if any) for status/ping
    def serial_sink(self):
        for s in self.sinks:
            if hasattr(s, "connected"):
                return s
        return None


class BridgeHandler(SimpleHTTPRequestHandler):
    # quieter than the default per-request stderr spam
    def log_message(self, fmt, *args):
        log.debug("%s - %s", self.address_string(), fmt % args)

    def _send_json(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
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

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/status":
            sink = self.server.serial_sink()
            connected = sink.connected if sink is not None else None
            return self._send_json(200, {"serial_connected": connected})
        return super().do_GET()  # static files from web/

    def do_POST(self):
        if self.path == "/api/fire":
            return self._handle_fire()
        if self.path == "/api/ping":
            sink = self.server.serial_sink()
            ok = bool(sink.ping(1.0)) if sink is not None else False
            return self._send_json(200, {"ok": ok})
        self._send_json(404, {"error": "not found"})

    def _handle_fire(self):
        data = self._read_json()
        zone = str(data.get("zone", "web"))
        conf = float(data.get("confidence", 1.0))
        now = time.monotonic()

        srv = self.server
        with srv._lock:
            if now - srv._last_fire < srv.min_interval:
                return self._send_json(200, {"ok": False, "reason": "cooldown"})
            srv._last_fire = now

        ev = TriggerEvent(zone, conf, now)
        served = []
        for s in srv.sinks:
            if hasattr(s, "on_fire"):
                try:
                    s.on_fire(ev)
                    served.append(type(s).__name__)
                except Exception:
                    log.exception("sink on_fire error")
        log.info("web FIRE zone=%s conf=%.2f -> %s", zone, conf, served or "(none)")
        self._send_json(200, {"ok": True, "served": served})


def main():
    ap = argparse.ArgumentParser(description="VSign Detect web->relay bridge")
    ap.add_argument("--config", default="config/config.yaml")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--web-dir", default="web")
    ap.add_argument("--min-interval", type=float, default=None,
                    help="server-side min seconds between fires (default: trigger.cooldown_s)")
    args = ap.parse_args()

    cfg = load_config(args.config)
    setup_logging(cfg)

    min_interval = (args.min_interval if args.min_interval is not None
                    else float(cfg.get("trigger", {}).get("cooldown_s", 1.0)))

    sinks = build_sinks(cfg)
    if not any(hasattr(s, "connected") for s in sinks):
        log.warning("No serial output enabled — /api/fire will not reach a relay. "
                    "Set outputs: serial enabled: true in config.")

    web_dir = os.path.abspath(args.web_dir)

    def handler(*h_args, **h_kwargs):
        return BridgeHandler(*h_args, directory=web_dir, **h_kwargs)

    httpd = BridgeServer((args.host, args.port), handler, sinks, min_interval)
    log.info("bridge serving %s at http://%s:%d/  (min_interval=%.2fs)",
             web_dir, args.host, args.port, min_interval)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        log.info("shutting down bridge…")
        httpd.shutdown()
        for s in sinks:
            if hasattr(s, "close"):
                try:
                    s.close()
                except Exception:
                    pass


if __name__ == "__main__":
    main()
