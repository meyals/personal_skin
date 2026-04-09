"""Asynchronous audit/error logging using a dedicated worker thread."""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from queue import Empty, Queue
from threading import Event, Thread
from typing import Any

from flask import Flask

_queue: Queue[dict[str, Any]] = Queue()
_started = False
_stop_event = Event()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log_file_path() -> str:
    base = os.path.abspath(os.getcwd())
    logs_dir = os.path.join(base, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    return os.path.join(logs_dir, "audit.log")


def _build_logger() -> logging.Logger:
    logger = logging.getLogger("personal_skin.audit")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(_log_file_path(), maxBytes=2_000_000, backupCount=5, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def _worker(app: Flask) -> None:
    logger = _build_logger()
    with app.app_context():
        while not _stop_event.is_set():
            try:
                payload = _queue.get(timeout=0.5)
            except Empty:
                continue
            try:
                logger.info(json.dumps(payload, ensure_ascii=False))
            except Exception:
                app.logger.exception("Failed writing audit event")


def init_async_audit_logger(app: Flask) -> None:
    global _started
    if _started:
        return
    thread = Thread(target=_worker, args=(app,), daemon=True, name="audit-log-worker")
    thread.start()
    _started = True


def log_audit_event(event_type: str, level: str = "info", **data: Any) -> None:
    payload = {
        "timestamp": _utc_now(),
        "event_type": event_type,
        "level": level,
        **data,
    }
    _queue.put(payload)

