"""Pluggable victory-sign classifiers. Each: frame_bgr, ts_ms -> (is_victory, confidence)."""
from __future__ import annotations


def make_classifier(detection_cfg: dict, model_path: str | None):
    """Build the classifier named in detection_cfg['classifier']."""
    name = detection_cfg.get("classifier", "gesture_recognizer")
    if name == "gesture_recognizer":
        from .gesture_recognizer import GestureRecognizerClassifier

        return GestureRecognizerClassifier(model_path=model_path, **detection_cfg)
    if name == "landmark_rule":
        from .landmark_rule import LandmarkRuleClassifier

        return LandmarkRuleClassifier(model_path=model_path, **detection_cfg)
    raise ValueError(f"Unknown classifier: {name!r}")
