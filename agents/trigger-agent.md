# Agent: Trigger

## Responsibility

Turn noisy per-frame `ZoneSignal`s into a clean, well-timed relay signal. This is
where "smoothness" lives — debounce and OR across zones. A signal counts as a
victory if **any** hand in **any** zone shows a V (the classifier already ORs
across hands; the trigger ORs across zones).

Two relay modes (config `relay_mode`):

- **pulse** (default): one debounced hold = one `TriggerEvent`, gated by
  `cooldown_s`. The serial sink then holds the relay ON for `pulse_s` seconds
  (host-timed, so the duration is tunable live from the monitor UI).
- **follow**: the relay tracks *presence* — ON while a V is held, OFF when it's
  gone. Emits `RelayState` on transitions only.

`hold_ms`, `cooldown_s`, and `pulse_s` are read live from `RuntimeSettings`, so
the monitor UI can retune them without a restart (persisted to
`config/runtime.json`).

## Interface

```
TriggerAgent(trigger_cfg, on_fire: Callable[[TriggerEvent], None],
                          on_state: Callable[[RelayState], None] = None)
  .submit(sig: ZoneSignal)   # called for every frame from every zone
# follow mode: calls on_state(RelayState{on,...}) on each ON/OFF transition
# pulse  mode: calls on_fire(TriggerEvent) at most once per cooldown window
```

## Logic

Per **zone**, keep a short rolling history. A zone has **held long enough** when it
has been `is_victory=True` for `hold_frames` consecutive frames **OR** for at least
`hold_ms` (time-based is more robust across variable FPS — prefer it).

**Follow mode** (level, with hysteresis so a single dropped frame can't flicker):

```
on submit(sig):
    update zone[sig.zone] history with (is_victory, ts)
    zone.on True  when held_true_for(zone, hold_ms)
    zone.on False when held_false_for(zone, release_ms)
    relay_on = OR(zone.on for all zones)
    if relay_on changed: on_state(RelayState{on, driving_zone, confidence, ts})
```

**Pulse mode** (edge):

```
    if any zone_active and now - last_fire >= cooldown_s:
        choose the active zone with highest confidence
        last_fire = now
        on_fire(TriggerEvent{zone, confidence, ts})
```

- **OR across zones**: a gesture in *either* zone counts (zones are independent —
  see [`features/dual-camera.md`](../features/dual-camera.md)).
- **Anti-flicker (follow)**: `hold_ms` to turn ON, `release_ms` of no-V to turn
  OFF. Keeps the relay steady through momentary detection dropouts.
- **Cooldown (pulse)**: after firing, ignore new fires for `cooldown_s`.
- **Release (pulse, optional)**: require the gesture to drop (a `release_ms` gap of
  `is_victory=False`) before the zone can arm again, so one continuous hold = one
  fire even after cooldown. Recommended ON.

## Why time-based, not pure frame count

FPS varies with CPU load. `hold_ms` gives consistent feel regardless of whether a
camera runs at 18 or 30 fps. `hold_frames` is offered as an alternative for
deterministic testing.

## Config keys

```yaml
trigger:
  relay_mode: pulse       # pulse | follow
  mode: time              # time | frames  (how the hold below is measured)
  hold_ms: 350            # V must persist this long before it counts (time mode) [LIVE]
  hold_frames: 8          # used when mode=frames
  release_ms: 250         # follow: no-V this long → OFF | pulse: drop before re-arm
  pulse_s: 5.0            # pulse: relay ON duration per detection (host-timed) [LIVE]
  cooldown_s: 5.0         # pulse: min gap between fires; keep >= pulse_s [LIVE]
  require_release: true   # pulse: one continuous hold = one fire
```

`[LIVE]` keys are editable at runtime from the monitor UI.

## Acceptance criteria

- [ ] A brief flash of a false-positive frame does NOT engage the relay (filtered by hold).
- [ ] **follow**: relay turns ON while any hand (any zone) holds a V and OFF once none do.
- [ ] **follow**: a single dropped detection frame does not flicker the relay.
- [ ] **pulse**: a held ✌️ fires exactly once, then not again until released + cooldown.
- [ ] A gesture in either zone counts; simultaneous zones behave as one OR.
- [ ] Tunable entirely from config; defaults feel responsive (~0.3–0.5 s).
