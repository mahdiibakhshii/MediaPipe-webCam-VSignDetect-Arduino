# Feature: Relay control

The relay can run in two modes, selected by `trigger.relay_mode`:

## follow (default) — relay tracks the live victory sign

The relay is **ON for exactly as long as a victory sign is present** and **OFF the
moment none is** — it mirrors the gesture in real time. A V from *any* hand in
*any* zone holds it on (OR); it releases once every zone is V-free.

The host holds the relay with `ON`/`OFF` commands. A small debounce smooths it:
`hold_ms` of V to switch ON, `release_ms` of no-V to switch OFF, so a single
dropped detection frame can't make it flicker.

### Fail-safe

The firmware runs a **watchdog**: while held ON it expects the host to keep
talking (the host re-sends `ON` every `serial.keepalive_s`). If the board hears
nothing for `WATCHDOG_MS` (default 2 s) it releases the relay and prints
`WATCHDOG OFF`. So a crashed host, a pulled USB cable, or app shutdown can never
leave the relay latched on. Relay is also OFF on boot and on a clean `close()`.

## pulse (legacy) — momentary pulse per trigger

On a confirmed trigger the relay switches **ON for a fixed duration, then OFF
automatically**. Timing is owned by the **Arduino firmware** (`PULSE_MS`) so it is
deterministic and unaffected by host load.

Rule: `trigger.cooldown_s >= PULSE_MS/1000 + a small gap`.

## Split of responsibility

| Concern | Owner | Setting |
|---|---|---|
| Mode | Host (Trigger Agent) | `trigger.relay_mode` |
| When ON/OFF (follow) | Host | `hold_ms`, `release_ms` |
| When to fire (pulse) | Host | `cooldown_s`, `hold_ms` |
| Pulse duration (pulse) | Arduino firmware | `PULSE_MS` (default 2000) |
| Held-ON fail-safe (follow) | Arduino firmware + host keepalive | `WATCHDOG_MS`, `serial.keepalive_s` |

## See also

- Wiring & BOM: [`docs/03-hardware-relay.md`](../docs/03-hardware-relay.md)
- Protocol: [`agents/serial-agent.md`](../agents/serial-agent.md)
- Firmware: [`firmware/`](../firmware/)

## Acceptance

- [ ] **follow**: relay is ON while a ✌️ is held and OFF within `release_ms` of it dropping.
- [ ] **follow**: a single dropped detection frame does not flicker the relay.
- [ ] **follow**: killing the host (or pulling USB) while held ON releases the relay within `WATCHDOG_MS`.
- [ ] **pulse**: one trigger → one clean pulse of `PULSE_MS`, then OFF; extra triggers during a pulse are `BUSY`.
- [ ] Power-cycling the Arduino leaves the relay OFF.
