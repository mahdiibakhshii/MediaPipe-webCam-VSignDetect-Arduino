"""Serial output sink — fires the Arduino relay on a trigger event."""
from __future__ import annotations

import logging

from ..serial_agent import SerialAgent

log = logging.getLogger(__name__)


class SerialSink:
    def __init__(self, serial_cfg: dict):
        self._agent = SerialAgent(
            port=serial_cfg.get("port"),
            baud=serial_cfg.get("baud", 115200),
            connect_timeout_s=serial_cfg.get("connect_timeout_s", 5),
            reconnect_min_s=serial_cfg.get("reconnect_min_s", 1),
            reconnect_max_s=serial_cfg.get("reconnect_max_s", 10),
        )
        self._agent.start()

    def on_fire(self, ev):
        if not self._agent.fire():
            log.warning("FIRE dropped - Arduino not connected")

    @property
    def connected(self) -> bool:
        return self._agent.is_connected

    def ping(self, timeout: float = 1.0) -> bool:
        return self._agent.ping(timeout)

    def close(self):
        self._agent.close()
