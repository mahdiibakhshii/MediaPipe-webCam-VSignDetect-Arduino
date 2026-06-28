# Workflow: Calibration (per venue)

Run this at the dev desk, then **again on-site** — lighting and camera placement
change everything. Goal: high true-positive, near-zero false-positive, responsive
feel.

## 1. Placement & framing

- Mount each camera so a visitor's raised hand lands in the central ~⅔ of frame.
- Avoid strong backlight (window/lamp behind the hand) — silhouettes hurt
  landmarking. Aim for even, front-ish light.
- Note the working **distance**; test the gesture at that distance.

## 2. Detection threshold (`detection.min_score`)

- Start `0.6`. With `--preview`, hold ✌️ and read confidence.
- Set `min_score` a bit below the stable held-gesture confidence, but above what
  the "not victory" set produces.

## 3. Debounce feel (`trigger.hold_ms`, `cooldown_s`)

- `hold_ms`: start `350`. Too jumpy → raise; feels sluggish → lower.
- `cooldown_s`: start `3.0`. Must be ≥ firmware `PULSE_MS/1000` + a gap.
- Keep `require_release: true` so a held pose fires once.

## 4. Performance (keep both streams smooth)

- Watch CPU. If high: `fps` 30→20, `frame_skip` 0→1, `model_complexity: 0`.
- On the Mac mini also watch thermals over a long run.

## 5. False-positive sweep

Run the full system and try the "not victory" set (open palm, fist, point, three
fingers, hand at rest, two people). Tune until none fire. Re-test true positives.

## Record results

Copy the final values into the venue's `config.yaml` and note them here per venue:

```
# Venue: __________  Date: __________
# min_score: ___  hold_ms: ___  cooldown_s: ___  fps: ___  frame_skip: ___
```
