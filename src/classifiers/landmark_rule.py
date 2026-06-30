"""Fallback classifier: geometric 'V' rule over MediaPipe hand landmarks.

Uses the MediaPipe Tasks HandLandmarker (model: hand_landmarker.task, fetched by
models.ensure_model). Gives full control over the exact definition of a victory
sign — useful if the built-in gesture mis-fires.
"""
from __future__ import annotations

import math

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

from ..types import HandResult

# Landmark indices
WRIST, THUMB_MCP, THUMB_TIP = 0, 2, 4
INDEX_PIP, INDEX_TIP = 6, 8
MIDDLE_MCP, MIDDLE_PIP, MIDDLE_TIP = 9, 10, 12
RING_PIP, RING_TIP = 14, 16
PINKY_PIP, PINKY_TIP = 18, 20


def _dist(a, b) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


class LandmarkRuleClassifier:
    def __init__(self, model_path: str, num_hands: int = 4,
                 min_score: float = 0.6, spread_min: float = 0.0,
                 require_thumb_tucked: bool = False, **_ignored):
        if not model_path:
            raise ValueError("landmark_rule requires a model_path (hand_landmarker.task)")
        options = vision.HandLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=model_path),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=num_hands,
            min_hand_detection_confidence=min_score,
        )
        self._landmarker = vision.HandLandmarker.create_from_options(options)
        self._spread_min = spread_min
        self._require_thumb_tucked = require_thumb_tucked
        self._last_ts = -1

    def classify(self, frame_bgr, ts_ms: float):
        ts = int(ts_ms)
        if ts <= self._last_ts:
            ts = self._last_ts + 1
        self._last_ts = ts

        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self._landmarker.detect_for_video(image, ts)

        if not result.hand_landmarks:
            return False, 0.0, []

        hands: list[HandResult] = []
        is_victory = False
        best_conf = 0.0

        for i, landmarks in enumerate(result.hand_landmarks):
            hand_is_victory = self._is_victory(landmarks)

            conf = 1.0
            handedness = "Unknown"
            if result.handedness and i < len(result.handedness) and result.handedness[i]:
                conf = result.handedness[i][0].score
                handedness = result.handedness[i][0].display_name

            hands.append(HandResult(
                handedness=handedness,
                is_victory=hand_is_victory,
                confidence=conf,
                landmarks=[(lm.x, lm.y) for lm in landmarks],
            ))

            if hand_is_victory:
                is_victory = True
                best_conf = max(best_conf, conf)

        return is_victory, (best_conf if is_victory else 0.0), hands

    def _is_victory(self, lm) -> bool:
        wrist = lm[WRIST]

        def extended(tip, pip):
            # Extended = fingertip is farther from the wrist than its PIP joint.
            return _dist(lm[tip], wrist) > _dist(lm[pip], wrist)

        index_ext = extended(INDEX_TIP, INDEX_PIP)
        middle_ext = extended(MIDDLE_TIP, MIDDLE_PIP)
        ring_ext = extended(RING_TIP, RING_PIP)
        pinky_ext = extended(PINKY_TIP, PINKY_PIP)

        victory = index_ext and middle_ext and not ring_ext and not pinky_ext
        if not victory:
            return False

        if self._spread_min > 0.0:
            scale = _dist(lm[WRIST], lm[MIDDLE_MCP]) or 1e-6
            spread = _dist(lm[INDEX_TIP], lm[MIDDLE_TIP]) / scale
            if spread < self._spread_min:
                return False

        if self._require_thumb_tucked:
            thumb_ext = _dist(lm[THUMB_TIP], wrist) > _dist(lm[THUMB_MCP], wrist)
            if thumb_ext:
                return False

        return True

    def close(self):
        self._landmarker.close()
