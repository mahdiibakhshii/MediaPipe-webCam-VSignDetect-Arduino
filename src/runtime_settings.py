"""Thread-safe runtime settings the monitor UI can change without a restart.

Seeded from the `trigger:` config block. The operator-editable subset (LIVE_KEYS)
can be changed live via the monitor server and is persisted to a small JSON
sidecar (config/runtime.json) so edits survive restarts. The sidecar never
touches config.yaml — config.yaml stays the source of defaults.
"""
from __future__ import annotations

import json
import logging
import os
import threading

log = logging.getLogger("settings")

# Keys the monitor UI is allowed to change at runtime, with validation bounds.
LIVE_KEYS = {
    "pulse_s": (0.1, 120.0),    # relay ON duration per fire (pulse mode)
    "hold_ms": (0.0, 5000.0),   # how long a V must persist before it counts
    "cooldown_s": (0.0, 120.0),  # min gap between fires
}


class RuntimeSettings:
    def __init__(self, trigger_cfg: dict, sidecar_path: str | None = None):
        self._lock = threading.Lock()
        self._sidecar = sidecar_path
        self._values = {
            "relay_mode": trigger_cfg.get("relay_mode", "pulse"),
            "mode": trigger_cfg.get("mode", "time"),
            "hold_ms": float(trigger_cfg.get("hold_ms", 350)),
            "hold_frames": int(trigger_cfg.get("hold_frames", 8)),
            "cooldown_s": float(trigger_cfg.get("cooldown_s", 3.0)),
            "require_release": bool(trigger_cfg.get("require_release", True)),
            "release_ms": float(trigger_cfg.get("release_ms", 250)),
            "pulse_s": float(trigger_cfg.get("pulse_s", 5.0)),
        }
        self._load()

    def get(self, key: str):
        with self._lock:
            return self._values.get(key)

    def snapshot(self) -> dict:
        with self._lock:
            return dict(self._values)

    def live_values(self) -> dict:
        with self._lock:
            return {k: self._values[k] for k in LIVE_KEYS}

    def update(self, changes: dict) -> dict:
        """Apply operator changes (only LIVE_KEYS, clamped to bounds). Returns the
        new live values. Persists to the sidecar."""
        applied = {}
        with self._lock:
            for key, (lo, hi) in LIVE_KEYS.items():
                if key not in changes:
                    continue
                try:
                    val = float(changes[key])
                except (TypeError, ValueError):
                    continue
                val = max(lo, min(hi, val))
                self._values[key] = val
                applied[key] = val
            live = {k: self._values[k] for k in LIVE_KEYS}
        if applied:
            log.info("settings updated: %s", applied)
            self._save()
        return live

    # ----- sidecar persistence -----
    def _load(self):
        if not self._sidecar or not os.path.exists(self._sidecar):
            return
        try:
            with open(self._sidecar, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            log.warning("could not read %s: %s", self._sidecar, e)
            return
        for key, (lo, hi) in LIVE_KEYS.items():
            if key in data:
                try:
                    self._values[key] = max(lo, min(hi, float(data[key])))
                except (TypeError, ValueError):
                    pass
        log.info("loaded runtime overrides from %s: %s",
                 self._sidecar, {k: self._values[k] for k in LIVE_KEYS})

    def _save(self):
        if not self._sidecar:
            return
        try:
            with open(self._sidecar, "w", encoding="utf-8") as f:
                json.dump({k: self._values[k] for k in LIVE_KEYS}, f, indent=2)
        except Exception as e:
            log.warning("could not write %s: %s", self._sidecar, e)
