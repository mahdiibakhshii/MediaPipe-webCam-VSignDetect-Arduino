# Agent: Orchestrator

## Responsibility

The entry point. Load config, construct and start every other agent, run the main
loop, wire `FIRE` → relay, log everything, and keep the installation alive.

## Interface

```
python -m src.orchestrator --config config/config.yaml
```

## Startup sequence

1. Load + validate config (fail loudly on missing required keys).
2. Init logging (stdout + rotating file; one line per trigger).
3. Construct `SerialAgent`; `open()` (log if Arduino missing, keep going — it can
   reconnect).
4. Construct one `VisionAgent` per `cameras[]` entry, sharing one queue.
5. Construct `TriggerAgent` with `on_fire = lambda ev: serial.fire()`.
6. Start all vision workers.

## Main loop

```
while running:
    sig = queue.get(timeout=...)
    trigger.submit(sig)          # may call on_fire -> serial.fire()
    periodically: watchdog + serial.ping() + heartbeat log
```

- **on_fire** logs `TriggerEvent` (ts, zone, confidence) and calls
  `serial.fire()`; logs the serial result.
- **Watchdog**: if a vision worker has emitted nothing for `stale_s`, restart it.
- **Shutdown**: on SIGINT/SIGTERM, stop workers, `serial.close()`, flush logs.

## Config keys

```yaml
app:
  log_level: INFO
  log_file: logs/vsign.log
  watchdog_stale_s: 5
  heartbeat_s: 30
```

(Plus the `cameras`, `detection`, `trigger`, `serial` sections owned by the other
agents — one config file, see [`config/config.example.yaml`](../config/config.example.yaml).)

## Acceptance criteria

- [ ] Single command starts the whole system from config.
- [ ] Runs with the Arduino absent (logs, reconnects when plugged in).
- [ ] A crashing camera worker is restarted; the process stays up.
- [ ] Ctrl-C shuts down cleanly (relay ends OFF, port closed).
- [ ] Every fire is logged with timestamp, zone, and confidence.
