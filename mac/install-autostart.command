#!/bin/bash
# Install a LaunchAgent so the engine starts automatically on login and
# restarts if it ever crashes. Double-click to install.
trap 'echo; read -r -p "Press Return to close this window."' EXIT
cd "$(dirname "$0")/.." || exit 1

if [ ! -x ".venv/bin/python" ]; then
  echo "Not set up yet — double-click setup.command first."
  exit 1
fi

ROOT="$(pwd)"
PY="$ROOT/.venv/bin/python"
LABEL="com.vsign.engine"
AGENTS="$HOME/Library/LaunchAgents"
PLIST="$AGENTS/$LABEL.plist"

mkdir -p "$AGENTS" "$ROOT/logs"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PY</string>
    <string>-m</string><string>src.orchestrator</string>
    <string>--config</string><string>$ROOT/config/config.yaml</string>
  </array>
  <key>WorkingDirectory</key><string>$ROOT</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$ROOT/logs/out.log</string>
  <key>StandardErrorPath</key><string>$ROOT/logs/err.log</string>
</dict>
</plist>
EOF

launchctl unload "$PLIST" 2>/dev/null
launchctl load "$PLIST" || { echo "ERROR: launchctl load failed"; exit 1; }

echo "Installed autostart: $LABEL"
echo "  • Starts on login and restarts on crash."
echo "  • Logs: $ROOT/logs/out.log  and  err.log"
echo
echo "IMPORTANT — Camera permission:"
echo "  Run start-engine.command ONCE and click Allow on the camera prompt first,"
echo "  so the background service is allowed to use the cameras."
echo
echo "To remove autostart later: double-click uninstall-autostart.command"
