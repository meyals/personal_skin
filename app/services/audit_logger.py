"""
=============================================================================
קובץ: services/audit_logger.py
שייך ל: צד שרת (Server-Side)
=============================================================================
תפקיד הקובץ:
    מערכת תיעוד אירועים (Audit Log) אסינכרונית.
    כל אירוע חשוב במערכת נרשם לקובץ logs/audit.log:
    - התחברות/הרשמה הצליחה/נכשלה
    - שליחת שאלון
    - פרסום שיתוף בקהילה
    - שגיאות בלתי צפויות

    למה Audit Log?
    - ניטור אבטחה: לראות ניסיונות כניסה כושלים (אולי מישהו מנסה לפרוץ)
    - דיבוג: לחקור בעיות בייצור
    - תיעוד: לדעת מה קרה ומתי

    למה אסינכרוני?
    - כתיבה לקובץ = פעולה "איטית" (disk I/O)
    - אם כותבים בזמן בקשת HTTP, המשתמש חווה עיכוב
    - הפתרון: שומרים את האירוע בתור (Queue) וthread ברקע כותב אותו
    - ככה הבקשה חוזרת מיד למשתמש, והכתיבה מתבצעת ברקע

ארכיטקטורה:
    [Route] → log_audit_event() → [Queue] → [Worker Thread] → [audit.log]

    log_audit_event = דוחף אירוע לתור (מיידי, לא חוסם)
    _worker = thread ברקע שקורא מהתור וכותב לקובץ
    RotatingFileHandler = כשהקובץ מגיע ל-2MB, יוצר קובץ חדש (עד 5 קבצים)
=============================================================================
"""
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

# ─── משתנים גלובליים ─────────────────────────────────────────────────────────
# Queue = תור thread-safe — מאפשר לshov ולקרוא מthreads שונים בבטחה
_queue: Queue[dict[str, Any]] = Queue()
_started = False        # דגל שמונע הפעלה כפולה
_stop_event = Event()   # Event לעצירת ה-worker


def _utc_now() -> str:
    """מחזיר חותמת זמן UTC בפורמט ISO-8601.
    למשל: "2025-05-22T14:30:00+00:00"
    """
    return datetime.now(timezone.utc).isoformat()


def _log_file_path() -> str:
    """מחזיר את הנתיב המלא לקובץ audit.log.
    יוצר את תיקיית logs/ אם לא קיימת.
    """
    base = os.path.abspath(os.getcwd())
    logs_dir = os.path.join(base, "logs")
    os.makedirs(logs_dir, exist_ok=True)  # exist_ok = לא זורק שגיאה אם כבר קיים
    return os.path.join(logs_dir, "audit.log")


def _build_logger() -> logging.Logger:
    """יוצר או מחזיר logger ייעודי עם סבב קבצים (RotatingFileHandler).

    RotatingFileHandler:
    - maxBytes=2_000_000 → כשהקובץ מגיע ל-2MB, עובר לקובץ חדש
    - backupCount=5 → שומר עד 5 קבצים ישנים (audit.log.1, audit.log.2, ...)
    - encoding="utf-8" → תמיכה בעברית
    """
    logger = logging.getLogger("personal_skin.audit")
    if logger.handlers:  # כבר מוגדר — לא יוצרים שוב
        return logger
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(_log_file_path(), maxBytes=2_000_000, backupCount=5, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))  # רק ההודעה, בלי תוספות
    logger.addHandler(handler)
    logger.propagate = False  # לא מעביר ל-root logger (מונע כפילויות)
    return logger


def _worker(app: Flask) -> None:
    """לולאת ה-Worker — רצה ב-thread ברקע וכותבת אירועים לקובץ.

    הלולאה:
    1. מחכה לאירוע חדש בתור (timeout 0.5 שניות)
    2. אם יש אירוע — כותבת אותו כ-JSON לקובץ
    3. אם התור ריק — חוזרת לחכות
    4. נעצרת כש-_stop_event מופעל (בסגירת האפליקציה)

    app.app_context() — נדרש כי ה-thread רץ מחוץ ל-request של Flask
    """
    logger = _build_logger()
    with app.app_context():
        while not _stop_event.is_set():
            try:
                payload = _queue.get(timeout=0.5)  # מחכה עד 0.5 שניות
            except Empty:
                continue  # התור ריק — ממשיכים לחכות
            try:
                # כותבים את האירוע כ-JSON בשורה אחת
                logger.info(json.dumps(payload, ensure_ascii=False))
            except Exception:
                app.logger.exception("Failed writing audit event")


def init_async_audit_logger(app: Flask) -> None:
    """מפעיל את ה-Worker Thread לכתיבת audit events ברקע.

    נקרא פעם אחת מ-create_app() באתחול האפליקציה.
    daemon=True → ה-thread נסגר אוטומטית כשהתהליך הראשי נסגר.
    """
    global _started
    if _started:  # מניעת הפעלה כפולה
        return
    thread = Thread(target=_worker, args=(app,), daemon=True, name="audit-log-worker")
    thread.start()
    _started = True


def log_audit_event(event_type: str, level: str = "info", **data: Any) -> None:
    """דוחף אירוע חדש לתור הכתיבה — הפונקציה הראשית שכל הקוד משתמש בה.

    הפונקציה לא כותבת לקובץ ישירות — היא רק שמה את האירוע בתור.
    ה-Worker Thread כותב לקובץ ברקע.

    Args:
        event_type: מזהה אירוע, למשל "auth.login_success" או "app.exception"
        level: רמת חומרה — "info" / "warning" / "error"
        **data: נתונים נוספים — user_id, email, reason, share_id וכו'

    דוגמאות:
        log_audit_event("auth.login_success", user_id="abc", email="a@b.com")
        log_audit_event("auth.login_failed", level="warning", email="x@y.com", reason="wrong_password")
    """
    payload = {
        "timestamp": _utc_now(),
        "event_type": event_type,
        "level": level,
        **data,  # מוסיף את כל הנתונים הנוספים למילון
    }
    _queue.put(payload)
