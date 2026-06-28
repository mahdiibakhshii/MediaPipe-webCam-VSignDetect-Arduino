# src — Python implementation

Built against the specs in [`../agents/`](../agents/). Current layout:

```
src/
├── orchestrator.py        # entry: python -m src.orchestrator --config ...
├── config.py              # load + validate config.yaml
├── types.py               # ZoneSignal, TriggerEvent
├── models.py              # download MediaPipe .task models on first use
├── vision_agent.py        # one camera -> ZoneSignal (threaded; pluggable classifier)
├── classifiers/
│   ├── gesture_recognizer.py   # default: MediaPipe built-in "Victory"
│   └── landmark_rule.py        # fallback: geometric "V" (no model download)
├── trigger_agent.py       # debounce + OR zones + cooldown
├── serial_agent.py        # host <-> Arduino link, auto-reconnect (implemented)
├── sinks/
│   ├── osc_sink.py        # OSC -> TouchDesigner / any OSC app  (implemented)
│   ├── console_sink.py    # log fires                            (implemented)
│   └── serial_sink.py     # Arduino relay                        (implemented)
└── tools/
    ├── vision_test.py     # preview one zone's detection (--preview)
    ├── osc_monitor.py     # print incoming OSC (verify without TD)
    └── serial_test.py     # PING/FIRE the Arduino without a camera
```

## Run

```powershell
python -m src.orchestrator --config config\config.yaml      # full engine -> OSC
python -m src.tools.vision_test --config config\config.yaml --zone A --preview
python -m src.tools.osc_monitor --port 7000                 # see OSC without TD
```

OSC schema + TouchDesigner wiring: [`../docs/06-osc-touchdesigner.md`](../docs/06-osc-touchdesigner.md).

## Build order

Vision + trigger + OSC + serial relay are all implemented. The Arduino sketch is
in [`firmware/vsign_relay/`](../firmware/vsign_relay/). Enable the
relay by flashing the board, setting `serial.port`, and turning on the `serial`
output in `config.yaml`.

## Ground rules

- Read all tunables from config; no hardcoded indices/ports/thresholds.
- Same code on Windows & macOS — OS differences (capture backend) stay inside the
  agents and are chosen by platform, not config.
