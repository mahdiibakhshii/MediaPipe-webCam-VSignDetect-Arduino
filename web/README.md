# Web control panel

A browser interface that runs the **same MediaPipe "Victory" detector** as the
Python engine, for two zones. Pick a camera per zone, tune parameters live, and
watch triggers fire. See [`../docs/07-web-interface.md`](../docs/07-web-interface.md).

## Run

It must be served over `http://localhost` (browsers only allow camera access on a
secure origin — `localhost` counts, `file://` does not).

```powershell
# from the project root, with the venv active (any Python works):
python -m http.server 8000 --directory web
```

Then open <http://localhost:8000/>, click **Enable cameras**, grant permission,
and choose a camera for Zone A and Zone B.

**To also fire the Arduino relay from the panel**, serve it via the bridge
instead and tick **Drive relay** in the header:

```powershell
.\.venv\Scripts\python.exe -m src.bridge --config config\config.yaml --port 8000
```
See [`../docs/08-web-relay-bridge.md`](../docs/08-web-relay-bridge.md).

> Needs internet on first load: MediaPipe's WASM runtime and the gesture model are
> fetched from a CDN, then browser-cached.

## What it does

- **Per zone:** camera selector (real device names), live video with hand
  landmarks, a confidence bar, a VICTORY/idle badge, and a FIRE flash.
- **Global TRIGGER** banner flashes when either zone fires (the OR logic).
- **Trigger log** of recent fires.
- **config.yaml panel** mirrors your current settings so you can paste them into
  the Python engine that drives the relay.

Settings (min score, hold, cooldown, release, camera) are saved in the browser
(localStorage) and restored on reload.
