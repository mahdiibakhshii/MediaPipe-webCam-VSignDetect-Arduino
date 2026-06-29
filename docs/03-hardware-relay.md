# 03 — Hardware: Arduino + relay

## Goal

Drive a relay from the host in one of two modes:

- **follow** (default): the host **holds** the relay ON/OFF (`ON`/`OFF`) so it
  tracks a live victory sign. A firmware **watchdog** releases it if the host goes
  silent, so it can never latch on.
- **pulse** (legacy): on `FIRE` the Arduino switches the **relay ON for a
  configurable duration, then OFF automatically** (momentary pulse). Timing lives
  on the Arduino so it is deterministic and survives host hiccups.

## Bill of materials

| Item | Notes |
|---|---|
| Arduino Uno / Nano (or compatible) | Any board with USB serial + a digital pin |
| Relay module (opto-isolated, 1ch) | Pick coil voltage = board logic (5V typical). Opto-isolation strongly recommended. |
| USB cable | Data-capable (host ↔ Arduino) |
| Flyback protection | On-module for most relay breakouts; add a diode if using a bare relay/coil |
| The switched load | Whatever the installation drives (mains? use a properly rated, safety-certified relay/SSR and follow local electrical code) |

> ⚠️ **Mains safety:** if the relay switches mains voltage, that wiring must be
> done by someone qualified, enclosed, fused, and to code. The low-voltage logic
> in this repo never touches mains.

## Wiring (logic side)

| Arduino pin | To |
|---|---|
| `D7` (configurable `RELAY_PIN`) | Relay module `IN` |
| `5V` | Relay module `VCC` |
| `GND` | Relay module `GND` |

Some relay modules are **active-LOW** (IN=LOW turns relay ON). The firmware has
an `ACTIVE_LOW` flag — set it to match your module. Test with a known command
before trusting it.

## Serial protocol

Line-based ASCII, `115200` baud, `\n`-terminated. Full spec in
[`agents/serial-agent.md`](../agents/serial-agent.md).

| Direction | Message | Meaning |
|---|---|---|
| Arduino → host | `READY` | Boot complete, relay OFF |
| host → Arduino | `PING` | Liveness check |
| Arduino → host | `PONG` | Reply to PING |
| host → Arduino | `ON` / `OFF` | Hold relay ON / OFF (follow mode) |
| Arduino → host | `OK ON` / `OK OFF` | Held state set |
| host → Arduino | `FIRE` | Pulse the relay now (pulse mode) |
| Arduino → host | `OK FIRE` | Pulse started |
| Arduino → host | `DONE` | Pulse finished, relay OFF |

While a pulse is active, additional `FIRE` commands are **ignored** by the
firmware (it replies `BUSY`) — host-side cooldown should already prevent this,
but the firmware is the last line of defense.

## Timing

- `PULSE_MS` (firmware constant, default `2000`) — pulse-mode relay ON duration.
  Host-side `cooldown_s` should be ≥ `PULSE_MS` plus a gap.
## Safe defaults

- On boot: relay **OFF**.
- Non-blocking timing using `millis()` (never `delay()`), so the board stays
  responsive to serial.
- Relay state purely mirrors what the host sends — no watchdog or auto-release.

Firmware lives in [`firmware/`](../firmware/).
