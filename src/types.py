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
    """A debounced, confirmed trigger — a one-shot 'fire' (pulse relay mode)."""
    zone: str
    confidence: float
    ts: float  # monotonic seconds


@dataclass
class RelayState:
    """A debounced relay level change (follow relay mode).

    Emitted only on transitions: `on=True` when any zone starts holding a V,
    `on=False` when no zone holds one any more. `zone`/`confidence` describe the
    most-confident zone driving it ON (zone is None when turning OFF).
    """
    on: bool
    zone: str | None
    confidence: float
    ts: float  # monotonic seconds
