# 07 — Web control panel

A self-contained browser UI ([`web/`](../web/)) for **picking cameras, tuning
detection, and watching triggers** — the friendliest interface layer for setup.

## Why browser-based

Browsers expose **real camera device names** and a one-click permission flow, so
choosing "which webcam is Zone A" is trivial — far better UX than OpenCV's numeric
indices. It runs the **same MediaPipe Gesture Recognizer ("Victory")** as the
Python engine (Tasks for Web, v0.10.35), and mirrors the exact debounce logic, so
what you see here matches the engine's behavior.

## Relationship to the Python engine

| | Web panel | Python engine |
|---|---|---|
| Role | Setup / tuning / live monitoring | Production runtime |
| Detection | MediaPipe Tasks **for Web** (in browser) | MediaPipe **Python** |
| Output | On-screen indicators + trigger log | OSC now; Arduino relay next |
| Runs on | Any browser | Headless on the Mac mini |

They use the **same model and the same parameter names**. The panel shows a live
`config.yaml` snippet so you tune visually, then paste into
[`config/config.yaml`](../config/config.example.yaml) for the engine that fires
the relay.

> The panel does not drive the relay itself (detection happens in the browser,
> not on the engine host). A future option: have the panel POST fire events to a
> small endpoint on the engine so the browser can drive the relay directly. Out of
> scope for now.

## Run

```powershell
python -m http.server 8000 --directory web
```

Open <http://localhost:8000/> → **Enable cameras** → grant permission → pick a
camera per zone. Must be `localhost` (camera access needs a secure origin).

## Controls (per zone)

- **Camera** — choose the device for this zone.
- **Min score** — confidence required to count a frame as "Victory"
  (= `detection.min_score`).
- **Hold (ms)** — how long the gesture must persist to fire (= `trigger.hold_ms`).
- **Cooldown (s)** — minimum gap between fires (= `trigger.cooldown_s`).
- **Release (ms)** — gesture must drop this long before re-arming
  (= `trigger.release_ms`).

All settings persist in the browser and restore on reload.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Camera dropdown empty | Click **Enable cameras** and **Allow** the permission prompt. Then it auto-fills. If it stays empty, open the console (F12) — the panel logs the detected video inputs under `[VSign Detect]`. |
| Empty after a code update | Hard-refresh to bust the cache: **Ctrl+Shift+R**. |
| Many virtual cams; default fails | Handled: the panel tolerates a failing default device, still lists everything, and lets you pick your built-in / USB cam. Plugging a USB cam auto-refreshes the list. |
| Windows blocks access | Settings → Privacy & security → Camera → allow apps/desktop apps to use the camera. |
| Camera list empty / no labels | Use `http://localhost`, not `file://` (camera access needs a secure origin). |
| Same camera for both zones | Two OS-level cameras are needed for two distinct feeds; otherwise pick the one device for both. |
| Model never loads | First load needs internet (CDN). Check the console; corporate proxies may block jsDelivr. |
| Laggy | Lower the browser tab count; the panel caps processing at ~30 fps per zone. |
