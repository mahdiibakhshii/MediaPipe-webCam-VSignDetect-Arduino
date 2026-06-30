"""Serial output sink — drives the Arduino relay on detection events.

Pulse mode: on a fire, hold the relay ON for `pulse_s` seconds (host-timed, so the
duration is configurable live from the monitor UI), then release. A new fire
during a pulse restarts the timer (extends the ON window).
Follow mode: the relay simply mirrors the live victory state.
"""
from __future__ import annotations

import logging
import threading

from ..serial_agent import SerialAgent

log = logging.getLogger(__name__)


class SerialSink:
    def __init__(self, serial_cfg: dict, settings=None):
        self._settings = settings
        self._agent = SerialAgent(
            port=serial_cfg.get("port"),
            baud=serial_cfg.get("baud", 115200),
            connect_timeout_s=serial_cfg.get("connect_timeout_s", 5),
            reconnect_min_s=serial_cfg.get("reconnect_min_s", 1),
            reconnect_max_s=serial_cfg.get("reconnect_max_s", 10),
        )
        self._lock = threading.Lock()
        self._timer: threading.Timer | None = None
        self._agent.start()

    def _pulse_s(self) -> float:
        if self._settings is not None:
            return float(self._settings.get("pulse_s"))
        return 5.0

    def on_fire(self, ev):
        # Pulse mode: relay ON now, schedule OFF after pulse_s (host-timed).
        pulse_s = self._pulse_s()
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
            ok = self._agent.set_relay(True)
            self._timer = threading.Timer(pulse_s, self._release)
            self._timer.daemon = True
            self._timer.start()
        if ok:
            log.info("relay ON for %.1fs (zone=%s)", pulse_s, ev.zone)
        else:
            log.warning("FIRE dropped - Arduino not connected")

    def _release(self):
        if not self._agent.set_relay(False):
            log.debug("relay OFF dropped - Arduino not connected")

    def on_state(self, ev):
        # Follow mode: hold the relay to match the live victory state.
        if not self._agent.set_relay(ev.on):
            log.warning("relay %s dropped - Arduino not connected",
                        "ON" if ev.on else "OFF")

    @property
    def connected(self) -> bool:
        return self._agent.is_connected

    def ping(self, timeout: float = 1.0) -> bool:
        return self._agent.ping(timeout)

    def close(self):
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
        self._agent.close()
