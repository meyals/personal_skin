"""
=============================================================================
קובץ: app/__init__.py
שייך ל: צד שרת (Server-Side)
=============================================================================
תפקיד הקובץ:
    זהו "הלב" של האפליקציה — כאן נוצרת אפליקציית Flask.
    הקובץ מממש את תבנית "App Factory" (מפעל אפליקציות):
    במקום ליצור את האפליקציה ברמה הגלובלית, יש פונקציה create_app()
    שמקבלת שם סביבה (development/production) ומחזירה אפליקציה מוכנה.

    למה App Factory?
    - מאפשר יצירת מספר אפליקציות עם הגדרות שונות (לבדיקות, לייצור...)
    - מונע בעיות ייבוא מעגלי (circular imports)
    - זו הפרקטיקה המומלצת ב-Flask

שלבי אתחול של create_app():
    1. יצירת אובייקט Flask
    2. טעינת הגדרות מ-config.py (לפי סביבה)
    3. הפעלת מערכת audit log ברקע (תיעוד אירועים)
    4. חיבור SQLAlchemy (DB) ו-Flask-Login (ניהול סשנים)
    5. הגדרת פילטר Jinja2 (markdown_safe — להמרת Markdown ל-HTML)
    6. הגדרת user_loader (טעינת משתמש מה-DB בכל בקשה)
    7. רישום Blueprints (מודולים: auth, questionnaire, community)
    8. הגדרת טיפול בשגיאות (שמירה ב-audit log)
    9. הגדרת דף הבית (route /)
    10. יצירת טבלאות במסד הנתונים (db.create_all)
=============================================================================
"""
import os

from flask import Flask
from flask.signals import got_request_exception

from app.config import config_by_name
from app.extensions import db, login_manager
from app.models import User
from app.services.audit_logger import init_async_audit_logger, log_audit_event


def create_app(config_name: str | None = None) -> Flask:
    """פונקציית המפעל — בונה ומאתחלת את אפליקציית Flask.

    Args:
        config_name: שם הסביבה ("development" או "production").
                     אם לא צוין, קורא ממשתנה הסביבה FLASK_CONFIG.
                     ברירת מחדל: "development".

    Returns:
        אובייקט Flask מוכן לשימוש, עם כל ה-blueprints, DB, וניהול סשנים.
    """

    # ─── שלב 1: יצירת אובייקט Flask ──────────────────────────────────────────
    # __name__ = שם המודול הנוכחי (app) — Flask משתמש בזה כדי למצוא קבצים
    # template_folder = איפה נמצאים קבצי HTML (תבניות Jinja2)
    # static_folder = איפה נמצאים קבצי CSS, תמונות וכו'
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )

    # ─── שלב 2: טעינת הגדרות ─────────────────────────────────────────────────
    # config_by_name = מילון שממפה שם סביבה למחלקת Config
    # from_object = Flask קורא את כל המשתנים מהמחלקה ושומר אותם ב-app.config
    cfg = config_name or os.getenv("FLASK_CONFIG", "development")
    app.config.from_object(config_by_name.get(cfg, config_by_name["development"]))

    # ─── שלב 3: הפעלת audit logger ──────────────────────────────────────────
    # מפעיל thread ברקע שכותב אירועים לקובץ logs/audit.log
    # "אסינכרוני" = לא חוסם את בקשות ה-HTTP (הכתיבה מתבצעת ברקע)
    init_async_audit_logger(app)

    # ─── שלב 4: חיבור DB ו-Login Manager ────────────────────────────────────
    # init_app = מחבר את האובייקט שנוצר ב-extensions.py לאפליקציה הספציפית
    db.init_app(app)
    login_manager.init_app(app)

    # ─── שלב 5: פילטר Jinja2 ────────────────────────────────────────────────
    # Jinja2 = מנוע תבניות HTML של Flask
    # פילטר = פונקציה שאפשר לקרוא לה מתוך HTML עם סימן | (pipe)
    # בתבניות: {{ routine.morning_text | markdown_safe }}
    # זה ממיר טקסט Markdown ל-HTML בטוח (מסנן תגיות מסוכנות)
    from app.utils import render_markdown_safe
    app.jinja_env.filters["markdown_safe"] = render_markdown_safe

    # ─── שלב 6: user_loader — טעינת משתמש מה-DB ─────────────────────────────
    @login_manager.user_loader
    def load_user(user_id: str):
        """נקרא אוטומטית בכל בקשת HTTP.

        Flask-Login שומר את ה-user_id בעוגיית הסשן.
        הפונקציה הזו טוענת את אובייקט User המלא מה-DB לפי ה-ID.
        ככה current_user זמין בכל route ובכל תבנית HTML.
        """
        return db.session.get(User, user_id)

    # ─── שלב 7: רישום Blueprints ────────────────────────────────────────────
    # Blueprint = מודול עצמאי עם routes משלו
    # כל blueprint נרשם ב-app ונותן לו את כל ה-routes שלו
    from app.auth.routes import auth_bp           # התחברות, הרשמה, שכחתי סיסמה
    from app.questionnaire.routes import questionnaire_bp  # שאלון עור ושגרה
    from app.community.routes import community_bp  # קהילה ושיתופים

    app.register_blueprint(auth_bp)
    app.register_blueprint(questionnaire_bp)
    app.register_blueprint(community_bp)

    # ─── שלב 8: טיפול בשגיאות ───────────────────────────────────────────────
    # got_request_exception = signal (אות) ש-Flask שולח כשקורית שגיאה לא מטופלת
    # הפונקציה רושמת את השגיאה ב-audit log לצורך ניטור ותחקור
    @got_request_exception.connect_via(app)
    def _on_exception(sender, exception, **extra):
        """רושם שגיאות בלתי צפויות ל-audit log."""
        log_audit_event(
            "app.exception",
            level="error",
            exception_type=type(exception).__name__,
            exception_message=str(exception),
        )

    # ─── שלב 9: דף הבית ─────────────────────────────────────────────────────
    @app.route("/")
    def index():
        """דף הבית של האתר.

        - משתמש מחובר → מופנה אוטומטית לשאלון העור
        - משתמש לא מחובר → רואה דף פתיחה עם הסבר והזמנה להירשם
        """
        from flask import redirect, render_template, url_for
        from flask_login import current_user

        if current_user.is_authenticated:
            return redirect(url_for("questionnaire.show_questionnaire"))
        return render_template("index.html")

    # ─── שלב 10: יצירת טבלאות ────────────────────────────────────────────────
    # app_context() = יוצר הקשר אפליקציה (נדרש לגישה ל-DB מחוץ ל-route)
    # create_all() = יוצר את כל הטבלאות שהוגדרו ב-models.py (אם לא קיימות)
    # שימו לב: זה לא מעדכן טבלאות קיימות — רק יוצר חדשות!
    with app.app_context():
        db.create_all()

    return app
