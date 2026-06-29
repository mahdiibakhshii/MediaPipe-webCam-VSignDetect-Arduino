# 05 — Deploy to Mac mini (Apple Silicon, 16 GB)

The runtime is identical to Windows. Migration = clone, install, and edit config
for the new camera indices and serial port. Budget ~30 minutes plus on-site
camera/threshold tuning.

> **For operators / on-site setup, use the double-click scripts** in [`mac/`](../mac/)
> and follow [`09-operator-guide-macos.md`](09-operator-guide-macos.md). The manual
> steps below are the underlying reference for what those scripts do.

## 1. Python (arm64, 3.10+ — important)

MediaPipe requires **Python 3.10 or newer**. macOS ships Python 3.9 via Xcode CLT
which is too old — `pip install mediapipe` will fail with a SyntaxError in a test
file. Target is **Python 3.11**.

### With admin access
```bash
brew install python@3.11          # Homebrew (recommended)
# or: download the universal2 .pkg from python.org/downloads
python3.11 -c "import platform; print(platform.machine())"   # must print: arm64
```

### Without admin access (use uv)
`uv` installs Python to the home directory — no admin needed:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.zshrc
uv python install 3.11
```

Then create the venv manually (skip step 2's `setup.command` path):
```bash
cd vsign-detect
uv venv --python 3.11 .venv
uv pip install -r requirements.txt
cp config/config.example.yaml config/config.yaml
```

## 2. Project + dependencies (with admin / native python3.11)

```bash
git clone <repo> vsign-detect && cd vsign-detect
bash mac/setup.command   # auto-selects python3.11 > python3.12 > python3.10
```

`setup.command` will error early if no suitable Python is found. `mediapipe` ships
arm64 wheels for Apple Silicon — `pip install` just works on a native arm64
interpreter.

## 3. Camera indices + serial port (macOS)

Use the built-in device probe — it lists cameras and serial ports in one shot and
prompts for camera permission automatically:

```bash
./.venv/bin/python -m src.tools.list_devices
```

Expected output example:
```
CAMERAS  (index : opens : resolution)
  0 : ok : (1920, 1080)

SERIAL PORTS
  /dev/cu.Bluetooth-Incoming-Port   - n/a
  /dev/cu.usbmodem8401              - IOUSBHostDevice   ← Arduino
```

The "out of bound" OpenCV warnings for indices 1–5 are normal noise — ignore them.
Arduino is the `usbmodem…` or `usbserial-…` entry (not Bluetooth).

Update `config.yaml`:
- `cameras[].index` → the working number (e.g. `0`)
- `serial.port` → the Arduino port (e.g. `"/dev/cu.usbmodem8401"`)
- `outputs` → serial entry → `enabled: true`

## 4. Test serial link

Before running the full engine, verify Arduino comms in isolation (close Arduino
IDE Serial Monitor first — it holds the port):

```bash
./.venv/bin/python -m src.tools.serial_test --config config/config.yaml
```

Expected: `READY`, `PONG`, `OK FIRE`, relay clicks, `DONE`.

## 5. Run

**Browser panel** (good for setup/tuning):
```bash
./.venv/bin/python -m src.bridge --config config/config.yaml --port 8000
# open http://localhost:8000/ in Safari
```

**Headless engine** (production):
```bash
./.venv/bin/python -m src.orchestrator --config config/config.yaml
```

## 6. Autostart (launchd)

Grant camera permission interactively first — run the engine once, click Allow on
the macOS prompt, then `Ctrl+C`. Background services inherit this grant.

```bash
bash mac/install-autostart.command
launchctl list | grep vsign          # confirm running
tail -f logs/out.log
```

For truly unattended operation, enable **auto-login** in System Settings →
Users & Groups → Automatic login (requires admin).

## Migration checklist

- [ ] Python 3.10+ arm64 confirmed (`platform.machine() == arm64`)
- [ ] `pip install -r requirements.txt` clean (no SyntaxError = correct Python version)
- [ ] Camera permission granted; indices set in config
- [ ] Serial `/dev/cu.*` port set in config; Arduino flashed & serial test passes
- [ ] Both zones detect; relay pulses; cooldown feels right
- [ ] CPU/thermals OK over a long run
- [ ] launchd service installed; auto-login enabled
