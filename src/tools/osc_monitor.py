"""Print incoming OSC messages — verify the engine's OSC output without TouchDesigner.

    python -m src.tools.osc_monitor --port 7000
"""
from __future__ import annotations

import argparse

from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import BlockingOSCUDPServer


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=7000)
    args = ap.parse_args()

    dispatcher = Dispatcher()
    dispatcher.set_default_handler(lambda addr, *a: print(addr, list(a)))

    server = BlockingOSCUDPServer((args.host, args.port), dispatcher)
    print(f"Listening for OSC on {args.host}:{args.port} (Ctrl-C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")


if __name__ == "__main__":
    main()
