# 09 — Operator guide (macOS)

A simple, click-by-click guide to set up and run VSign Detect on the Mac mini.
No coding needed. All the tools are double-clickable files in the **`mac`** folder.

---

## One-time first step: unlock the buttons

If you got the project with **`git clone`**, the buttons are already runnable —
**skip to Setup below.** Only do this if you downloaded a **ZIP** (which loses the
"runnable" flag):

1. Open **Terminal** (press `Cmd`+`Space`, type *Terminal*, press Return).
2. Type exactly this, **with a space at the end**, but don't press Return yet:
   ```
   chmod +x 
   ```
3. Drag the **`mac`** folder from Finder onto the Terminal window (this pastes its
   location), then type `/*.command` after it and press **Return**. The line will
   look like:
   ```
   chmod +x /Users/you/vsign-detect/mac/*.command
   ```

That's it — from now on everything is double-click.

---

## Setup (do once)

1. **Double-click `setup.command`.** It installs everything (a few minutes) and
   prepares the settings file. Wait for "SETUP COMPLETE", then close the window.

   > **If you see "Python 3.10+ is required":** the Mac's built-in Python is too
   > old. If you don't have an admin password, open Terminal and run:
   > ```bash
   > curl -LsSf https://astral.sh/uv/install.sh | sh
   > source ~/.zshrc
   > uv python install 3.11
   > cd ~/vsign-detect
   > uv venv --python 3.11 .venv
   > uv pip install -r requirements.txt
   > cp config/config.example.yaml config/config.yaml
   > ```
   > Then skip to step 2.

2. **Double-click `find-devices.command`.** Allow the camera prompt. It lists your
   cameras (with numbers) and the Arduino port. **Write these down**, e.g.:
   - Built-in camera = `0`, USB camera = `1`
   - Arduino = `/dev/cu.usbserial-1420`

3. **Edit the settings.** Open `config/config.yaml` (double-click → open with
   TextEdit) and set:
   - the two camera **`index:`** values to your camera numbers,
   - **`serial: port:`** to your Arduino port,
   - under `outputs:` → the `serial` one → **`enabled: true`**.

   Save and close.

4. **Test it. Double-click `open-panel.command`.** A web page opens. Click
   **Enable cameras**, pick a camera for each zone, and make a ✌️ — you should see
   it light up. Tick **Drive relay** and the relay should click on a ✌️. Close the
   window when done.

5. **Grant camera permission for background use.** Double-click
   `start-engine.command`, click **Allow** on the camera prompt, let it run for a
   few seconds, then close the window. This must happen once so the background
   service is allowed to use the cameras.

6. **Make it run on boot. Double-click `install-autostart.command`.** Now the
   system starts automatically whenever the Mac turns on, and restarts itself if
   it ever stops.

   > **Also enable auto-login** so the Mac doesn't wait at the login screen:
   > **System Settings → Users & Groups → Automatic login → pick the user.**
   > (Requires admin password — ask whoever manages the machine.)

---

## Daily operation

- **It just runs.** Turn the Mac on → it starts by itself → a ✌️ fires the relay.
- **To restart everything:** restart the Mac, or run `uninstall-autostart.command`
  then `install-autostart.command`.
- **To run it by hand (no autostart):** double-click `start-engine.command`
  (close the window to stop).
- **To change cameras/sensitivity later:** edit `config/config.yaml`, then restart
  the Mac (or re-run the autostart installer).

## Where to look if something's wrong

- Logs are in the **`logs`** folder: `out.log` and `err.log`.
- Re-run `find-devices.command` if a camera or the Arduino moved to a new
  number/port, and update `config/config.yaml` to match.

## Troubleshooting

| Problem | Fix |
|---|---|
| "can't be opened / unidentified developer" | Right-click the file → **Open** → **Open** (only needed the first time per file). |
| Buttons open a text editor instead of running | The one-time `chmod` step above wasn't done — do it. |
| Relay never clicks | In `config.yaml`, is the `serial` output `enabled: true` and the `port` correct? Re-check with `find-devices.command`. |
| Camera is black / not detected | Allow camera access: **System Settings → Privacy & Security → Camera**. Re-run `find-devices.command` to confirm the number. |
| Two cameras show the same number | You need two separate physical cameras; pick the correct one for each zone. |
| Fires too easily / too rarely | Edit `config.yaml`: raise/lower `detection: min_score` and `trigger: hold_ms`. |

## The buttons at a glance

| File | What it does |
|---|---|
| `setup.command` | Installs everything (run once). |
| `find-devices.command` | Shows camera numbers + Arduino port. |
| `open-panel.command` | Opens the web panel to verify cameras / test the relay. |
| `start-engine.command` | Runs the detector by hand (close window to stop). |
| `install-autostart.command` | Makes it start on boot & restart on crash. |
| `uninstall-autostart.command` | Turns off autostart. |
