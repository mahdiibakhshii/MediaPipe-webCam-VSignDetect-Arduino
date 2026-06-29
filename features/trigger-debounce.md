# Feature: Trigger debounce & cooldown

This is what makes the trigger feel **smooth and intentional** instead of jittery.
Implemented in the [`TriggerAgent`](../agents/trigger-agent.md).

A signal counts as a victory if **any** hand in **any** zone shows a V (the
classifier ORs across hands, the trigger ORs across zones). The guards below then
smooth that combined signal.

## follow mode (default): hold + release hysteresis

The relay tracks presence with two debounce edges:

1. **Hold-to-confirm** — a V must persist for `hold_ms` (~350 ms) before the relay
   turns ON. Kills single-frame false positives.
2. **Release-to-clear** — no V for `release_ms` (~250 ms) before it turns OFF. A
   momentary detection dropout while the pose is still held does not flicker it.

```
victory held ───┐(350ms)┌──── relay ON (held) ────┐(no V 250ms)
not victory ────┘        └─ ON ──────────────────  └─ OFF
```

## pulse mode (legacy): hold + cooldown + rearm

1. **Hold-to-confirm** — same `hold_ms` gate.
2. **Cooldown** — after a fire, ignore new fires for `cooldown_s` (default 3 s,
   ≥ the firmware pulse length). Stops machine-gun re-triggering.
3. **Release-to-rearm** (recommended) — the gesture must drop for `release_ms`
   before it can fire again, so one continuous hold = one fire.

```
victory held ───┐(350ms)┌─ FIRE ──────── cooldown 3s ──────── armed again
not victory ────┘       └─ relay pulses 2s (firmware) ─┘   (after release)
```

## Time-based by default

`hold` and `release` are measured in **milliseconds**, not frames, so behavior is
consistent whether a camera runs at 18 or 30 fps. A `frames` mode exists for
deterministic tests.

## Tuning

All in config under `trigger:` — `relay_mode`, `hold_ms`, `release_ms`, and
(pulse mode) `cooldown_s`, `require_release`. Tune for the venue in
[`workflows/calibration.md`](../workflows/calibration.md).

## Acceptance

- [ ] A 1–2 frame false positive never engages the relay.
- [ ] **follow**: the relay is ON ~0.3–0.5 s after a ✌️ is formed and OFF ~`release_ms` after it drops.
- [ ] **follow**: a brief detection dropout while the pose is held does not flicker the relay.
- [ ] **pulse**: a deliberate held ✌️ fires once; holding does not re-fire, releasing + re-posing does.
