# Workflow: Dev run

## Prereqs

Environment set up per [`docs/04-dev-windows.md`](../docs/04-dev-windows.md);
`config/config.yaml` created and edited for your machine.

## Staged bring-up (recommended)

Test each layer before wiring the whole chain.

### 1. Serial only (no camera)

Flash [`firmware/`](../firmware/), then:

```powershell
python -m src.tools.serial_test --config config\config.yaml   # sends PING, then FIRE
```

Expect: `READY`, `PONG`, `OK FIRE`, relay clicks, `DONE`.

### 2. Vision only (no relay)

```powershell
python -m src.tools.vision_test --config config\config.yaml --zone A --preview
```

Expect: a window (dev only) showing per-frame `is_victory` + confidence. Confirm
✌️ reads True and the "not victory" set reads False.

### 3. Full system

```powershell
python -m src.orchestrator --config config\config.yaml
```

Expect: log lines per fire (`zone`, `confidence`, `OK FIRE`/`DONE`), relay pulses,
cooldown respected.

> `--preview` windows are a dev aid only. The production Mac mini runs headless —
> never depend on a GUI.

## Common issues

| Symptom | Fix |
|---|---|
| Camera won't open | Wrong index; re-probe (doc 04). On Windows ensure `CAP_DSHOW`. |
| No `READY` | Wrong COM port, or Serial Monitor is holding the port — close it. |
| Fires too eagerly | Raise `trigger.hold_ms` / `detection.min_score`. |
| Misses real gestures | Lower `min_score`/`hold_ms`; improve lighting; check distance. |
| Laggy / high CPU | Lower `fps`, raise `frame_skip`, `model_complexity: 0`. |
