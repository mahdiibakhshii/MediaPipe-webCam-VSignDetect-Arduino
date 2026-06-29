#!/bin/bash
# VSign Detect — one-time setup (double-click me).
# Creates the Python environment, installs everything, and prepares config.
trap 'echo; read -r -p "Press Return to close this window."' EXIT
cd "$(dirname "$0")/.." || exit 1

echo "=================================================="
echo " VSign Detect — macOS setup"
echo "=================================================="

# Prefer explicit python3.11 over whatever python3 resolves to.
PY=""
for candidate in python3.11 python3.12 python3.10 python3; do
  if command -v "$candidate" >/dev/null 2>&1; then
    VER="$("$candidate" -c 'import sys;print(sys.version_info[:2])')"
    # Accept only (3,10) or newer
    OK="$("$candidate" -c 'import sys;print(int(sys.version_info>=(3,10)))')"
    if [ "$OK" = "1" ]; then
      PY="$candidate"
      break
    fi
  fi
done

if [ -z "$PY" ]; then
  echo "ERROR: Python 3.10+ is required but not found."
  echo
  echo "Install Python 3.11 for Apple Silicon:"
  echo "  Option A (python.org): https://www.python.org/downloads/macos/"
  echo "              → grab the macOS 64-bit universal2 installer"
  echo "  Option B (Homebrew):   brew install python@3.11"
  echo
  echo "Then run this script again."
  exit 1
fi

ARCH="$("$PY" -c 'import platform;print(platform.machine())')"
echo "Found: $("$PY" --version)  [$ARCH]  ($(command -v "$PY"))"
if [ "$ARCH" != "arm64" ]; then
  echo "WARNING: this Python is not arm64 (Apple Silicon). MediaPipe may be slow or fail."
  echo "         Install a native arm64 Python 3.11 from python.org for best results."
fi

echo
echo "Creating virtual environment (.venv) …"
"$PY" -m venv .venv || { echo "ERROR: could not create venv"; exit 1; }

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
