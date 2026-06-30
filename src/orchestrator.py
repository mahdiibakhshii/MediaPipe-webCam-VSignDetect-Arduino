"""Entry point: load config, start vision agents, debounce, dispatch to sinks.

    python -m src.orchestrator --config config/config.yaml
"""
from __future__ import annotations

import argparse
import logging
import os
import queue
import signal
import threading
import time

from .config import load_config
from .logging_setup import setup_logging
from .models import ensure_model, model_for_classifier
from .runtime_settings import RuntimeSettings
from .sinks import build_sinks
from .status_server import FrameStore, StatusStore, start_monitor_server
from .trigger_agent import TriggerAgent
from .vision_agent import VisionAgent


def main():
    ap = argparse.ArgumentParser(description="VSign Detect engine")
    ap.add_argument("--config", default="config/config.yaml")
    args = ap.parse_args()

    cfg = load_config(args.config)
    setup_logging(cfg)
    log = logging.getLogger("orchestrator")

    detection = cfg["detection"]
    classifier_name = detection.get("classifier", "gesture_recognizer")
    model_path = ensure_model(model_for_classifier(classifier_name))
    # Log the detection settings actually in effect — if num_hands looks wrong
    # here (e.g. 1 when you expect 4), fix it in config.yaml under `detection:`.
    log.info("detection: classifier=%s num_hands=%s min_score=%s",
             classifier_name, detection.get("num_hands", 4),
             detection.get("min_score", 0.6))

    # Live-editable settings, persisted next to the config file.
    sidecar = os.path.join(os.path.dirname(os.path.abspath(args.config)), "runtime.json")
    settings = RuntimeSettings(cfg.get("trigger", {}), sidecar_path=sidecar)

    sinks = build_sinks(cfg, settings)

    app_cfg = cfg.get("app", {})
    status_store = StatusStore()
    frame_store = FrameStore()
    start_monitor_server(
        status_store, frame_store, settings,
        host=app_cfg.get("status_host", "0.0.0.0"),
        port=int(app_cfg.get("status_port", 8080)),
    )

    # Logical relay state for the monitor: in pulse mode the relay is held ON for
    # pulse_s then released; reflect that window in the UI (mirrors the sink timer).
    relay_timer: dict = {"t": None}

    def _relay_off():
        status_store.update_relay(False, None)

    def on_fire(ev):
        log.info("FIRE zone=%s conf=%.2f", ev.zone, ev.confidence)
        pulse_s = float(settings.get("pulse_s"))
        status_store.update_relay(True, ev.zone)
        if relay_timer["t"] is not None:
            relay_timer["t"].cancel()
        relay_timer["t"] = threading.Timer(pulse_s, _relay_off)
        relay_timer["t"].daemon = True
        relay_timer["t"].start()
        for s in sinks:
            if hasattr(s, "on_fire"):
                try:
                    s.on_fire(ev)
                except Exception:
                    log.exception("sink on_fire error")

    def on_state(ev):
        log.info("RELAY %s zone=%s conf=%.2f",
                 "ON" if ev.on else "OFF", ev.zone, ev.confidence)
        status_store.update_relay(ev.on, ev.zone)
        for s in sinks:
            if hasattr(s, "on_state"):
                try:
                    s.on_state(ev)
                except Exception:
                    log.exception("sink on_state error")

    trigger = TriggerAgent(settings, on_fire, on_state)

    q: "queue.Queue" = queue.Queue(maxsize=400)

    def emit(sig):
        try:
            q.put_nowait(sig)
        except queue.Full:
            pass  # drop oldest-style: skip if backed up; keeps latency bounded

    agents = []
    for cam in cfg["cameras"]:
        agent = VisionAgent(cam["zone"], cam, detection, model_path, emit, frame_store)
        agents.append(agent)
        agent.start()
        log.info("started vision zone=%s index=%s", cam["zone"], cam["index"])

    state = {"running": True}

    def shutdown(*_):
        state["running"] = False

    signal.signal(signal.SIGINT, shutdown)
    try:
        signal.signal(signal.SIGTERM, shutdown)
    except (ValueError, AttributeError):
        pass

    heartbeat_s = float(cfg.get("app", {}).get("heartbeat_s", 30))
    last_hb = time.monotonic()
    log.info("engine running (%d camera(s)). Ctrl-C to stop.", len(agents))

    try:
        while state["running"]:
            try:
                sig = q.get(timeout=0.5)
            except queue.Empty:
                sig = None
            if sig is not None:
                status_store.update_zone(sig.zone, sig.is_victory, sig.confidence, sig.hands)
                for s in sinks:
                    if hasattr(s, "on_signal"):
                        try:
                            s.on_signal(sig)
                        except Exception:
                            log.exception("sink on_signal error")
                trigger.submit(sig)

            now = time.monotonic()
            if now - last_hb >= heartbeat_s:
                last_hb = now
                log.info("heartbeat: alive")
    finally:
        log.info("shutting down…")
        for a in agents:
            a.stop()
        for a in agents:
            a.join(timeout=2.0)
        for s in sinks:
            if hasattr(s, "close"):
                try:
                    s.close()
                except Exception:
                    pass
        log.info("stopped.")


if __name__ == "__main__":
    main()
