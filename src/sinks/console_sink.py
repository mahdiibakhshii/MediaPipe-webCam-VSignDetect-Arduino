"""Console sink — logs fire events. Handy while developing."""
from __future__ import annotations

import logging

log = logging.getLogger("trigger")


class ConsoleSink:
    def on_fire(self, ev):
        log.info("✌  FIRE  zone=%s  conf=%.2f", ev.zone, ev.confidence)
