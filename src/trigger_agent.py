"""Debounce per zone, OR across zones. See agents/trigger-agent.md.

Two relay modes:

- **follow** (default): the relay tracks the *presence* of a victory sign. It
  turns ON as soon as any zone has held a V for `hold_ms`/`hold_frames`, and OFF
  once every zone has been V-free for `release_ms`. Emits `RelayState` only on
  transitions. The small on/off debounce keeps a single dropped frame from
  flickering the relay (golden rule 3) while still feeling instant.
- **pulse** (legacy): one debounced hold = one one-shot `TriggerEvent`, gated by
  `cooldown_s` and (optionally) a sustained release before re-arming.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Optional

from .types import RelayState, TriggerEvent, ZoneSignal

log = logging.getLogger(__name__)


@dataclass
class _ZoneState:
    victory_since: float | None = None  # ts of start of current continuous victory
    false_since: float | None = None    # ts of start of current continuous non-victory
    victory_frames: int = 0
    armed: bool = True                  # pulse mode: ready to fire again
    on: bool = False                    # follow mode: debounced relay-on for this zone
    last_conf: float = 0.0


class TriggerAgent:
    def __init__(self, cfg: dict,
                 on_fire: Callable[[TriggerEvent], None],
                 on_state: Optional[Callable[[RelayState], None]] = None):
        self.relay_mode = cfg.get("relay_mode", "follow")
        self.mode = cfg.get("mode", "time")
        self.hold_ms = float(cfg.get("hold_ms", 350))
        self.hold_frames = int(cfg.get("hold_frames", 8))
        self.cooldown_s = float(cfg.get("cooldown_s", 3.0))
        self.require_release = bool(cfg.get("require_release", True))
        self.release_ms = float(cfg.get("release_ms", 250))
        self._on_fire = on_fire
        self._on_state = on_state
        self._zones: dict[str, _ZoneState] = {}
        self._last_fire = float("-inf")  # never block the first fire
        self._relay_on = False           # follow mode: overall (OR) relay level

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
            # Pulse mode: re-arm only after a sustained release.
            if self.require_release and not st.armed:
                if (now - st.false_since) * 1000.0 >= self.release_ms:
                    st.armed = True
                    log.debug("zone %s re-armed", sig.zone)

        if self.relay_mode == "pulse":
            self._maybe_fire(now)
        else:
            self._update_zone_on(st, now)
            self._maybe_set_relay(now)

    # ----- follow mode -----
    def _held_long_enough(self, st: _ZoneState, now: float) -> bool:
        if st.victory_since is None:
            return False
        if self.mode == "frames":
            return st.victory_frames >= self.hold_frames
        return (now - st.victory_since) * 1000.0 >= self.hold_ms

    def _update_zone_on(self, st: _ZoneState, now: float):
        """Debounced per-zone on/off with hysteresis (hold to turn on, release to off)."""
        if not st.on:
            if self._held_long_enough(st, now):
                st.on = True
        else:
            if st.victory_since is None and st.false_since is not None:
                if (now - st.false_since) * 1000.0 >= self.release_ms:
                    st.on = False

    def _maybe_set_relay(self, now: float):
        # OR across zones; if several are on, report the most confident one.
        best_zone, best_conf = None, -1.0
        for zone, st in self._zones.items():
            if st.on and st.last_conf > best_conf:
                best_zone, best_conf = zone, st.last_conf
        new_on = best_zone is not None
        if new_on == self._relay_on:
            return
        self._relay_on = new_on
        if self._on_state is not None:
            self._on_state(RelayState(new_on, best_zone, max(best_conf, 0.0), now))

    # ----- pulse mode (legacy) -----
    def _zone_active(self, st: _ZoneState, now: float) -> bool:
        if not st.armed or st.victory_since is None:
            return False
        return self._held_long_enough(st, now)

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
