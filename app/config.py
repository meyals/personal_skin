"""
=============================================================================
קובץ: config.py
שייך ל: צד שרת (Server-Side)
=============================================================================
תפקיד הקובץ:
    קובץ ההגדרות של האפליקציה. הוא מגדיר את כל הפרמטרים שהאפליקציה צריכה
    לדעת כדי לעבוד: איפה מסד הנתונים, מה מפתח ההצפנה, באיזה פורט שרת
    האימות מאזין, וכו'.

    הקובץ תומך בשתי סביבות:
    - Development (פיתוח): מצב debug פעיל, SQLite מקומי
    - Production (ייצור): מצב debug כבוי, PostgreSQL בענן (Render)

    משתני סביבה (Environment Variables):
    הקובץ משתמש בקובץ .env (אם קיים) כדי לטעון הגדרות רגישות
    כמו מפתח סודי או כתובת מסד נתונים. זה מאפשר לשמור סודות
    מחוץ לקוד עצמו (אבטחה).

מבנה:
    _database_uri()      → פונקציית עזר שבונה את כתובת ה-DB
    Config               → מחלקת בסיס עם הגדרות משותפות
    DevelopmentConfig     → הגדרות לפיתוח (יורשת מ-Config)
    ProductionConfig      → הגדרות לייצור (יורשת מ-Config)
    config_by_name        → מילון שממפה שם סביבה למחלקת הגדרות
=============================================================================
"""
import os

from dotenv import load_dotenv

# ─── טעינת משתני סביבה מקובץ .env ──────────────────────────────────────────
# python-dotenv קורא קובץ .env (אם קיים) ושם את התוכן שלו כמשתני סביבה.
# לדוגמה, אם בקובץ כתוב DATABASE_URL=postgres://... אז
# os.environ.get("DATABASE_URL") יחזיר את הערך הזה.
load_dotenv()


def _database_uri() -> str:
    """בונה את מחרוזת החיבור (Connection String) למסד הנתונים.

    מחרוזת החיבור אומרת ל-SQLAlchemy איפה נמצא מסד הנתונים ואיך להתחבר אליו.

    לוגיקה:
    - אם אין משתנה סביבה DATABASE_URL → משתמשים ב-SQLite מקומי (קובץ על הדיסק).
      SQLite הוא מסד נתונים פשוט שלא דורש שרת נפרד — מושלם לפיתוח.
    - אם יש DATABASE_URL → משתמשים ב-PostgreSQL (מסד נתונים אמיתי בענן).
    - תיקון: ספקי ענן (כמו Render) נותנים כתובת שמתחילה ב-postgres://
      אבל SQLAlchemy דורש postgresql:// — אז מחליפים את הקידומת.

    Returns:
        מחרוזת חיבור למסד נתונים, למשל:
        - "sqlite:///personal_skin.db" (פיתוח)
        - "postgresql://user:pass@host/dbname" (ייצור)
    """
    raw = (os.environ.get("DATABASE_URL") or "").strip()
    if not raw:
        return "sqlite:///personal_skin.db"
    if raw.startswith("postgres://"):
        return raw.replace("postgres://", "postgresql://", 1)
    return raw


class Config:
    """מחלקת בסיס — הגדרות משותפות לכל הסביבות (פיתוח וייצור).

    כל הגדרה כאן היא משתנה מחלקה (class variable) ש-Flask קורא אוטומטית
    כשקוראים ל-app.config.from_object(Config).
    """

    # ─── מפתח סודי (Secret Key) ──────────────────────────────────────────────
    # משמש להצפנת עוגיות הסשן ולהגנה מ-CSRF (Cross-Site Request Forgery).
    # בפיתוח אפשר להשתמש בערך קבוע, אבל בייצור חובה לשנות לערך אקראי וסודי!
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY") or "dev-only-change-in-production"

    # ─── כתובת מסד הנתונים ───────────────────────────────────────────────────
    # SQLAlchemy משתמש בכתובת הזו כדי לדעת לאן להתחבר
    SQLALCHEMY_DATABASE_URI = _database_uri()

    # ─── ביטול מעקב אחר שינויים ──────────────────────────────────────────────
    # Flask-SQLAlchemy יכול לעקוב אחרי שינויים באובייקטים — אבל זה צורך זיכרון
    # ולא נחוץ כשמשתמשים ב-db.session.commit() ידנית
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ─── הגנת CSRF ───────────────────────────────────────────────────────────
    # CSRF = Cross-Site Request Forgery (זיוף בקשות בין אתרים)
    # כשמופעל, כל טופס HTML חייב לכלול אסימון (token) מוצפן ייחודי.
    # בלי האסימון, השרת ידחה את הבקשה. זה מונע מאתר זדוני לשלוח
    # טפסים בשם המשתמש.
    WTF_CSRF_ENABLED = True

    # ─── הגדרות שרת אימות TCP ────────────────────────────────────────────────
    # הפרויקט כולל שרת אימות נפרד שרץ על פרוטוקול TCP (לא HTTP).
    # Flask (צד הלקוח) מתחבר לשרת הזה כשמשתמש מנסה להתחבר או להירשם.
    AUTH_SOCKET_HOST = os.environ.get("AUTH_SOCKET_HOST", "127.0.0.1")  # כתובת IP של השרת
    AUTH_SOCKET_PORT = int(os.environ.get("AUTH_SOCKET_PORT", "5050"))  # פורט השרת


class DevelopmentConfig(Config):
    """הגדרות לסביבת פיתוח — מצב debug פעיל.

    מצב debug מאפשר:
    - הודעות שגיאה מפורטות בדפדפן
    - טעינה מחדש אוטומטית כשמשנים קוד
    - לא מיועד לשימוש בייצור (חושף מידע רגיש)
    """
    DEBUG = True


class ProductionConfig(Config):
    """הגדרות לסביבת ייצור (Render / שרת ענן) — מצב debug כבוי.

    SQLALCHEMY_ENGINE_OPTIONS — הגדרות לניהול חיבורים למסד הנתונים:
    - pool_pre_ping: בודק אם החיבור עדיין חי לפני שימוש (מונע שגיאות SSL)
    - pool_recycle: מחליף חיבורים כל 5 דקות (300 שניות) כדי למנוע ניתוקים
    - pool_size: כמה חיבורים לשמור פתוחים (5)
    - max_overflow: כמה חיבורים נוספים מותר ליצור בעומס (10)
    """
    DEBUG = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_size": 5,
        "max_overflow": 10,
    }


# ─── מילון שממפה שם סביבה למחלקת ההגדרות המתאימה ────────────────────────────
# בעת יצירת האפליקציה, create_app מקבל שם סביבה (כמו "production")
# ומשתמש במילון הזה כדי לטעון את ההגדרות הנכונות.
config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
