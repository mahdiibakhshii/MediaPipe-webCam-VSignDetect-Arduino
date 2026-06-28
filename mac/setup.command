#!/bin/bash
# VSign Detect — one-time setup (double-click me).
# Creates the Python environment, installs everything, and prepares config.
trap 'echo; read -r -p "Press Return to close this window."' EXIT
cd "$(dirname "$0")/.." || exit 1

echo "=================================================="
echo " VSign Detect — macOS setup"
echo "=================================================="

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: Python 3 is not installed."
  echo "Install it (Apple Silicon) from https://www.python.org/downloads/ and run this again."
  exit 1
fi

ARCH="$(python3 -c 'import platform;print(platform.machine())')"
echo "Found: $(python3 --version)  [$ARCH]"
if [ "$ARCH" != "arm64" ]; then
  echo "WARNING: this Python is not arm64 (Apple Silicon). MediaPipe may be slow or fail."
  echo "         Prefer a native arm64 Python 3.11."
fi

echo
echo "Creating virtual environment (.venv) …"
python3 -m venv .venv || { echo "ERROR: could not create venv"; exit 1; }

echo "Installing dependencies (this can take a few minutes) …"
./.venv/bin/python -m pip install --upgrade pip >/dev/null
./.venv/bin/python -m pip install -r requirements.txt || { echo "ERROR: pip install failed"; exit 1; }

if [ ! -f config/config.yaml ]; then
  cp config/config.example.yaml config/config.yaml
  echo "Created config/config.yaml from the example."
else
  echo "config/config.yaml already exists — keeping it."
fi

echo
echo "SETUP COMPLETE."
echo "Next steps:"
echo "  1) Double-click  find-devices.command   (note your camera numbers + Arduino port)"
echo "  2) Edit          config/config.yaml      (set those values; enable the relay)"
echo "  3) Double-click  open-panel.command      (verify cameras / test the relay)"
echo "  4) Double-click  install-autostart.command  (so it runs on boot)"
