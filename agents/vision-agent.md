# Agent: Vision (one per camera)

## Responsibility

Capture frames from ONE camera and emit, per processed frame, whether a victory
sign is present. One instance per zone.

## Interface

```
VisionAgent(zone: str, camera_cfg: dict, detection_cfg: dict, sink: Queue)
  .start()    # begins capture loop on its own worker (thread or process)
  .stop()
# emits ZoneSignal{zone, is_victory, confidence, ts} onto `sink` per frame
```

## Pipeline

1. **Open camera** by `index`. Backend by platform: `CAP_DSHOW` on Windows,
   default (AVFoundation) on macOS. Set resolution + FPS from config.
2. **Read frame**; on failure, log + reopen with backoff (don't kill the loop).
3. **Detect** with the configured classifier (pluggable):
   - `gesture_recognizer` (default): MediaPipe Gesture Recognizer →
     `is_victory = (top_gesture == "Victory" and score >= min_score)`.
   - `landmark_rule`: MediaPipe Hand Landmarker → geometric "V" test
     (index+middle extended, ring+pinky folded; optional thumb-tuck & spread).
4. **Emit** `ZoneSignal`. Raw per-frame only — **no debounce here** (that's the
   Trigger Agent's job).
5. Optional `frame_skip`: process every Nth frame to save CPU.

## Classifier detail — landmark_rule

Using 21 landmarks (wrist=0; tips: index=8, middle=12, ring=16, pinky=20; PIPs:
6,10,14,18):
- A finger is **extended** if its tip is farther from the wrist than its PIP
  (handle hand orientation via the wrist→middle-MCP axis, not raw screen-Y, so it
  works at angles).
- `is_victory = index_extended AND middle_extended AND NOT ring_extended AND NOT
  pinky_extended` (+ optional: thumb folded, index/middle tip spread > threshold).

## Config keys

```yaml
cameras:
  - zone: "A"
    index: 0
    width: 640
    height: 480
    fps: 30
    frame_skip: 0          # 0 = every frame; 1 = every other; ...
    worker: thread         # thread | process

detection:
  classifier: gesture_recognizer   # gesture_recognizer | landmark_rule
  min_score: 0.6                    # min confidence for "Victory"
  num_hands: 4                      # max hands tracked/frame; ANY hand = a V (multi-person)
  model_complexity: 0               # 0 = lite/fast
  # landmark_rule extras:
  spread_min: 0.0                   # 0 = ignore index/middle gap check
  require_thumb_tucked: false
```

## Acceptance criteria

- [ ] Emits ~`fps` ZoneSignals/sec for its zone.
- [ ] Holding a clear ✌️ yields `is_victory=True` with stable confidence.
- [ ] An open palm, fist, or pointing finger yields `is_victory=False`.
- [ ] Swapping `classifier` in config changes the detector with no other changes.
- [ ] A disconnected/again-connected camera self-recovers without crashing.
- [ ] Two instances run together within the CPU budget (see architecture).
