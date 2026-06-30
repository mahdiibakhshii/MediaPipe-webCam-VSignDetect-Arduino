# Feature: Relay control

The relay can run in two modes, selected by `trigger.relay_mode`:

## pulse (default) — relay ON for a fixed time per detection

On a confirmed trigger the relay switches **ON for `pulse_s` seconds, then OFF**.
The timing is **host-owned** (the serial sink sends `ON`, then `OFF` after
`pulse_s`), so the duration is configurable **live from the monitor UI** without
reflashing. A re-trigger during the window restarts the timer (extends ON).

Keep `cooldown_s >= pulse_s` so one hold = one pulse.

## follow — relay tracks the live victory sign

The relay is **ON for exactly as long as a victory sign is present** and **OFF the
moment none is** — it mirrors the gesture in real time. A V from *any* hand in
*any* zone holds it on (OR); it releases once every zone is V-free.

`hold_ms` of V switches ON, `release_ms` of no-V switches OFF, so a single dropped
detection frame can't make it flicker. The relay state purely mirrors detection —
no watchdog or auto-release.

In both modes the relay is OFF on boot and the host sends `OFF` on clean shutdown.

## Split of responsibility

| Concern | Owner | Setting |
|---|---|---|
| Mode | Host (Trigger Agent) | `trigger.relay_mode` |
| When to fire | Host | `hold_ms`, `cooldown_s` |
| Pulse ON duration (pulse) | Host (serial sink, timed) | `trigger.pulse_s` [LIVE] |
| When ON/OFF (follow) | Host | `hold_ms`, `release_ms` |
| Relay OFF on boot | Arduino firmware | `OFF` in `setup()` |

> The firmware also has a legacy `FIRE` command (fixed `PULSE_MS` pulse), used by
> `serial_test`, but the engine drives pulses via host-timed `ON`/`OFF`.

## See also

- Wiring & BOM: [`docs/03-hardware-relay.md`](../docs/03-hardware-relay.md)
- Protocol: [`agents/serial-agent.md`](../agents/serial-agent.md)
- Firmware: [`firmware/`](../firmware/)

## Acceptance

- [ ] **pulse**: a held ✌️ turns the relay ON for `pulse_s`, then OFF; changing `pulse_s` in the monitor UI takes effect on the next fire.
- [ ] **pulse**: a re-trigger during the ON window extends it (single OFF after the last fire).
- [ ] **follow**: relay is ON while a ✌️ is held and OFF within `release_ms` of it dropping, with no flicker on a dropped frame.
- [ ] Power-cycling the Arduino leaves the relay OFF.
