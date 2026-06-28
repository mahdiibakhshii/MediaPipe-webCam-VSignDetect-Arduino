# 00 — Overview

## The installation

A visitor makes a **victory sign (✌️)** in front of a camera. The system detects
it and switches a **relay** (which can drive a light, motor, sound cue, magnet,
solenoid, etc. — anything the hardware side wires to it). Two cameras cover
**two separate zones**; a gesture in either zone fires the relay.

## Signal chain

```
 ┌────────────┐     ┌────────────┐
 │  Webcam 0  │     │  Webcam 1  │     two zones, independent
 │  (Zone A)  │     │  (Zone B)  │
 └─────┬──────┘     └─────┬──────┘
       │                  │
   ┌───▼───┐          ┌───▼───┐
   │Vision │          │Vision │   MediaPipe per camera →
   │Agent A│          │Agent B│   per-frame "victory?" + confidence
   └───┬───┘          └───┬───┘
       │                  │
       └────────┬─────────┘
                ▼
        ┌───────────────┐
        │ Trigger Agent │  debounce (hold N frames) per zone,
        │  (OR zones)   │  OR across zones, enforce cooldown
        └───────┬───────┘
                ▼ "FIRE"
        ┌───────────────┐
        │ Serial Agent  │  pyserial, line protocol
        └───────┬───────┘
                ▼ USB serial
        ┌───────────────┐
        │   Arduino     │  momentary pulse: relay ON for T, then OFF
        └───────┬───────┘
                ▼
            [ Relay ]  → installation hardware
```

## Non-negotiables

- **Realtime & smooth** — low latency, no flicker/false fires. Achieved with
  temporal debounce + cooldown, not just per-frame detection.
- **CPU-only** — must run on a 16 GB Mac mini with no discrete GPU.
- **Robust** — runs for hours unattended; survives a camera or serial hiccup.
- **Portable** — same code on Windows (dev) and macOS (prod).

## Where to go next

- Why MediaPipe/Python → [`01-tech-decision.md`](01-tech-decision.md)
- How the pieces fit → [`02-architecture.md`](02-architecture.md)
- Relay & wiring → [`03-hardware-relay.md`](03-hardware-relay.md)
- Build on Windows → [`04-dev-windows.md`](04-dev-windows.md)
- Move to Mac mini → [`05-deploy-macmini.md`](05-deploy-macmini.md)
