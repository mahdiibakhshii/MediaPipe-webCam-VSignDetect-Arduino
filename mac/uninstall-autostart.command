#!/bin/bash
# Remove the autostart LaunchAgent. Double-click to uninstall.
trap 'echo; read -r -p "Press Return to close this window."' EXIT

LABEL="com.vsign.engine"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

if [ -f "$PLIST" ]; then
  launchctl unload "$PLIST" 2>/dev/null
  rm -f "$PLIST"
  echo "Removed autostart: $LABEL"
else
  echo "Autostart was not installed (nothing to remove)."
fi
