# Workflow: Deploy to Mac mini (run unattended)

Migration steps are in [`docs/05-deploy-macmini.md`](../docs/05-deploy-macmini.md).
This covers running it as a **service that starts on boot and restarts on crash**.

## Option A — launchd (recommended)

Create `~/Library/LaunchAgents/com.vsign.engine.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.vsign.engine</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Users/USER/vsign-detect/.venv/bin/python</string>
    <string>-m</string><string>src.orchestrator</string>
    <string>--config</string>
    <string>/Users/USER/vsign-detect/config/config.yaml</string>
  </array>
  <key>WorkingDirectory</key><string>/Users/USER/vsign-detect</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>/Users/USER/vsign-detect/logs/out.log</string>
  <key>StandardErrorPath</key><string>/Users/USER/vsign-detect/logs/err.log</string>
</dict></plist>
```

Load it:

```bash
launchctl load ~/Library/LaunchAgents/com.vsign.engine.plist
launchctl start com.vsign.engine
# logs: tail -f ~/vsign-detect/logs/*.log
```

> **Camera permission + launchd:** a background launchd job may not get the TTY
> camera grant. If the camera is denied, run once from Terminal to trigger the
> permission prompt, grant it, then use a **LaunchAgent in the user session**
> (as above, in `~/Library/LaunchAgents`) rather than a system daemon.

## Installation hygiene

- Disable system sleep / display sleep (`pmset`) and auto-updates on the kiosk.
- Set the Mac to auto-login so the user-session LaunchAgent runs after a power
  cut.
- Confirm the Arduino re-enumerates to the same `/dev/cu.*` (or have the Serial
  Agent match by USB VID/PID if it drifts).

## Pre-show checklist

- [ ] Boot the Mac cold → service starts → both cameras detect → relay fires.
- [ ] Pull/replug Arduino → reconnects, no crash.
- [ ] Long soak run (hours) → no leak, no thermal throttle, logs healthy.
