"""One camera -> per-frame ZoneSignal. Runs on its own thread. See agents/vision-agent.md."""
from __future__ import annotations

import logging
import platform
import threading
import time
from typing import Callable

import cv2

from .classifiers import make_classifier
from .types import ZoneSignal

log = logging.getLogger(__name__)


def open_capture(index: int, width: int, height: int, fps: int):
    """Open a camera with the right backend per OS (DSHOW on Windows)."""
    if platform.system() == "Windows":
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    else:
        cap = cv2.VideoCapture(index)  # AVFoundation default on macOS
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS, fps)
    return cap


class VisionAgent(threading.Thread):
    def __init__(self, zone: str, camera_cfg: dict, detection_cfg: dict,
                 model_path: str | None, emit: Callable[[ZoneSignal], None]):
        super().__init__(daemon=True, name=f"vision-{zone}")
        self.zone = zone
        self.camera_cfg = camera_cfg
        self.detection_cfg = detection_cfg
        self.model_path = model_path
        self.emit = emit
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def _open(self):
        return open_capture(
            self.camera_cfg["index"],
            self.camera_cfg.get("width", 640),
            self.camera_cfg.get("height", 480),
            self.camera_cfg.get("fps", 30),
        )

    def run(self):
        # Build the classifier inside this thread (MediaPipe graph is thread-bound).
        classifier = make_classifier(self.detection_cfg, self.model_path)
        cap = self._open()
        frame_skip = int(self.camera_cfg.get("frame_skip", 0))
        backoff = 1.0
        frame_i = 0

        try:
            while not self._stop.is_set():
                if cap is None or not cap.isOpened():
                    log.warning("zone %s: camera not open, retrying in %.0fs",
                                self.zone, backoff)
                    time.sleep(backoff)
                    backoff = min(backoff * 2, 10.0)
                    cap = self._open()
                    continue

                ok, frame = cap.read()
                if not ok or frame is None:
                    log.warning("zone %s: frame read failed, reopening", self.zone)
                    cap.release()
                    time.sleep(backoff)
                    backoff = min(backoff * 2, 10.0)
                    cap = self._open()
                    continue
                backoff = 1.0

                frame_i += 1
                if frame_skip and (frame_i % (frame_skip + 1) != 0):
                    continue

                ts_ms = time.monotonic() * 1000.0
                try:
                    is_victory, conf, hands = classifier.classify(frame, ts_ms)
                except Exception:
                    log.exception("zone %s: classify error", self.zone)
                    is_victory, conf, hands = False, 0.0, []

                self.emit(ZoneSignal(self.zone, is_victory, conf, time.monotonic(), hands))
        finally:
            if cap is not None:
                cap.release()
            classifier.close()
            log.info("zone %s: vision agent stopped", self.zone)
