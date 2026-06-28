"""Plain data objects passed between agents. See agents/README.md."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ZoneSignal:
    """Raw, per-frame detection result from one camera/zone."""
    zone: str
    is_victory: bool
    confidence: float
    ts: float  # monotonic seconds


@dataclass
class TriggerEvent:
    """A debounced, confirmed trigger — the thing that fires an output."""
    zone: str
    confidence: float
    ts: float  # monotonic seconds
