# Feature: Relay control (momentary pulse)

## Behavior

On a confirmed trigger, the relay switches **ON for a fixed duration, then OFF
automatically** — a momentary pulse. Timing is owned by the **Arduino firmware**
so it is deterministic and unaffected by host load or a dropped serial link.

## Split of responsibility

| Concern | Owner | Setting |
|---|---|---|
| When to fire | Host (Trigger Agent) | `trigger.cooldown_s`, `hold_ms` |
| Pulse duration | Arduino firmware | `PULSE_MS` (default 2000) |
| Re-fire protection | Both | host cooldown + firmware `BUSY` while pulsing |

Rule: `trigger.cooldown_s >= PULSE_MS/1000 + a small gap`.

## Fail-safe

- Relay is **OFF on boot** and **OFF after every pulse**.
- A dropped host link cannot leave the relay latched (pulse self-terminates).
- Pulse uses `millis()` (non-blocking) so the board stays responsive.

## See also

- Wiring & BOM: [`docs/03-hardware-relay.md`](../docs/03-hardware-relay.md)
- Protocol: [`agents/serial-agent.md`](../agents/serial-agent.md)
- Firmware: [`firmware/`](../firmware/)

## Acceptance

- [ ] One trigger → one clean pulse of `PULSE_MS`, then OFF.
- [ ] Extra triggers during a pulse are ignored (`BUSY`), not queued.
- [ ] Power-cycling the Arduino leaves the relay OFF.
