#!/bin/bash
# Lists the cameras and serial ports on this Mac, to fill in config.yaml.
trap 'echo; read -r -p "Press Return to close this window."' EXIT
cd "$(dirname "$0")/.." || exit 1

if [ ! -x ".venv/bin/python" ]; then
  echo "Not set up yet — double-click setup.command first."
  exit 1
fi

echo "(macOS may ask for Camera permission — click Allow.)"
echo
./.venv/bin/python -m src.tools.list_devices
