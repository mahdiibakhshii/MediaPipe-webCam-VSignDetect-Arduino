# Firmware (Arduino)

Drives the relay as a **momentary pulse** on `FIRE`, using non-blocking timing.
Implements the serial protocol in [`../agents/serial-agent.md`](../agents/serial-agent.md)
and the hardware notes in [`../docs/03-hardware-relay.md`](../docs/03-hardware-relay.md).

## Sketch spec (`vsign_relay/vsign_relay.ino`)

Constants (edit to match your hardware):

```cpp
const uint8_t  RELAY_PIN = 7;       // digital pin to relay IN
const bool     ACTIVE_LOW = false;  // true if module turns ON when IN = LOW
const uint32_t PULSE_MS   = 2000;   // relay ON duration per fire
const uint32_t BAUD       = 115200;
```

Behavior:
- `setup()`: relay OFF, `Serial.begin(BAUD)`, print `READY`.
- `loop()`: read lines; on `PING` → `PONG`; on `FIRE` → if idle, start pulse,
  print `OK FIRE`; if pulsing, print `BUSY`. Use `millis()` to end the pulse
  (never `delay()`), then set relay OFF and print `DONE`.
- Relay helper respects `ACTIVE_LOW`.

## Flashing

1. Arduino IDE → open the sketch → select board + port → Upload.
2. Close the Serial Monitor before running the host app (only one program can
   own the port).

## Standalone test (no host)

Open Serial Monitor at 115200, line ending = Newline. Type `FIRE` → relay clicks
for `PULSE_MS`, you see `OK FIRE` then `DONE`. Type `PING` → `PONG`.

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
