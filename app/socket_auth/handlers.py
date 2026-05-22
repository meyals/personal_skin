"""
=============================================================================
קובץ: socket_auth/handlers.py
שייך ל: צד שרת (Server-Side) — שרת אימות TCP
=============================================================================
תפקיד הקובץ:
    הלוגיקה העסקית (Business Logic) של שרת האימות.
    הקובץ מקבל בקשות JSON מהלקוח (דרך server.py) ומבצע פעולות
    מול מסד הנתונים באמצעות SQLAlchemy ORM.

    פעולות נתמכות (לפי שדה "action" ב-JSON):
    - ping           → בדיקת חיים (healthcheck) — מחזיר "pong"
    - login          → בדיקת אימייל + סיסמה מול ה-DB
    - register       → יצירת משתמש חדש (אם האימייל לא קיים)
    - reset_password → שינוי סיסמה למשתמש קיים

    כל פעולה:
    1. מקבלת מילון JSON כקלט
    2. מבצעת ולידציה (שדות חובה, חוזק סיסמה)
    3. פונה ל-DB דרך ORM (שאילתות/עדכונים)
    4. רושמת את האירוע ב-audit log
    5. מחזירה מילון JSON כתשובה

    פורמט תשובה:
    - הצלחה: {"ok": true, "user": {"user_id": "...", "email": "..."}}
    - כישלון: {"ok": false, "error": "error_code", "message": "הודעה בעברית"}

    אבטחה:
    - סיסמאות נשמרות כ-hash (הצפנה חד-כיוונית) — לא ניתן לשחזר
    - בדיקת חוזק סיסמה (8 תווים, אות, ספרה, תו מיוחד)
    - _user_payload מחזיר רק נתונים בטוחים (בלי סיסמה!)
=============================================================================
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.auth.validation import password_strength_error
from app.extensions import db
from app.models import User
from app.services.audit_logger import log_audit_event


def _user_payload(user: User) -> dict[str, Any]:
    """בונה מילון עם נתוני משתמש בטוחים לשליחה ללקוח.

    חשוב: לא כולל את password_hash! רק מידע שבטוח לחשוף.

    Args:
        user: אובייקט User מה-DB

    Returns:
        מילון עם user_id, email, first_name, last_name
    """
    return {
        "user_id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
    }


def handle_auth_request(request: dict[str, Any]) -> dict[str, Any]:
    """פונקציית ניתוב ראשית — מנתבת כל בקשה לפונקציה המתאימה.

    מקבלת את ה-action מהבקשה ומפנה לפונקציה הנכונה.
    אם ה-action לא מוכר — מחזירה שגיאה.

    Args:
        request: מילון JSON שהתקבל מהלקוח, למשל:
                 {"action": "login", "email": "...", "password": "..."}

    Returns:
        מילון תשובה — {"ok": true/false, ...}
    """
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
    """טיפול בבקשת התחברות (login).

    שלבים:
    1. חילוץ אימייל וסיסמה מהבקשה
    2. חיפוש המשתמש ב-DB לפי אימייל
    3. בדיקת הסיסמה מול ה-hash שנשמר (check_password)
    4. עדכון last_login בהצלחה
    5. רישום ב-audit log

    Args:
        request: {"action": "login", "email": "...", "password": "..."}

    Returns:
        הצלחה: {"ok": true, "user": {...}}
        כישלון: {"ok": false, "error": "invalid_credentials", "message": "..."}
    """
    email = (request.get("email") or "").strip().lower()
    password = request.get("password") or ""

    if not email or not password:
        return {"ok": False, "error": "missing_fields", "message": "חסרים אימייל או סיסמה"}

    # חיפוש משתמש ב-DB לפי אימייל
    user = User.query.filter_by(email=email).first()

    # בדיקה: המשתמש לא קיים, או הסיסמה לא תואמת
    if user is None or not user.check_password(password):
        log_audit_event(
            "auth.socket.login_failed",
            level="warning",
            email=email,
            reason="invalid_credentials",
        )
        return {"ok": False, "error": "invalid_credentials", "message": "אימייל או סיסמה שגויים"}

    # התחברות הצליחה — עדכון זמן התחברות אחרון
    user.last_login = datetime.now(timezone.utc)
    db.session.commit()

    log_audit_event("auth.socket.login_success", user_id=user.id, email=user.email)
    return {"ok": True, "user": _user_payload(user)}


def _handle_register(request: dict[str, Any]) -> dict[str, Any]:
    """טיפול בבקשת הרשמה (register).

    שלבים:
    1. חילוץ נתונים מהבקשה (אימייל, סיסמה, שם)
    2. בדיקת חוזק סיסמה
    3. בדיקה שהאימייל לא קיים כבר ב-DB
    4. יצירת אובייקט User חדש עם סיסמה מוצפנת (hash)
    5. שמירה ב-DB
    6. רישום ב-audit log

    Args:
        request: {"action": "register", "email": "...", "password": "...", ...}

    Returns:
        הצלחה: {"ok": true, "user": {...}}
        כישלון: {"ok": false, "error": "email_exists"/"weak_password", "message": "..."}
    """
    email = (request.get("email") or "").strip().lower()
    password = request.get("password") or ""
    first_name = (request.get("first_name") or "").strip() or None
    last_name = (request.get("last_name") or "").strip() or None

    if not email or not password:
        return {"ok": False, "error": "missing_fields", "message": "חסרים אימייל או סיסמה"}

    # בדיקת חוזק סיסמה
    pwd_error = password_strength_error(password)
    if pwd_error:
        return {"ok": False, "error": "weak_password", "message": pwd_error}

    # בדיקה שהאימייל לא תפוס
    if User.query.filter_by(email=email).first():
        log_audit_event(
            "auth.socket.register_failed",
            level="warning",
            email=email,
            reason="email_exists",
        )
        return {"ok": False, "error": "email_exists", "message": "כתובת האימייל כבר רשומה במערכת"}

    # יצירת משתמש חדש
    user = User(email=email, first_name=first_name, last_name=last_name)
    user.set_password(password)  # שומר hash של הסיסמה, לא את הסיסמה עצמה!
    db.session.add(user)
    db.session.commit()

    log_audit_event("auth.socket.register_success", user_id=user.id, email=user.email)
    return {"ok": True, "user": _user_payload(user)}


def _handle_reset_password(request: dict[str, Any]) -> dict[str, Any]:
    """טיפול בבקשת איפוס סיסמה (reset_password).

    גרסת דמו — ללא אימות באימייל (בפרויקט אמיתי שולחים קישור חד-פעמי).

    שלבים:
    1. חילוץ אימייל וסיסמה חדשה
    2. בדיקת חוזק הסיסמה החדשה
    3. חיפוש המשתמש ב-DB
    4. עדכון ה-hash לסיסמה החדשה
    5. שמירה ב-DB

    Args:
        request: {"action": "reset_password", "email": "...", "password": "..."}
    """
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

    # עדכון הסיסמה — שומר hash חדש
    user.set_password(password)
    db.session.commit()

    log_audit_event("auth.socket.password_reset_success", user_id=user.id, email=user.email)
    return {"ok": True, "user": _user_payload(user)}
