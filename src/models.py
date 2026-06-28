"""Download MediaPipe Tasks model files on first use (cached in models/)."""
from __future__ import annotations

import logging
import os
import urllib.request

log = logging.getLogger(__name__)

_MODELS = {
    "gesture_recognizer": (
        "https://storage.googleapis.com/mediapipe-models/gesture_recognizer/"
        "gesture_recognizer/float16/1/gesture_recognizer.task",
        "gesture_recognizer.task",
    ),
    "hand_landmarker": (
        "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
        "hand_landmarker/float16/1/hand_landmarker.task",
        "hand_landmarker.task",
    ),
}


def model_for_classifier(classifier_name: str) -> str:
    """Map a classifier name to the model key it needs."""
    if classifier_name == "landmark_rule":
        return "hand_landmarker"
    return "gesture_recognizer"


def ensure_model(name: str, models_dir: str = "models") -> str:
    """Return a local path to the model, downloading it once if missing."""
    if name not in _MODELS:
        raise ValueError(f"Unknown model '{name}'")
    url, filename = _MODELS[name]
    os.makedirs(models_dir, exist_ok=True)
    path = os.path.join(models_dir, filename)
    if not os.path.exists(path):
        log.info("Downloading model %s -> %s", url, path)
        urllib.request.urlretrieve(url, path)
        log.info("Model ready: %s", path)
    return path
