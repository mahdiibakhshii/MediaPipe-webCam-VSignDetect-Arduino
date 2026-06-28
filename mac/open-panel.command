#!/bin/bash
# Open the browser control panel (with relay bridge) for setup / testing.
# Close this window to stop it.
cd "$(dirname "$0")/.." || exit 1

if [ ! -x ".venv/bin/python" ]; then
  echo "Not set up yet — double-click setup.command first."
  read -r -p "Press Return to close."; exit 1
fi

echo "Starting control panel at http://localhost:8000/  (close this window to stop)"
echo "In the page: click 'Enable cameras', pick a camera per zone, tick 'Drive relay' to test."
( sleep 2; open "http://localhost:8000/" ) >/dev/null 2>&1 &
exec ./.venv/bin/python -m src.bridge --config config/config.yaml --port 8000
