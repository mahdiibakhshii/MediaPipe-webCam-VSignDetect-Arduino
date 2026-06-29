"""Default classifier: MediaPipe Gesture Recognizer with built-in 'Victory' class."""
from __future__ import annotations

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision


class GestureRecognizerClassifier:
    def __init__(self, model_path: str, num_hands: int = 4,
                 min_score: float = 0.6, **_ignored):
        if not model_path:
            raise ValueError("gesture_recognizer requires a model_path")
        options = vision.GestureRecognizerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=model_path),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=num_hands,
        )
        self._recognizer = vision.GestureRecognizer.create_from_options(options)
        self._min_score = min_score
        self._last_ts = -1

    def classify(self, frame_bgr, ts_ms: float):
        # MediaPipe VIDEO mode needs strictly increasing integer timestamps.
        ts = int(ts_ms)
        if ts <= self._last_ts:
            ts = self._last_ts + 1
        self._last_ts = ts

        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self._recognizer.recognize_for_video(image, ts)

        is_victory = False
        victory_score = 0.0
        for hand_gestures in result.gestures:  # one list per detected hand
            if not hand_gestures:
                continue
            top = hand_gestures[0]
            if top.category_name == "Victory":
                victory_score = max(victory_score, top.score)
                if top.score >= self._min_score:
                    is_victory = True
        return is_victory, victory_score

    def close(self):
        self._recognizer.close()
