# Feature: Trigger debounce & cooldown

This is what makes the trigger feel **smooth and intentional** instead of jittery.
Implemented in the [`TriggerAgent`](../agents/trigger-agent.md).

## The three guards

1. **Hold-to-confirm** — the gesture must persist for `hold_ms` (~350 ms default)
   before it counts. Kills single-frame false positives.
2. **Cooldown** — after a fire, ignore new fires for `cooldown_s` (default 3 s,
   ≥ the firmware pulse length). Stops machine-gun re-triggering.
3. **Release-to-rearm** (recommended) — the gesture must drop for `release_ms`
   before it can fire again, so one continuous hold = one fire.

## Timeline (default values)

```
victory held ───┐(350ms)┌─ FIRE ──────── cooldown 3s ──────── armed again
not victory ────┘       └─ relay pulses 2s (firmware) ─┘   (after release)
```

## Time-based by default

`hold` and `release` are measured in **milliseconds**, not frames, so behavior is
consistent whether a camera runs at 18 or 30 fps. A `frames` mode exists for
deterministic tests.

## Tuning

All in config under `trigger:` — `hold_ms`, `cooldown_s`, `require_release`,
`release_ms`. Tune for the venue in
[`workflows/calibration.md`](../workflows/calibration.md).

## Acceptance

- [ ] A 1–2 frame false positive never fires.
- [ ] A deliberate held ✌️ fires once, ~0.3–0.5 s after the pose is formed.
- [ ] Holding the pose does not re-fire; releasing + re-posing does.
