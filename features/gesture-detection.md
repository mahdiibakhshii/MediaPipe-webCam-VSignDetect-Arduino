# Feature: Victory-sign detection

## What "good" looks like

- Detects a clear ✌️ (index + middle extended, ring + pinky folded, thumb tucked)
  within ~0.3–0.5 s of the visitor holding it.
- Works across a reasonable range of hand angles, distances, and skin tones.
- Does **not** fire on: open palm, fist, single pointing finger, three fingers,
  or a hand at rest.
- Robust to typical installation lighting; degrades gracefully in dim light.

## How it's built

MediaPipe, two interchangeable classifiers behind one interface (see
[`agents/vision-agent.md`](../agents/vision-agent.md)):

- **`gesture_recognizer`** (default): built-in `Victory` class, fastest path.
- **`landmark_rule`** (fallback): geometric test on 21 hand landmarks for full
  control over the exact definition and false-positive behavior.

Detection is **per-frame and raw**; turning it into a trustworthy event is the
job of [`trigger-debounce`](trigger-debounce.md).

## Multiple hands & people

`num_hands` (default 4) sets how many hands MediaPipe tracks per frame, so either
of a person's hands — or several people in frame — are all considered. The
classifier reports `is_victory=True` if **any** tracked hand is a ✌️ (logical OR);
no per-hand identity is needed. Higher `num_hands` costs more CPU per frame, so
keep it to what the venue needs.

## Tuning knobs

`detection.min_score`, `model_complexity`, `num_hands`, and (for landmark_rule)
`spread_min` / `require_thumb_tucked`. See
[`workflows/calibration.md`](../workflows/calibration.md).

## Acceptance

- [ ] True-positive rate high on deliberate ✌️ at the install distance.
- [ ] Near-zero false positives on the "not victory" set above.
- [ ] Switching classifier requires only a config change.
