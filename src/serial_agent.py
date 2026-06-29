"""Host <-> Arduino serial link with auto-reconnect. See agents/serial-agent.md.

All serial I/O happens on one background thread, so callers (fire/ping) are
non-blocking and thread-safe. The link never throws to the caller: while
disconnected, fire()/ping() just return False and the thread keeps retrying.
"""
from __future__ import annotations

import logging
import queue
import threading
import time

import serial  # pyserial

log = logging.getLogger("serial")


class SerialAgent:
    def __init__(self, port: str, baud: int = 115200, connect_timeout_s: float = 5,
                 reconnect_min_s: float = 1, reconnect_max_s: float = 10, **_ignored):
        self.port = port
        self.baud = int(baud)
        self.connect_timeout_s = float(connect_timeout_s)
        self.reconnect_min_s = float(reconnect_min_s)
        self.reconnect_max_s = float(reconnect_max_s)

        self._ser = None
        self._connected = threading.Event()
        self._stop = threading.Event()
        self._cmd_q: "queue.Queue[bytes]" = queue.Queue()
        self._pong = threading.Event()
        self._thread = None
        self._relay_on = False  # desired held state (follow mode), asserted on reconnect

    # ----- public API -----
    @property
    def is_connected(self) -> bool:
        return self._connected.is_set()

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="serial", daemon=True)
        self._thread.start()

    def wait_connected(self, timeout: float) -> bool:
        return self._connected.wait(timeout)

    def fire(self) -> bool:
        if not self._connected.is_set():
            return False
        self._cmd_q.put(b"FIRE\n")
        return True

    def set_relay(self, on: bool) -> bool:
        """Hold the relay ON or OFF (follow mode). Idempotent; remembers the
        desired state so it can be re-asserted after a reconnect."""
        self._relay_on = bool(on)
        if not self._connected.is_set():
            return False
        self._cmd_q.put(b"ON\n" if on else b"OFF\n")
        return True

    def ping(self, timeout: float = 1.0) -> bool:
        if not self._connected.is_set():
            return False
        self._pong.clear()
        self._cmd_q.put(b"PING\n")
        return self._pong.wait(timeout)

    def close(self):
        # Best-effort: release the relay before tearing down (fail-safe OFF).
        if self._connected.is_set() and self._ser is not None:
            try:
                self._ser.write(b"OFF\n")
            except Exception:
                pass
        self._relay_on = False
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        self._close_port()

    # ----- internals (background thread only) -----
    def _open_port(self) -> bool:
        try:
            self._ser = serial.Serial(self.port, self.baud, timeout=0.1, write_timeout=1.0)
        except Exception as e:
            log.warning("cannot open %s: %s", self.port, e)
            self._ser = None
            return False
        # Arduino resets when the port opens; wait for its READY greeting.
        deadline = time.monotonic() + self.connect_timeout_s
        while time.monotonic() < deadline and not self._stop.is_set():
            line = self._read_line()
            if line is None:
                continue
            log.info("<- %s", line)
            if line == "READY":
                return True
        log.warning("opened %s but saw no READY within %.1fs (continuing)",
                    self.port, self.connect_timeout_s)
        return True

    def _read_line(self):
        raw = self._ser.readline()  # may raise on disconnect; caller handles
        if not raw:
            return None
        return raw.decode("ascii", "replace").strip()

    def _close_port(self):
        if self._ser is not None:
            try:
                self._ser.close()
            except Exception:
                pass
        self._ser = None
        self._connected.clear()

    def _run(self):
        backoff = self.reconnect_min_s
        while not self._stop.is_set():
            if self._ser is None:
                if self._open_port():
                    self._connected.set()
                    backoff = self.reconnect_min_s
                    # Re-assert the desired relay level after a (re)connect.
                    try:
                        self._ser.write(b"ON\n" if self._relay_on else b"OFF\n")
                    except Exception:
                        pass
                    log.info("connected on %s", self.port)
                else:
                    self._close_port()
                    self._stop.wait(backoff)
                    backoff = min(backoff * 2, self.reconnect_max_s)
                continue

            try:
                # send any queued commands
                try:
                    while True:
                        cmd = self._cmd_q.get_nowait()
                        self._ser.write(cmd)
                        log.info("-> %s", cmd.decode().strip())
                except queue.Empty:
                    pass

                # read one response line (blocks up to the read timeout)
                line = self._read_line()
                if line:
                    log.info("<- %s", line)
                    if line == "PONG":
                        self._pong.set()
            except Exception as e:
                log.warning("link error (%s) — reconnecting", e)
                self._close_port()
                self._stop.wait(backoff)
                backoff = min(backoff * 2, self.reconnect_max_s)

        self._close_port()
