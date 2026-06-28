# 05 — Deploy to Mac mini (Apple Silicon, 16 GB)

The runtime is identical to Windows. Migration = clone, install, and edit config
for the new camera indices and serial port. Budget ~30 minutes plus on-site
camera/threshold tuning.

> **For operators / on-site setup, use the double-click scripts** in [`mac/`](../mac/)
> and follow [`09-operator-guide-macos.md`](09-operator-guide-macos.md). The manual
> steps below are the underlying reference for what those scripts do.

## 1. Python (arm64 — important)

Install an **arm64** Python 3.11 (Homebrew `python@3.11` or python.org universal2
running natively). Verify it is NOT under Rosetta:

```bash
python3 -c "import platform; print(platform.machine())"   # must print: arm64
```

If it prints `x86_64`, you're under Rosetta — reinstall a native arm64 Python, or
MediaPipe will be slow/unavailable.

## 2. Project + dependencies

```bash
git clone <repo> vsign-detect && cd vsign-detect
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config/config.example.yaml config/config.yaml
```

`mediapipe` ships arm64 wheels for Apple Silicon — `pip install` just works on a
native arm64 interpreter.

## 3. Camera indices (macOS)

Same probe, no `CAP_DSHOW` (AVFoundation is default):

```python
import cv2
for i in range(5):
    cap = cv2.VideoCapture(i)
    print(i, cap.isOpened()); cap.release()
```

First run will prompt for **Camera permission** (System Settings → Privacy &
Security → Camera) — grant it to the terminal/app running Python. Update
`config.yaml` camera indices.

## 4. Serial port (macOS)

Arduino appears as `/dev/cu.usbserial-XXXX` or `/dev/cu.usbmodemXXXX`:

```bash
ls /dev/cu.*
```

Set `serial.port` in `config.yaml` accordingly. (Use the `cu.*` device, not
`tty.*`.)

## 5. Run & tune

```bash
python -m src.orchestrator --config config/config.yaml
```

Re-run on-site calibration ([`workflows/calibration.md`](../workflows/calibration.md)) —
lighting and camera placement differ from the dev desk. Tune resolution/FPS to
keep both streams smooth on the CPU.

## 6. Run unattended (optional)

Wrap as a `launchd` agent (macOS service) so it starts on boot and restarts on
crash. Details in [`workflows/deploy-macmini.md`](../workflows/deploy-macmini.md).

## Migration checklist

- [ ] arm64 Python confirmed (`platform.machine() == arm64`)
- [ ] `pip install -r requirements.txt` clean
- [ ] Camera permission granted; indices set in config
- [ ] Serial `/dev/cu.*` port set in config; Arduino flashed
- [ ] Both zones detect; relay pulses; cooldown feels right
- [ ] CPU/thermals OK over a long run
- [ ] (optional) launchd service installed
