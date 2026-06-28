# 01 — Technology decision

## Decision

**Detect the victory sign with Google MediaPipe, driven from Python.**
No TouchDesigner / Max / vvvv in the runtime — the installation is a *pure
trigger* with no visual output, so a headless Python engine is the leanest and
most portable choice.

## Options considered

| Approach | Realtime | CPU-only (Mac mini) | Effort | Verdict |
|---|---|---|---|---|
| **MediaPipe Gesture Recognizer** | ★★★★★ | ★★★★★ | ★ | **Chosen for v1.** Ships a built-in `Victory` class (one of 7 canned gestures) — zero training. |
| **MediaPipe Hand Landmarker + geometric rule** | ★★★★★ | ★★★★★ | ★★ | **Chosen as the tunable fallback.** 21 landmarks/hand; we define "V" ourselves for precise control over false positives. |
| TouchDesigner + MediaPipe plugin | ★★★★ | ★★★ | ★★★ | Rejected: only worth it if there were visuals/projection. Heavier on 16 GB. |
| Custom CNN / Teachable Machine / YOLO | ★★★ | ★★ | ★★★★ | Rejected: overkill + brittle for one static gesture; wants a GPU. |
| OpenPose / heavy pose nets | ★★ | ★ | ★★★★★ | Rejected: GPU-hungry. |

## Why MediaPipe

- **Built-in "Victory."** The Gesture Recognizer task recognizes 7 gestures
  including `Victory` — we get a working detector on day one.
- **CPU realtime.** Designed for mobile/CPU; runs two streams comfortably on
  Apple Silicon at reduced resolution.
- **Identical on Windows & macOS.** arm64 wheels exist for Apple Silicon, so the
  same code migrates with no changes.
- **Landmarks available.** If the canned classifier ever mis-fires, we switch the
  Vision Agent to the landmark-rule classifier (same pipeline) for full control.

## The classifier is pluggable

The [`Vision Agent`](../agents/vision-agent.md) exposes a single interface:
`frame → (is_victory: bool, confidence: float)`. Behind it we can run **either**
the Gesture Recognizer **or** the landmark-geometric rule, selected in config.
Start with Gesture Recognizer; swap if needed. The rest of the system never
changes.

### Landmark-geometric rule (the fallback definition of "V")

Using MediaPipe's 21 hand landmarks:
- **Index** and **middle** fingers **extended** (tip is far from the wrist /
  above the PIP joint).
- **Ring** and **pinky** fingers **folded** (tip below their PIP joint).
- Optionally: index–middle tips **spread apart** (the "V" gap) and **thumb
  tucked**.
This is a few lines of vector math and is extremely robust for one gesture.

## Stack

| Layer | Choice |
|---|---|
| Language | Python 3.11 |
| Capture | OpenCV (`opencv-python`) |
| Detection | `mediapipe` (Tasks API: Gesture Recognizer / Hand Landmarker) |
| Serial | `pyserial` |
| Config | `pyyaml` |
| Firmware | Arduino C++ |

## What we explicitly are NOT doing

- No model training, no datasets, no GPU.
- No TouchDesigner/Max/vvvv at runtime (can be bridged later via OSC if visuals
  are ever added — out of scope now).
