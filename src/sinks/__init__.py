"""Output sinks. A sink may implement on_signal(ZoneSignal), on_fire(TriggerEvent), close()."""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def build_sinks(cfg: dict, settings=None) -> list:
    """Build the enabled output sinks from the full config.

    Reads cfg['outputs'] (the list of sinks) and, for the serial sink, the
    top-level cfg['serial'] connection settings. `settings` (RuntimeSettings) is
    passed to the serial sink so the relay pulse duration is live-tunable.
    """
    specs = cfg.get("outputs", []) or []
    serial_cfg = cfg.get("serial", {}) or {}
    sinks = []
    for spec in specs:
        if not spec.get("enabled", True):
            continue
        kind = spec.get("type")
        if kind == "osc":
            from .osc_sink import OscSink

            sinks.append(OscSink(
                host=spec.get("host", "127.0.0.1"),
                port=int(spec.get("port", 7000)),
                prefix=spec.get("prefix", "/vsign"),
            ))
            log.info("output: OSC -> %s:%s", spec.get("host", "127.0.0.1"),
                     spec.get("port", 7000))
        elif kind == "console":
            from .console_sink import ConsoleSink

            sinks.append(ConsoleSink())
            log.info("output: console")
        elif kind == "serial":
            from .serial_sink import SerialSink

            sinks.append(SerialSink(serial_cfg, settings))
            log.info("output: serial -> %s", serial_cfg.get("port"))
        else:
            log.warning("output: unknown sink type %r — skipping", kind)
    return sinks
