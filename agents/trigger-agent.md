# Agent: Trigger

## Responsibility

Turn noisy per-frame `ZoneSignal`s into clean, well-timed `FIRE` events. This is
where "smoothness" lives — debounce, OR across zones, and cooldown.

## Interface

```
TriggerAgent(trigger_cfg: dict, on_fire: Callable[[TriggerEvent], None])
  .submit(sig: ZoneSignal)   # called for every frame from every zone
# calls on_fire(TriggerEvent) at most once per (cooldown) window
```

## Logic

Per **zone**, keep a short rolling history. A zone is **ACTIVE** when it has been
`is_victory=True` for `hold_frames` consecutive frames **OR** for at least
`hold_ms` (time-based is more robust across variable FPS — prefer it).

```
on submit(sig):
    update zone[sig.zone] history with (is_victory, ts)
    zone_active = held_true_for(zone, hold_ms)

    if any zone_active and now - last_fire >= cooldown_s:
        choose the active zone with highest confidence
        last_fire = now
        on_fire(TriggerEvent{zone, confidence, ts})
```

- **OR across zones**: a gesture in *either* zone fires (zones are independent —
  see [`features/dual-camera.md`](../features/dual-camera.md)).
- **Cooldown**: after firing, ignore new fires for `cooldown_s`. Prevents machine
  re-triggering while someone holds the pose.
- **Release** (optional): require the gesture to drop (a `release_ms` gap of
  `is_victory=False`) before the zone can arm again, so one continuous hold = one
  fire even after cooldown. Recommended ON.

## Why time-based, not pure frame count

FPS varies with CPU load. `hold_ms` gives consistent feel regardless of whether a
camera runs at 18 or 30 fps. `hold_frames` is offered as an alternative for
deterministic testing.

## Config keys

```yaml
trigger:
  mode: time              # time | frames
  hold_ms: 350            # gesture must persist this long to count (time mode)
  hold_frames: 8          # used when mode=frames
  cooldown_s: 3.0         # min gap between fires (>= firmware PULSE_MS/1000 + gap)
  require_release: true
  release_ms: 250         # gesture must drop this long before re-arming
```

## Acceptance criteria

- [ ] A brief flash of a false-positive frame does NOT fire (filtered by hold).
- [ ] A held ✌️ fires exactly once, then not again until released + cooldown.
- [ ] A gesture in either zone fires; simultaneous zones still fire once.
- [ ] Tunable entirely from config; defaults feel responsive (~0.3–0.5 s).
