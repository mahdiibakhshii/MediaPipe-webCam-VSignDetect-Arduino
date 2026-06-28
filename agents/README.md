# Agents

Each file here is a **component spec** — the contract an implementer (human or AI)
builds against. A spec defines: responsibility, inputs, outputs, config keys, and
acceptance criteria. Implement in this order (each is testable before the next):

1. [`serial-agent.md`](serial-agent.md) — host ↔ Arduino link (test with firmware, no camera)
2. [`vision-agent.md`](vision-agent.md) — one camera → "victory?" boolean
3. [`trigger-agent.md`](trigger-agent.md) — debounce + OR zones + cooldown
4. [`orchestrator-agent.md`](orchestrator-agent.md) — wire everything from config

"Agent" here means a **single-responsibility software component**, not an LLM.
They communicate via plain data objects (see
[`docs/02-architecture.md`](../docs/02-architecture.md)).

## Shared data types

```
ZoneSignal:
  zone: str          # e.g. "A"
  is_victory: bool   # this frame's raw detection
  confidence: float  # 0.0–1.0
  ts: float          # monotonic timestamp (seconds)

TriggerEvent:
  zone: str          # which zone caused the fire
  confidence: float
  ts: float
```
