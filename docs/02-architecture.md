# 02 — Architecture

## Components (one agent spec each)

| Component | Responsibility | Spec |
|---|---|---|
| **Orchestrator** | Load config, start/stop agents, main loop, logging, health/watchdog | [`agents/orchestrator-agent.md`](../agents/orchestrator-agent.md) |
| **Vision Agent** (×2) | One camera → per-frame `(is_victory, confidence)` | [`agents/vision-agent.md`](../agents/vision-agent.md) |
| **Trigger Agent** | Debounce per zone, OR across zones, cooldown → emit `FIRE` | [`agents/trigger-agent.md`](../agents/trigger-agent.md) |
| **Serial Agent** | Reliable line-based link to Arduino | [`agents/serial-agent.md`](../agents/serial-agent.md) |

## Data flow

```
VisionAgent(zoneA) ─┐  ZoneSignal{zone, is_victory, conf, ts}
VisionAgent(zoneB) ─┴──────────────► TriggerAgent ──► "FIRE" ──► SerialAgent ──► Arduino
```

- **ZoneSignal**: emitted every processed frame, per camera.
- **TriggerAgent** keeps a short rolling state per zone. A zone is "active" when
  it has been `is_victory` for `hold_frames` consecutive frames (or within a time
  window). If **any** zone becomes active and we're not in cooldown → emit one
  `FIRE`, then start `cooldown_seconds`.

## Concurrency model

- **One worker per camera** (thread or process). MediaPipe releases the GIL
  during native inference, so **threads** are the default; if CPU contention is
  bad on the Mac mini, switch a camera worker to a **process** (config flag).
- Workers push `ZoneSignal`s onto a thread-safe queue.
- The Orchestrator/Trigger loop drains the queue, runs debounce, and calls the
  Serial Agent. Serial writes happen on a single owner (the main loop) to avoid
  interleaving.

```
[Cam0 worker thread] ─┐
                      ├─ Queue ─► [main loop: TriggerAgent → SerialAgent]
[Cam1 worker thread] ─┘
```

## Performance budget (16 GB CPU-only Mac mini, two streams)

| Lever | Default | Why |
|---|---|---|
| Capture resolution | 640×480 | Plenty for hand detection; quarter the pixels of 720p |
| Target FPS | 20–30 | Smooth enough for a held gesture; lighter than 60 |
| `num_hands` | 1 | One hand per zone is enough to fire |
| Model complexity | low/lite | Faster; accuracy is fine for one clear gesture |
| Frame skip | optional | Process every Nth frame if CPU is tight |

Two lite hand pipelines at 640×480 fit comfortably; tune in
[`workflows/calibration.md`](../workflows/calibration.md).

## Failure handling (fail safe)

- Camera read fails → log, attempt reopen with backoff; other zone keeps working.
- Serial disconnect → log, attempt reconnect with backoff; **relay defaults OFF**
  (firmware also auto-OFF after pulse, so a dropped link can't leave it latched).
- Unhandled exception in a worker → restart that worker, don't kill the process.

## Config is the contract

Everything machine-specific or tunable is in
[`config/config.example.yaml`](../config/config.example.yaml). Copy it to
`config/config.yaml` per machine. Code never hardcodes indices, ports, or
thresholds.
