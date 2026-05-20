"""לוגיקת אימות על שרת הסוקטים — גישה ישירה למסד הנתונים (ORM).

פעולות נתמכות (שדה action ב-JSON):
- ping: בדיקת חיים
- login: אימייל + סיסמה
- register: הרשמה + hash סיסמה
- reset_password: איפוס סיסמה לפי אימייל
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.auth.validation import password_strength_error
from app.extensions import db
from app.models import User
from app.services.audit_logger import log_audit_event


def _user_payload(user: User) -> dict[str, Any]:
    """מחזיר נתוני משתמש בטוחים לתשובה (בלי סיסמה)."""
    return {
        "user_id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
    }


def handle_auth_request(request: dict[str, Any]) -> dict[str, Any]:
    """מנתב בקשת JSON לפונקציה המתאימה לפי action."""
    action = (request.get("action") or "").strip().lower()
    if action == "ping":
        return {"ok": True, "message": "pong"}

    if action == "login":
        return _handle_login(request)
    if action == "register":
        return _handle_register(request)
    if action == "reset_password":
        return _handle_reset_password(request)

    return {"ok": False, "error": "unknown_action", "message": f"פעולה לא נתמכת: {action}"}


def _handle_login(request: dict[str, Any]) -> dict[str, Any]:
    """בודק אימייל וסיסמה מול DB; מעדכן last_login בהצלחה."""
    email = (request.get("email") or "").strip().lower()
    password = request.get("password") or ""
    if not email or not password:
        return {"ok": False, "error": "missing_fields", "message": "חסרים אימייל או סיסמה"}

    user = User.query.filter_by(email=email).first()
    if user is None or not user.check_password(password):
        log_audit_event(
            "auth.socket.login_failed",
            level="warning",
            email=email,
            reason="invalid_credentials",
        )
        return {"ok": False, "error": "invalid_credentials", "message": "אימייל או סיסמה שגויים"}

    user.last_login = datetime.now(timezone.utc)
    db.session.commit()
    log_audit_event("auth.socket.login_success", user_id=user.id, email=user.email)
    return {"ok": True, "user": _user_payload(user)}


def _handle_register(request: dict[str, Any]) -> dict[str, Any]:
    """יוצר משתמש חדש — סיסמה נשמרת כ-hash."""
    email = (request.get("email") or "").strip().lower()
    password = request.get("password") or ""
    first_name = (request.get("first_name") or "").strip() or None
    last_name = (request.get("last_name") or "").strip() or None

    if not email or not password:
        return {"ok": False, "error": "missing_fields", "message": "חסרים אימייל או סיסמה"}

    pwd_error = password_strength_error(password)
    if pwd_error:
        return {"ok": False, "error": "weak_password", "message": pwd_error}

    if User.query.filter_by(email=email).first():
        log_audit_event(
            "auth.socket.register_failed",
            level="warning",
            email=email,
            reason="email_exists",
        )
        return {"ok": False, "error": "email_exists", "message": "כתובת האימייל כבר רשומה במערכת"}

    user = User(email=email, first_name=first_name, last_name=last_name)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    log_audit_event("auth.socket.register_success", user_id=user.id, email=user.email)
    return {"ok": True, "user": _user_payload(user)}


def _handle_reset_password(request: dict[str, Any]) -> dict[str, Any]:
    """מאפס סיסמה למשתמש קיים (דמו — ללא אימות במייל)."""
    email = (request.get("email") or "").strip().lower()
    password = request.get("password") or ""

    if not email or not password:
        return {"ok": False, "error": "missing_fields", "message": "חסרים אימייל או סיסמה"}

    pwd_error = password_strength_error(password)
    if pwd_error:
        return {"ok": False, "error": "weak_password", "message": pwd_error}

    user = User.query.filter_by(email=email).first()
    if user is None:
        log_audit_event(
            "auth.socket.password_reset_failed",
            level="warning",
            email=email,
            reason="email_not_found",
        )
        return {"ok": False, "error": "email_not_found", "message": "לא נמצא משתמש עם האימייל הזה"}

    user.set_password(password)
    db.session.commit()
    log_audit_event("auth.socket.password_reset_success", user_id=user.id, email=user.email)
    return {"ok": True, "user": _user_payload(user)}
