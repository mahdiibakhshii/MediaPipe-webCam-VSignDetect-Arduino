# VSign Detect

Realtime **victory-sign (✌️) gesture detection** on two live webcams that fires a
hardware **relay** (via Arduino) when the gesture is seen. Built as a lean,
headless engine for a media installation.

> Reference gesture: [`Victory.jpeg`](Victory.jpeg) — index + middle finger
> extended in a "V", ring + pinky folded, thumb tucked.

## What it does (one line)

`two webcams → MediaPipe hand detection → "victory?" → debounce + cooldown → serial "FIRE" → Arduino → relay pulse`

## Quickstart

One-time setup (Windows; see [docs/04-dev-windows.md](docs/04-dev-windows.md)):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy config\config.example.yaml config\config.yaml
```

**A) Browser control panel** — pick cameras, tune, watch triggers (easiest):

```powershell
python -m http.server 8000 --directory web
```
Open <http://localhost:8000/> → **Enable cameras** → grant permission → choose a
camera per zone. See [docs/07-web-interface.md](docs/07-web-interface.md).

**A+) Panel that also fires the relay** — serve via the bridge instead, then tick
**Drive relay** in the header:

```powershell
.\.venv\Scripts\python.exe -m src.bridge --config config\config.yaml --port 8000
```
See [docs/08-web-relay-bridge.md](docs/08-web-relay-bridge.md).

**B) Python engine** — the production runtime (emits OSC now, relay next):

```powershell
.\.venv\Scripts\python.exe -m src.orchestrator --config config\config.yaml
# optional, another terminal — see the OSC without TouchDesigner:
.\.venv\Scripts\python.exe -m src.tools.osc_monitor --port 7000
```

Quick detector preview with a video window:
```powershell
.\.venv\Scripts\python.exe -m src.tools.vision_test --config config\config.yaml --zone A --preview
```

## Core decisions (locked)

| Topic | Decision |
|---|---|
| Detector | **MediaPipe** (Google), driven from **Python** — CPU-only, cross-platform, no training |
| Two cameras | **Two zones / coverage** — victory in *either* camera fires the trigger |
| Output | **Pure trigger** — no visuals; only the relay fires (headless engine) |
| Relay behavior | **Momentary pulse** — relay ON for a configurable duration, then auto-OFF, with cooldown |
| Dev now | **Windows**, engineered for portability |
| Final target | **Mac mini (Apple Silicon), 16 GB RAM** — same Python code |

## Repository map

| Path | Purpose |
|---|---|
| [`docs/`](docs/) | The thinking: overview, tech decision, architecture, hardware, dev & deploy |
| [`agents/`](agents/) | Component specs (orchestrator, vision, trigger, serial) — implement against these |
| [`features/`](features/) | Feature-level specs (detection, dual-camera, debounce, relay) |
| [`workflows/`](workflows/) | How to run, calibrate, and deploy |
| [`config/`](config/) | `config.example.yaml` — the single source of per-machine settings |
| [`firmware/`](firmware/) | Arduino sketch + protocol |
| [`mac/`](mac/) | Double-click operator scripts for the Mac mini (setup/run/autostart) |
| [`src/`](src/) | Python implementation (built against the specs) |
| [`CLAUDE.md`](CLAUDE.md) | Operating guide for AI agents / contributors |

## Status

📐 **Design phase.** Docs and specs are written; `src/` and `firmware/` are next.
Start at [`docs/00-overview.md`](docs/00-overview.md).
