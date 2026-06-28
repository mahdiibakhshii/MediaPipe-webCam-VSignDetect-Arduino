"""Entry point: load config, start vision agents, debounce, dispatch to sinks.

    python -m src.orchestrator --config config/config.yaml
"""
from __future__ import annotations

import argparse
import logging
import queue
import signal
import time

from .config import load_config
from .logging_setup import setup_logging
from .models import ensure_model, model_for_classifier
from .sinks import build_sinks
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

    sinks = build_sinks(cfg)

    def on_fire(ev):
        log.info("FIRE zone=%s conf=%.2f", ev.zone, ev.confidence)
        for s in sinks:
            if hasattr(s, "on_fire"):
                try:
                    s.on_fire(ev)
                except Exception:
                    log.exception("sink on_fire error")

    trigger = TriggerAgent(cfg.get("trigger", {}), on_fire)

    q: "queue.Queue" = queue.Queue(maxsize=400)

    def emit(sig):
        try:
            q.put_nowait(sig)
        except queue.Full:
            pass  # drop oldest-style: skip if backed up; keeps latency bounded

    agents = []
    for cam in cfg["cameras"]:
        agent = VisionAgent(cam["zone"], cam, detection, model_path, emit)
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
