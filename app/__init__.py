"""יישום Flask — PersonalSkin (App Factory).

יוצר את האפליקציה, מחבר מסד נתונים, אימות, audit, ו-blueprints:
- auth: התחברות/הרשמה (דרך שרת סוקטים)
- questionnaire: שאלון עור ושגרה
- community: שיתוף ולייקים
"""
import os

from flask import Flask
from flask.signals import got_request_exception

from app.config import config_by_name
from app.extensions import db, login_manager
from app.models import User
from app.services.audit_logger import init_async_audit_logger, log_audit_event


def create_app(config_name: str | None = None) -> Flask:
    """בונה ומאתחל את אפליקציית Flask.

    שלבי אתחול:
    1. טעינת הגדרות (config.py)
    2. הפעלת audit logger ברקע (thread)
    3. חיבור DB ו-Flask-Login
    4. רישום blueprints (מודולי routes)
    5. יצירת טבלאות אם לא קיימות (db.create_all)
    """
    app = Flask(
        __name__,
        template_folder="../templates",  # דפי HTML
        static_folder="../static",  # CSS וקבצים סטטיים
    )
    cfg = config_name or os.getenv("FLASK_CONFIG", "development")
    app.config.from_object(config_by_name.get(cfg, config_by_name["development"]))

    # תיעוד אירועים אסינכרוני — לא חוסם בקשות HTTP
    init_async_audit_logger(app)

    db.init_app(app)
    login_manager.init_app(app)

    from app.utils import render_markdown_safe

    # פילטר Jinja: Markdown בטוח (bleach) לתצוגת שגרות
    app.jinja_env.filters["markdown_safe"] = render_markdown_safe

    @login_manager.user_loader
    def load_user(user_id: str):
        """נקרא בכל בקשה — טוען את המשתמש מ-DB לפי מזהה מהסשן."""
        return db.session.get(User, user_id)

    from app.auth.routes import auth_bp
    from app.questionnaire.routes import questionnaire_bp
    from app.community.routes import community_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(questionnaire_bp)
    app.register_blueprint(community_bp)

    @got_request_exception.connect_via(app)
    def _on_exception(sender, exception, **extra):
        """רושם שגיאות לא מטופלות ל-audit.log."""
        log_audit_event(
            "app.exception",
            level="error",
            exception_type=type(exception).__name__,
            exception_message=str(exception),
        )

    @app.route("/")
    def index():
        """דף בית — מחוברים מועברים לשאלון, אחרים רואים דף פתיחה."""
        from flask import redirect, render_template, url_for
        from flask_login import current_user

        if current_user.is_authenticated:
            return redirect(url_for("questionnaire.show_questionnaire"))
        return render_template("index.html")

    with app.app_context():
        # יוצר טבלאות במסד אם עדיין לא קיימות (אין migrations)
        db.create_all()

    return app
