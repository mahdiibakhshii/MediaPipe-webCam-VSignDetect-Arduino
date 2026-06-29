"""OSC output sink — drives a TouchDesigner (or any OSC) interface.

Address scheme (prefix default '/vsign'); see docs/06-osc-touchdesigner.md:
  per frame:  {prefix}/zone/{zone}/victory      int 0|1
              {prefix}/zone/{zone}/confidence   float 0..1
  on fire:    {prefix}/fire                     [zone:str, confidence:float]
              {prefix}/zone/{zone}/fire         float confidence
  on relay:   {prefix}/relay                    int 0|1   (follow mode)
              {prefix}/relay/zone               str | ""  (driving zone, "" when off)
"""
from __future__ import annotations

import logging

from pythonosc.udp_client import SimpleUDPClient

log = logging.getLogger(__name__)


class OscSink:
    def __init__(self, host: str, port: int, prefix: str = "/vsign"):
        self._client = SimpleUDPClient(host, port)
        self._prefix = prefix.rstrip("/")

    def on_signal(self, sig):
        base = f"{self._prefix}/zone/{sig.zone}"
        try:
            self._client.send_message(f"{base}/victory", int(sig.is_victory))
            self._client.send_message(f"{base}/confidence", float(sig.confidence))
        except OSError as e:  # don't let a network hiccup kill the loop
            log.debug("osc send_signal failed: %s", e)

    def on_fire(self, ev):
        try:
            self._client.send_message(f"{self._prefix}/fire",
                                      [ev.zone, float(ev.confidence)])
            self._client.send_message(f"{self._prefix}/zone/{ev.zone}/fire",
                                      float(ev.confidence))
        except OSError as e:
            log.debug("osc send_fire failed: %s", e)

    def on_state(self, ev):
        try:
            self._client.send_message(f"{self._prefix}/relay", int(ev.on))
            self._client.send_message(f"{self._prefix}/relay/zone", ev.zone or "")
        except OSError as e:
            log.debug("osc send_state failed: %s", e)
