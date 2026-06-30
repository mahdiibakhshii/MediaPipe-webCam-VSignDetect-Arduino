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

# MediaPipe hand skeleton topology (pairs of the 21 landmark indices).
_HAND_CONNECTIONS = (
    (0, 1), (1, 2), (2, 3), (3, 4),          # thumb
    (0, 5), (5, 6), (6, 7), (7, 8),          # index
    (5, 9), (9, 10), (10, 11), (11, 12),     # middle
    (9, 13), (13, 14), (14, 15), (15, 16),   # ring
    (13, 17), (17, 18), (18, 19), (19, 20),  # pinky
    (0, 17),                                  # palm base
)

_GREEN = (0, 255, 0)
_GREY = (160, 160, 160)
_RED = (40, 40, 220)


def draw_overlay(frame, zone: str, hands, fps: float):
    """Draw a hand skeleton per detected hand (green if it's a V) plus a status
    banner. Returns the same frame, annotated in place."""
    h, w = frame.shape[:2]
    n_v = sum(1 for hd in hands if hd.is_victory)

    for hd in hands:
        if not hd.landmarks:
            continue
        color = _GREEN if hd.is_victory else _GREY
        pts = [(int(x * w), int(y * h)) for (x, y) in hd.landmarks]
        for a, b in _HAND_CONNECTIONS:
            if a < len(pts) and b < len(pts):
                cv2.line(frame, pts[a], pts[b], color, 2)
        for p in pts:
            cv2.circle(frame, p, 3, color, -1)
        # bounding box + label
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
        cv2.rectangle(frame, (x0 - 8, y0 - 8), (x1 + 8, y1 + 8),
                      color if hd.is_victory else _RED, 2)
        label = f"{hd.handedness} {'V' if hd.is_victory else '-'} {hd.confidence:.2f}"
        cv2.putText(frame, label, (x0 - 8, max(0, y0 - 14)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)

    banner = f"Zone {zone}  {fps:.0f}fps  hands:{len(hands)}  V:{n_v}"
    cv2.rectangle(frame, (0, 0), (w, 26), (0, 0, 0), -1)
    cv2.putText(frame, banner, (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                _GREEN if n_v else (220, 220, 220), 1, cv2.LINE_AA)
    return frame


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
                 model_path: str | None, emit: Callable[[ZoneSignal], None],
                 frame_store=None):
        super().__init__(daemon=True, name=f"vision-{zone}")
        self.zone = zone
        self.camera_cfg = camera_cfg
        self.detection_cfg = detection_cfg
        self.model_path = model_path
        self.emit = emit
        self.frame_store = frame_store   # optional: monitor video stream
        self._stop = threading.Event()
        self._last_encode = 0.0
        self._stream_interval = 1.0 / float(camera_cfg.get("stream_fps", 12) or 12)

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
        last_t = time.monotonic()
        fps = 0.0

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

                now = time.monotonic()
                dt = now - last_t
                last_t = now
                if dt > 0:
                    fps = 0.9 * fps + 0.1 * (1.0 / dt) if fps else 1.0 / dt

                ts_ms = now * 1000.0
                try:
                    is_victory, conf, hands = classifier.classify(frame, ts_ms)
                except Exception:
                    log.exception("zone %s: classify error", self.zone)
                    is_victory, conf, hands = False, 0.0, []

                self.emit(ZoneSignal(self.zone, is_victory, conf, time.monotonic(), hands))

                # Encode an annotated frame for the monitor video — only while a
                # browser is watching, throttled to stream_fps to spare CPU.
                if (self.frame_store is not None and self.frame_store.viewers > 0
                        and now - self._last_encode >= self._stream_interval):
                    self._last_encode = now
                    try:
                        annotated = draw_overlay(frame, self.zone, hands, fps)
                        ok2, buf = cv2.imencode(".jpg", annotated,
                                                [cv2.IMWRITE_JPEG_QUALITY, 70])
                        if ok2:
                            self.frame_store.put(self.zone, buf.tobytes())
                    except Exception:
                        log.exception("zone %s: overlay/encode error", self.zone)
        finally:
            if cap is not None:
                cap.release()
            classifier.close()
            log.info("zone %s: vision agent stopped", self.zone)
