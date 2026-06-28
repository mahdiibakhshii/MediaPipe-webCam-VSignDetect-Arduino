"""Load and lightly validate config.yaml. Code reads config; never hardcodes."""
from __future__ import annotations

import os
import sys

import yaml

REQUIRED_SECTIONS = ("cameras", "detection")


def load_config(path: str) -> dict:
    if not os.path.exists(path):
        sys.exit(
            f"Config not found: {path}\n"
            "Copy config/config.example.yaml to config/config.yaml and edit it."
        )
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    for section in REQUIRED_SECTIONS:
        if section not in cfg:
            sys.exit(f"Config missing required section: '{section}'")
    if not cfg.get("cameras"):
        sys.exit("Config: at least one entry under 'cameras' is required.")
    for i, cam in enumerate(cfg["cameras"]):
        for key in ("zone", "index"):
            if key not in cam:
                sys.exit(f"Config: cameras[{i}] missing required key '{key}'.")

    cfg.setdefault("app", {})
    cfg.setdefault("trigger", {})
    cfg.setdefault("outputs", [])
    return cfg
