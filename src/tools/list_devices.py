"""List cameras and serial ports to help fill in config.yaml.

    python -m src.tools.list_devices

Cross-platform: uses the right camera backend per OS and lists serial ports.
"""
from __future__ import annotations

import platform
import sys

import cv2
from serial.tools import list_ports

try:  # keep box-drawing/bullets readable on the Windows console
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass


def list_cameras(max_index: int = 6):
    is_win = platform.system() == "Windows"
    found = []
    for i in range(max_index):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW) if is_win else cv2.VideoCapture(i)
        if cap.isOpened():
            ok, frame = cap.read()
            res = None if frame is None else (frame.shape[1], frame.shape[0])
            found.append((i, ok, res))
        cap.release()
    return found


def list_serial():
    return [(p.device, (p.description or "").strip()) for p in list_ports.comports()]


def main():
    print("=" * 56)
    print(" VSign Detect — devices on this machine")
    print("=" * 56)

    print("\nCAMERAS  (index : opens : resolution)")
    cams = list_cameras()
    if not cams:
        print("  (none found)")
    for i, ok, res in cams:
        print(f"  {i} : {'ok' if ok else 'no-frame'} : {res}")

    print("\nSERIAL PORTS")
    ports = list_serial()
    if not ports:
        print("  (none found)")
    for dev, desc in ports:
        print(f"  {dev}   {('- ' + desc) if desc else ''}")

    print("\nNext:")
    print("  • Put camera indices into config.yaml  -> cameras[].index")
    print("  • Put the Arduino port into config.yaml -> serial.port")
    if platform.system() != "Windows":
        print("    (on macOS the Arduino is usually /dev/cu.usbserial-… or /dev/cu.usbmodem…)")
    print()


if __name__ == "__main__":
    main()
