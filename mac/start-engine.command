#!/bin/bash
# Run the headless detection engine (production runtime).
# Close this window to stop it.
cd "$(dirname "$0")/.." || exit 1

if [ ! -x ".venv/bin/python" ]; then
  echo "Not set up yet — double-click setup.command first."
  read -r -p "Press Return to close."; exit 1
fi

echo "Starting VSign Detect engine…  (close this window to stop)"
echo "(If macOS asks for Camera permission, click Allow, then start again.)"
echo
exec ./.venv/bin/python -m src.orchestrator --config config/config.yaml
