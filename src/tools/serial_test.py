"""Test the Arduino link without a camera — PING, FIRE (pulse), and ON/OFF (hold).

    python -m src.tools.serial_test --config config/config.yaml
    python -m src.tools.serial_test --port COM5 --no-fire

Expects the firmware in firmware/vsign_relay flashed. You should see READY, PONG,
then OK FIRE … DONE (a click), then OK ON (relay holds 2 s) … OK OFF.
"""
from __future__ import annotations

import argparse
import logging
import time

from ..config import load_config
from ..serial_agent import SerialAgent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/config.yaml")
    ap.add_argument("--port", default=None, help="override serial.port (e.g. COM5)")
    ap.add_argument("--no-fire", action="store_true",
                    help="only PING; don't pulse the relay or test the held ON/OFF path")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    log = logging.getLogger("serial_test")

    cfg = load_config(args.config)
    scfg = dict(cfg.get("serial", {}))
    if args.port:
        scfg["port"] = args.port
    if not scfg.get("port"):
        raise SystemExit("No serial.port set. Use --port COMx or set serial.port in config.")

    agent = SerialAgent(
        port=scfg["port"], baud=scfg.get("baud", 115200),
        connect_timeout_s=scfg.get("connect_timeout_s", 5),
        reconnect_min_s=scfg.get("reconnect_min_s", 1),
        reconnect_max_s=scfg.get("reconnect_max_s", 10),
    )
    agent.start()
    log.info("opening %s …", scfg["port"])
    if not agent.wait_connected(scfg.get("connect_timeout_s", 5) + 2):
        log.error("could not connect to %s (is the port right and free?)", scfg["port"])
        agent.close()
        raise SystemExit(1)

    log.info("PING -> %s", "PONG ✓" if agent.ping(2.0) else "no PONG")
    if not args.no_fire:
        log.info("FIRE -> %s", "sent" if agent.fire() else "failed (not connected)")
        time.sleep(3.0)  # let OK FIRE / DONE arrive in the log
        # Follow-mode path: hold ON, keepalive should keep it on past the watchdog.
        log.info("ON  -> %s (relay should hold)",
                 "sent" if agent.set_relay(True) else "failed (not connected)")
        time.sleep(3.0)  # > firmware WATCHDOG_MS: stays on only if keepalive works
        log.info("OFF -> %s", "sent" if agent.set_relay(False) else "failed (not connected)")
        time.sleep(0.5)
    agent.close()  # also sends OFF (fail-safe)
    log.info("done.")


if __name__ == "__main__":
    main()
