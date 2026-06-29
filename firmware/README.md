# Firmware (Arduino)

Drives the relay in two host-selectable modes, using non-blocking timing:
- **follow** — relay is *held* ON/OFF by the host to track a live victory sign
  (`ON`/`OFF` commands). This is the default.
- **pulse** — a **momentary pulse** on `FIRE` (legacy mode).

Implements the serial protocol in [`../agents/serial-agent.md`](../agents/serial-agent.md)
and the hardware notes in [`../docs/03-hardware-relay.md`](../docs/03-hardware-relay.md).

## Sketch spec (`vsign_relay/vsign_relay.ino`)

Constants (edit to match your hardware):

```cpp
const uint8_t  RELAY_PIN  = 7;      // digital pin to relay IN
const bool     ACTIVE_LOW = false;  // true if module turns ON when IN = LOW
const uint32_t PULSE_MS   = 2000;   // relay ON duration per FIRE pulse
const uint32_t BAUD       = 115200;
```

Behavior:
- `setup()`: relay OFF, `Serial.begin(BAUD)`, print `READY`.
- `loop()`: read lines; on `PING` → `PONG`; on `ON` → hold relay ON, print
  `OK ON`; on `OFF` → release, print `OK OFF`; on `FIRE` → if idle and not held,
  start pulse and print `OK FIRE`, else `BUSY`. Use `millis()` for pulse end
  (`DONE`) — never `delay()`.
- Relay helper respects `ACTIVE_LOW`.
- The relay state purely mirrors what the host sends — there is no watchdog or
  auto-release timer.

## Flashing

1. Arduino IDE → open the sketch → select board + port → Upload.
2. Close the Serial Monitor before running the host app (only one program can
   own the port).

## Standalone test (no host)

Open Serial Monitor at 115200, line ending = Newline. Type `ON` → relay switches
on and stays on (`OK ON`); type `OFF` → it releases (`OK OFF`). Type `FIRE` →
relay clicks for `PULSE_MS` (`OK FIRE` … `DONE`). Type `PING` → `PONG`.

## Test from the engine (no camera)

After flashing, set `serial.port` in `config/config.yaml`, then:

```powershell
.\.venv\Scripts\python.exe -m src.tools.serial_test --config config\config.yaml
```

Expect: `READY`, `PONG ✓`, then `OK FIRE` … `DONE` with the relay clicking.

## Flashing with arduino-cli (optional, scriptable)

```bash
arduino-cli compile  --fqbn arduino:avr:uno firmware/vsign_relay
arduino-cli upload   --fqbn arduino:avr:uno -p COM5 firmware/vsign_relay
```

(Use your board's FQBN and port. The Arduino IDE works too.)
