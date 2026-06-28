"""Preview one zone's detection locally (dev only).

    python -m src.tools.vision_test --config config/config.yaml --zone A --preview

Shows a window with the live VICTORY/.. label + confidence. Press 'q' to quit.
Without --preview, prints the label to the console.
"""
from __future__ import annotations

import argparse
import time

import cv2

from ..classifiers import make_classifier
from ..config import load_config
from ..models import ensure_model, model_for_classifier
from ..vision_agent import open_capture


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/config.yaml")
    ap.add_argument("--zone", default=None, help="zone label; defaults to first camera")
    ap.add_argument("--preview", action="store_true", help="show a video window")
    args = ap.parse_args()

    cfg = load_config(args.config)
    cams = cfg["cameras"]
    cam = next((c for c in cams if c["zone"] == args.zone), None) if args.zone else None
    if cam is None:
        cam = cams[0]

    detection = cfg["detection"]
    classifier_name = detection.get("classifier", "gesture_recognizer")
    model_path = ensure_model(model_for_classifier(classifier_name))
    classifier = make_classifier(detection, model_path)

    cap = open_capture(cam["index"], cam.get("width", 640),
                       cam.get("height", 480), cam.get("fps", 30))
    print(f"zone={cam['zone']} index={cam['index']} "
          f"classifier={detection.get('classifier', 'gesture_recognizer')} — q to quit")

    try:
        while True:
            ok, frame = cap.read()
            if not ok or frame is None:
                print("frame read failed"); break
            is_victory, conf = classifier.classify(frame, time.monotonic() * 1000.0)
            label = (f"{cam['zone']}  VICTORY  {conf:.2f}" if is_victory
                     else f"{cam['zone']}  ...      {conf:.2f}")
            if args.preview:
                color = (0, 220, 0) if is_victory else (0, 0, 230)
                cv2.putText(frame, label, (12, 36), cv2.FONT_HERSHEY_SIMPLEX,
                            1.0, color, 2, cv2.LINE_AA)
                cv2.imshow("vision_test", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
            else:
                print("  " + label, end="\r", flush=True)
    finally:
        cap.release()
        classifier.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
