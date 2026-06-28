# CLAUDE.md — operating guide for agents & contributors

This repo is **documentation-driven** and **agent-structured**. Before writing
code, read the relevant spec; keep code and specs in sync.

## How this repo is organized

- **`docs/`** — durable decisions and reasoning. Numbered; read in order.
- **`agents/`** — one markdown spec per software component. Each spec is the
  contract an implementer (human or AI) builds against: responsibility, inputs,
  outputs, config keys, and acceptance criteria.
- **`features/`** — cross-cutting behavior specs (what "good" looks like).
- **`workflows/`** — operational runbooks (run / calibrate / deploy).
- **`config/config.example.yaml`** — the ONLY place machine-specific values live
  (camera indices, serial port, thresholds). Code reads config; never hardcode.

## Golden rules

1. **Portability first.** Code must run unchanged on Windows (dev) and macOS
   Apple Silicon (prod). OS differences (camera index, serial port) live in
   config, not in code. No OS-specific paths.
2. **Config over constants.** Every tunable (thresholds, hold frames, cooldown,
   pulse duration, baud) is a config key documented in the example file.
3. **Smoothness = debounce.** A raw per-frame "victory" boolean is never the
   trigger. The trigger is the *debounced* event (held N frames + cooldown). See
   [`features/trigger-debounce.md`](features/trigger-debounce.md).
4. **Fail safe.** If a camera or the serial link drops, log and keep running;
   never crash the installation. Relay defaults to OFF on disconnect.
5. **Keep it lean.** Target is a 16 GB CPU-only Mac mini running two streams.
   Prefer lower resolution / single hand / low model complexity over GPU tricks.

## Implementation order

1. `firmware/` — Arduino sketch (relay pulse + serial protocol). Testable alone.
2. `src/serial_agent` — host↔Arduino link (test with firmware, no camera).
3. `src/vision_agent` — one camera → "victory?" boolean.
4. `src/trigger_agent` — debounce + OR across zones + cooldown.
5. `src/orchestrator` — wire it together from config; logging; health.

## Conventions

- Python 3.11. Dependencies pinned in `requirements.txt`. Use a venv.
- Serial protocol is line-based ASCII, `\n`-terminated (see
  [`agents/serial-agent.md`](agents/serial-agent.md)).
- Log to stdout + a rotating file; every trigger event is logged with timestamp,
  zone, and confidence.
