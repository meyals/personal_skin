"""יישום Flask — PersonalSkin."""
import os

from flask import Flask

from app.config import config_by_name
from app.extensions import db, login_manager
from app.models import User


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )
    cfg = config_name or os.getenv("FLASK_CONFIG", "development")
    app.config.from_object(config_by_name.get(cfg, config_by_name["development"]))

    db.init_app(app)
    login_manager.init_app(app)

    from app.utils import render_markdown_safe

    app.jinja_env.filters["markdown_safe"] = render_markdown_safe

    @login_manager.user_loader
    def load_user(user_id: str):
        return db.session.get(User, user_id)

    from app.auth.routes import auth_bp
    from app.questionnaire.routes import questionnaire_bp
    from app.community.routes import community_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(questionnaire_bp)
    app.register_blueprint(community_bp)

    @app.route("/")
    def index():
        from flask import redirect, render_template, url_for
        from flask_login import current_user

        if current_user.is_authenticated:
            return redirect(url_for("questionnaire.show_questionnaire"))
        return render_template("index.html")

    with app.app_context():
        db.create_all()

    return app
