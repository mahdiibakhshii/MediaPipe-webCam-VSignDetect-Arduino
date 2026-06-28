# Agent: Serial

## Responsibility

Own the USB serial link to the Arduino. Send `FIRE`, handle handshakes, and
auto-reconnect. This is the only component that touches the serial port.

## Interface

```
SerialAgent(port: str, baud: int = 115200, write_timeout: float = 0.5)
  .open() -> bool          # open port, wait for READY (with timeout)
  .fire() -> bool          # send "FIRE\n"; returns True if accepted (OK FIRE)
  .ping() -> bool          # send "PING\n"; True if PONG within timeout
  .close()
  .is_connected: bool
```

## Protocol (line-based ASCII, `\n`-terminated, 115200 baud)

| Direction | Message | Meaning |
|---|---|---|
| Arduino → host | `READY` | Boot complete, relay OFF |
| host → Arduino | `PING` | Liveness check |
| Arduino → host | `PONG` | Reply |
| host → Arduino | `FIRE` | Pulse relay now |
| Arduino → host | `OK FIRE` | Pulse started |
| Arduino → host | `BUSY` | Ignored — pulse already running |
| Arduino → host | `DONE` | Pulse finished, relay OFF |

## Behavior

- **Open**: open port, then wait up to `connect_timeout_s` for `READY`. If the
  board reset on port open (Arduino does), `READY` arrives shortly after.
- **Reconnect**: on write/read error or port loss, mark disconnected, retry with
  exponential backoff (`reconnect_min_s` → `reconnect_max_s`). Never throw to the
  caller; `fire()` just returns `False` while disconnected.
- **Thread safety**: a single owner (the main loop) calls `fire()`. If accessed
  from multiple threads, guard with a lock.
- **Health**: optional periodic `ping()` for the watchdog/logging.

## Config keys

```yaml
serial:
  port: "COM3"            # macOS: "/dev/cu.usbserial-XXXX"
  baud: 115200
  connect_timeout_s: 5
  reconnect_min_s: 1
  reconnect_max_s: 10
```

## Acceptance criteria

- [ ] With firmware flashed, `open()` returns True and logs `READY`.
- [ ] `fire()` pulses the relay and returns True; logs `OK FIRE` … `DONE`.
- [ ] Unplugging the Arduino mid-run does not crash; replugging reconnects.
- [ ] No serial writes happen from more than one place.
- [ ] Works on Windows (`COMx`) and macOS (`/dev/cu.*`) with only a config change.
