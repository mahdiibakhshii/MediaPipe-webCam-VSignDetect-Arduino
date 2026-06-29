# Agent: Serial

## Responsibility

Own the USB serial link to the Arduino. Send relay commands, handle handshakes,
and auto-reconnect. This is the only component that touches the serial port.

## Interface

```
SerialAgent(port: str, baud: int = 115200, ..., keepalive_s: float = 0.75)
  .start()                 # open port on a background thread, wait for READY
  .fire() -> bool          # send "FIRE\n" (pulse mode); True if accepted
  .set_relay(on) -> bool   # send "ON\n"/"OFF\n" (follow mode); holds the relay
  .ping() -> bool          # send "PING\n"; True if PONG within timeout
  .close()                 # releases the relay (OFF) before closing
  .is_connected: bool
```

All serial I/O runs on one background thread, so `fire()`/`set_relay()`/`ping()`
are non-blocking and thread-safe.

## Protocol (line-based ASCII, `\n`-terminated, 115200 baud)

| Direction | Message | Meaning |
|---|---|---|
| Arduino → host | `READY` | Boot complete, relay OFF |
| host → Arduino | `PING` | Liveness check |
| Arduino → host | `PONG` | Reply |
| host → Arduino | `ON` | Hold relay ON (follow mode) |
| Arduino → host | `OK ON` | Relay held ON |
| host → Arduino | `OFF` | Hold relay OFF (follow mode) |
| Arduino → host | `OK OFF` | Relay held OFF |
| host → Arduino | `FIRE` | Momentary pulse (pulse mode) |
| Arduino → host | `OK FIRE` | Pulse started |
| Arduino → host | `BUSY` | Ignored — pulse running, or relay is held ON |
| Arduino → host | `DONE` | Pulse finished, relay OFF |
| Arduino → host | `WATCHDOG OFF` | Held ON but host went silent → released |

## Behavior

- **Open**: open port, then wait up to `connect_timeout_s` for `READY`. If the
  board reset on port open (Arduino does), `READY` arrives shortly after.
- **Follow mode keepalive**: while the relay is held ON, the agent re-sends `ON`
  every `keepalive_s` so the firmware watchdog never trips. `keepalive_s` MUST be
  shorter than the firmware `WATCHDOG_MS` (default 2 s).
- **Reconnect**: on write/read error or port loss, mark disconnected, retry with
  exponential backoff (`reconnect_min_s` → `reconnect_max_s`). Never throw to the
  caller; commands just return `False` while disconnected. The last desired relay
  level is re-asserted on reconnect.
- **Fail-safe**: while disconnected the relay is physically OFF (firmware watchdog
  + board default). `close()` sends `OFF` best-effort before tearing down.
- **Health**: optional periodic `ping()` for the watchdog/logging.

## Config keys

```yaml
serial:
  port: "COM3"            # macOS: "/dev/cu.usbserial-XXXX"
  baud: 115200
  connect_timeout_s: 5
  reconnect_min_s: 1
  reconnect_max_s: 10
  keepalive_s: 0.75       # follow mode ON-refresh; must be < firmware WATCHDOG_MS
```

## Acceptance criteria

- [ ] With firmware flashed, `start()` connects and logs `READY`.
- [ ] `fire()` pulses the relay (pulse mode); logs `OK FIRE` … `DONE`.
- [ ] `set_relay(True)` holds the relay ON and it stays on while held; `set_relay(False)` releases it.
- [ ] Killing the host while the relay is held ON releases it within `WATCHDOG_MS` (no latch-on).
- [ ] Unplugging the Arduino mid-run does not crash; replugging reconnects and re-asserts state.
- [ ] No serial writes happen from more than one place.
- [ ] Works on Windows (`COMx`) and macOS (`/dev/cu.*`) with only a config change.
