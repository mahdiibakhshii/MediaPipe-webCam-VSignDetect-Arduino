# 08 — Web → relay bridge

Lets the **browser control panel drive the Arduino relay directly**. Detection
still runs in the browser; the bridge gives the browser's triggers a path to the
hardware through the *same* output sinks the engine uses.

## How it works

```
browser panel (detects ✌)  ──POST /api/fire──►  bridge (src/bridge.py)
                                                    │  dispatches TriggerEvent
                                                    ▼
                                        output sinks (serial → Arduino, OSC, console)
```

The bridge is a tiny stdlib HTTP server (no extra dependencies) that **also serves
the panel**, so the panel and the API share one origin (no CORS headaches) and one
command.

## Run it (instead of `python -m http.server`)

```powershell
.\.venv\Scripts\python.exe -m src.bridge --config config\config.yaml --port 8000
```

Open <http://localhost:8000/>, **Enable cameras**, then tick **Drive relay** in the
header. The dot next to it shows relay status:

| Dot | Meaning |
|---|---|
| 🟢 green | bridge up, Arduino connected |
| 🔴 red | bridge up, Arduino **not** connected (check `serial.port` / flashing) |
| ⚪ grey | bridge not running (panel served by plain `http.server`) — relay toggle disabled |

For the relay to actually fire, enable the serial output in `config/config.yaml`:

```yaml
outputs:
  - type: serial
    enabled: true        # <- on
serial:
  port: "COM5"           # your Arduino port
```

## API (same origin as the panel)

| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/api/status` | – | `{"serial_connected": true\|false\|null}` |
| POST | `/api/ping` | – | `{"ok": true\|false}` |
| POST | `/api/fire` | `{"zone":"A","confidence":0.9}` | `{"ok":true,"served":["SerialSink",...]}` |

`null` status = no serial sink enabled. `/api/fire` enforces a server-side
**min-interval** (defaults to `trigger.cooldown_s`) so a chatty browser can't
hammer the relay; rapid repeats get `{"ok":false,"reason":"cooldown"}`.

## Engine vs. bridge — when to use which

| | Headless engine (`src.orchestrator`) | Bridge (`src.bridge`) |
|---|---|---|
| Detection | Python (on the engine host) | Browser |
| Best for | Production install on the Mac mini | Setup/tuning where you also want the relay to react |
| Relay | yes (serial sink) | yes (same serial sink) |

They share `config.yaml` and the same sink code. Don't point both at the same
serial port at once (only one process can own it).

## Verified

Automated test (`scratchpad/bridge_test.py`): static serving, `/api/status`,
`/api/fire` (dispatches to Console+Serial sinks), the cooldown rejection, and
`/api/ping` — all working with a disconnected board, no crashes.
