"""Shared logging setup (used by the orchestrator and the web bridge)."""
from __future__ import annotations

import logging
import os
import sys


def setup_logging(cfg: dict):
    app = cfg.get("app", {})
    level = getattr(logging, str(app.get("log_level", "INFO")).upper(), logging.INFO)
    # Make stdout UTF-8 so non-ASCII log chars don't break the Windows console.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    handlers = [logging.StreamHandler(sys.stdout)]
    log_file = app.get("log_file")
    if log_file:
        from logging.handlers import RotatingFileHandler

        d = os.path.dirname(log_file)
        if d:
            os.makedirs(d, exist_ok=True)
        handlers.append(RotatingFileHandler(
            log_file, maxBytes=2_000_000, backupCount=3, encoding="utf-8"))
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )
