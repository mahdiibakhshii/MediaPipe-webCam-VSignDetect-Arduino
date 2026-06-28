"""Debounce per zone, OR across zones, enforce cooldown. See agents/trigger-agent.md."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable

from .types import TriggerEvent, ZoneSignal

log = logging.getLogger(__name__)


@dataclass
class _ZoneState:
    victory_since: float | None = None  # ts of start of current continuous victory
    false_since: float | None = None    # ts of start of current continuous non-victory
    victory_frames: int = 0
    armed: bool = True
    last_conf: float = 0.0


class TriggerAgent:
    def __init__(self, cfg: dict, on_fire: Callable[[TriggerEvent], None]):
        self.mode = cfg.get("mode", "time")
        self.hold_ms = float(cfg.get("hold_ms", 350))
        self.hold_frames = int(cfg.get("hold_frames", 8))
        self.cooldown_s = float(cfg.get("cooldown_s", 3.0))
        self.require_release = bool(cfg.get("require_release", True))
        self.release_ms = float(cfg.get("release_ms", 250))
        self._on_fire = on_fire
        self._zones: dict[str, _ZoneState] = {}
        self._last_fire = float("-inf")  # never block the first fire

    def submit(self, sig: ZoneSignal):
        st = self._zones.setdefault(sig.zone, _ZoneState())
        now = sig.ts

        if sig.is_victory:
            if st.victory_since is None:
                st.victory_since = now
            st.victory_frames += 1
            st.false_since = None
            st.last_conf = sig.confidence
        else:
            st.victory_since = None
            st.victory_frames = 0
            if st.false_since is None:
                st.false_since = now
            # Re-arm only after a sustained release.
            if self.require_release and not st.armed:
                if (now - st.false_since) * 1000.0 >= self.release_ms:
                    st.armed = True
                    log.debug("zone %s re-armed", sig.zone)

        self._maybe_fire(now)

    def _zone_active(self, st: _ZoneState, now: float) -> bool:
        if not st.armed or st.victory_since is None:
            return False
        if self.mode == "frames":
            return st.victory_frames >= self.hold_frames
        return (now - st.victory_since) * 1000.0 >= self.hold_ms

    def _maybe_fire(self, now: float):
        if now - self._last_fire < self.cooldown_s:
            return
        # OR across zones; if several are active, pick the most confident.
        best_zone, best_conf = None, -1.0
        for zone, st in self._zones.items():
            if self._zone_active(st, now) and st.last_conf > best_conf:
                best_zone, best_conf = zone, st.last_conf
        if best_zone is None:
            return

        self._last_fire = now
        if self.require_release:
            self._zones[best_zone].armed = False
        self._on_fire(TriggerEvent(best_zone, best_conf, now))
