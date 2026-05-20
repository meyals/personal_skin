"""הגדרות אפליקציה לפי סביבה (פיתוח / ייצור).

טוען משתני סביבה מקובץ .env (אם קיים) באמצעות python-dotenv.
"""
import os

from dotenv import load_dotenv

load_dotenv()


def _database_uri() -> str:
    """בונה מחרוזת חיבור למסד הנתונים.

    - ללא DATABASE_URL → SQLite מקומי (קובץ personal_skin.db).
    - עם DATABASE_URL → PostgreSQL (למשל Render).
    - מתקן postgres:// ל-postgresql:// לתאימות ספקי ענן.
    """
    raw = (os.environ.get("DATABASE_URL") or "").strip()
    if not raw:
        return "sqlite:///personal_skin.db"
    if raw.startswith("postgres://"):
        return raw.replace("postgres://", "postgresql://", 1)
    return raw


class Config:
    """הגדרות בסיס משותפות לכל הסביבות."""

    # חותם סשן וטפסי CSRF — חובה לשנות בייצור אמיתי
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY") or "dev-only-change-in-production"
    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # חוסך התראות מיותרות
    WTF_CSRF_ENABLED = True  # הגנה מ-CSRF בכל טפסי Flask-WTF

    # כתובת שרת אימות TCP — Flask מתחבר לכאן ב-login/register
    AUTH_SOCKET_HOST = os.environ.get("AUTH_SOCKET_HOST", "127.0.0.1")
    AUTH_SOCKET_PORT = int(os.environ.get("AUTH_SOCKET_PORT", "5050"))


class DevelopmentConfig(Config):
    """סביבת פיתוח — debug פעיל."""

    DEBUG = True


class ProductionConfig(Config):
    """סביבת ייצור — ללא debug."""

    DEBUG = False


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
