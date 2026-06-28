# Feature: Dual camera (two zones)

## Intent

Two webcams cover **two separate zones/angles**. A victory sign in **either**
zone fires the relay. The zones are independent detectors, logically **OR'd**.

## Design

- One [`VisionAgent`](../agents/vision-agent.md) per camera, each tagged with a
  `zone` name (`"A"`, `"B"`).
- Each runs on its own worker (thread by default; process if CPU-bound) and emits
  `ZoneSignal`s into a shared queue.
- The [`TriggerAgent`](../agents/trigger-agent.md) debounces **per zone**, then
  ORs: any active zone (not in cooldown) → one `FIRE`. If both go active at once,
  still one fire (highest-confidence zone is recorded in the event).

## Why per-zone debounce (not global)

A visitor in zone A and noise in zone B shouldn't combine. Each zone earns its
own "held long enough" state; the OR happens only on already-debounced states.

## CPU note

Two lite pipelines at 640×480 fit the 16 GB CPU-only Mac mini. If tight: lower
fps, raise `frame_skip`, or move one camera worker to `worker: process`. See
[`docs/02-architecture.md`](../docs/02-architecture.md).

## Acceptance

- [ ] ✌️ in zone A fires; ✌️ in zone B fires; neither blocks the other.
- [ ] Both zones simultaneously → exactly one fire per cooldown window.
- [ ] Each zone's detection is logged with its zone label.
