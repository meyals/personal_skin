"""הגדרות אפליקציה לפי סביבה."""
import os

from dotenv import load_dotenv

load_dotenv()


def _database_uri() -> str:
    """Build SQLAlchemy DB URI with Render/Postgres compatibility."""
    raw = (os.environ.get("DATABASE_URL") or "").strip()
    if not raw:
        return "sqlite:///personal_skin.db"
    if raw.startswith("postgres://"):
        # Backward-compatible alias sometimes used by hosted providers.
        return raw.replace("postgres://", "postgresql://", 1)
    return raw


class Config:
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY") or "dev-only-change-in-production"
    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    # שרת אימות TCP (לקוח Flask מתחבר לכאן)
    AUTH_SOCKET_HOST = os.environ.get("AUTH_SOCKET_HOST", "127.0.0.1")
    AUTH_SOCKET_PORT = int(os.environ.get("AUTH_SOCKET_PORT", "5050"))


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
