# 06 — OSC output & TouchDesigner interface

During development we visualize the engine in **TouchDesigner** (or any OSC app)
so we can *see* detection + triggers before any hardware exists. OSC is a regular
output sink — the Arduino serial sink slots in later behind the same interface.

## OSC address scheme

Default prefix `/vsign` (configurable in `outputs[].prefix`).

| Address | Type | When | Meaning |
|---|---|---|---|
| `/vsign/zone/A/victory` | int `0`/`1` | every frame | raw per-frame detection for zone A |
| `/vsign/zone/A/confidence` | float `0..1` | every frame | victory confidence for zone A |
| `/vsign/zone/B/victory` | int | every frame | zone B (one set per camera/zone) |
| `/vsign/zone/B/confidence` | float | every frame | zone B |
| `/vsign/fire` | `[str, float]` | on trigger | `[zone, confidence]` — the debounced FIRE |
| `/vsign/zone/A/fire` | float | on trigger | per-zone fire pulse (= confidence) |

`/zone/*/victory` is raw (jittery — good for a live "is it seeing it" readout).
`/fire` is the clean, debounced event you'd act on. (See
[`features/trigger-debounce.md`](../features/trigger-debounce.md).)

## Configure the engine

In `config/config.yaml`, the OSC sink is on by default:

```yaml
outputs:
  - type: osc
    enabled: true
    host: "127.0.0.1"   # set to the TD machine's IP if TD runs elsewhere
    port: 7000
    prefix: "/vsign"
```

## Verify WITHOUT TouchDesigner first

Two terminals (venv active):

```powershell
python -m src.tools.osc_monitor --port 7000      # terminal 1: prints OSC
python -m src.orchestrator --config config\config.yaml   # terminal 2: the engine
```

Make a ✌️ — you'll see `victory` flip to `1`, `confidence` rise, and a `/fire`
line on each debounced trigger.

## TouchDesigner setup (interface layer)

Goal: a panel that lights up live and flashes on fire.

1. **OSC In DAT** — set **Network Port = 7000**. This shows every message as rows
   (address + values) — the simplest "it's working" view.
2. **OSC In CHOP** — same port. It exposes numeric addresses as channels
   (e.g. `zone/A/victory`, `zone/A/confidence`). Wire these to:
   - a **Level/Math CHOP → Geometry/Constant** to drive a circle's brightness or
     scale per zone (live confidence), and
   - the `fire` channel into a **Trigger CHOP** or **Speed/Lag CHOP** to flash a
     box / play a sound when it fires.
3. Optional: a **Text TOP** bound to the DAT row for `/fire` to show "ZONE A ✌".

> Tip: `/fire` carries a string (`zone`) + float in the same message. In the OSC
> In **DAT** you'll see both; in the OSC In **CHOP** you'll get the numeric part.
> For a pure-numeric pulse per zone, use `/vsign/zone/A/fire`.

## Networking notes

- Same machine → `host: 127.0.0.1`. TD on another machine → set `host` to its IP
  and open UDP `7000` in the firewall.
- OSC is UDP (fire-and-forget): if TD isn't listening, the engine doesn't care and
  keeps running.
