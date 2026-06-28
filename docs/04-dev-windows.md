# 04 — Dev environment (Windows, now)

Develop here; the code is written to migrate to the Mac mini unchanged. Only
config values (camera index, serial port) differ between machines.

## Prerequisites

- **Python 3.11** (MediaPipe supports 3.9–3.12; 3.11 is the target).
  Verify: `python --version`.
- A webcam (two for full testing; one is enough to start).
- Arduino IDE (to flash [`firmware/`](../firmware/)) — optional until the serial
  stage.

## Setup

```powershell
# from the project root
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy config\config.example.yaml config\config.yaml
```

## Find your camera indices (Windows)

Cameras are indices `0,1,2…`. They are **not stable across machines** — this is
exactly why they live in config. Quick probe:

```python
import cv2
for i in range(5):
    cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)   # DSHOW = faster open on Windows
    print(i, cap.isOpened())
    cap.release()
```

Put the working indices into `config/config.yaml` (`cameras[].index`).

> Note: on Windows the code uses the `CAP_DSHOW` backend for faster camera open;
> on macOS the default `AVFoundation` backend is used. The Vision Agent selects
> the backend by platform automatically — you don't set it in config.

## Find your serial port (Windows)

Arduino shows up as `COMx`. Check **Device Manager → Ports (COM & LPT)** or:

```powershell
python -c "import serial.tools.list_ports as p; print([x.device for x in p.comports()])"
```

Put e.g. `COM3` into `config/config.yaml` (`serial.port`).

## Run

See [`workflows/dev-run.md`](../workflows/dev-run.md). Typical:

```powershell
python -m src.orchestrator --config config\config.yaml
```

## Portability rules while developing

- Never hardcode `COM3`, camera `0`, or a Windows path — use config.
- Use `pathlib` / forward-slash-safe paths, no `C:\...` literals in code.
- Keep all OS branching inside the Vision/Serial agents (backend selection only).
- Pin every new dependency in `requirements.txt`.
