"""הרשמה והתחברות."""
from datetime import datetime, timezone
import re

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError

from app.extensions import db, login_manager
from app.models import User

auth_bp = Blueprint("auth", __name__, url_prefix="")


def _validate_password_strength(form, field):
    value = field.data or ""
    if len(value) < 8:
        raise ValidationError("הסיסמה חייבת להכיל לפחות 8 תווים.")
    if not re.search(r"[A-Za-z]", value):
        raise ValidationError("הסיסמה חייבת להכיל לפחות אות אחת באנגלית.")
    if not re.search(r"\d", value):
        raise ValidationError("הסיסמה חייבת להכיל לפחות מספר אחד.")
    if not re.search(r"[^A-Za-z0-9]", value):
        raise ValidationError("הסיסמה חייבת להכיל לפחות תו מיוחד אחד.")


class LoginForm(FlaskForm):
    email = StringField("אימייל", validators=[DataRequired(), Email()])
    password = PasswordField("סיסמה", validators=[DataRequired()])
    submit = SubmitField("התחברות")


class RegisterForm(FlaskForm):
    email = StringField("אימייל", validators=[DataRequired(), Email()])
    first_name = StringField("שם פרטי", validators=[Length(max=50)])
    last_name = StringField("שם משפחה", validators=[Length(max=50)])
    password = PasswordField(
        "סיסמה",
        validators=[DataRequired(), Length(min=8, message="לפחות 8 תווים"), _validate_password_strength],
    )
    password2 = PasswordField(
        "אימות סיסמה",
        validators=[DataRequired(), EqualTo("password", message="הסיסמאות אינן תואמות")],
    )
    submit = SubmitField("הרשמה")

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.strip().lower()).first():
            raise ValidationError("כתובת האימייל כבר רשומה במערכת.")


class ResetPasswordForm(FlaskForm):
    email = StringField("אימייל", validators=[DataRequired(), Email()])
    password = PasswordField(
        "סיסמה חדשה",
        validators=[DataRequired(), Length(min=8, message="לפחות 8 תווים"), _validate_password_strength],
    )
    password2 = PasswordField(
        "אימות סיסמה חדשה",
        validators=[DataRequired(), EqualTo("password", message="הסיסמאות אינן תואמות")],
    )
    submit = SubmitField("איפוס סיסמה")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("questionnaire.show_questionnaire"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user is None or not user.check_password(form.password.data):
            flash("אימייל או סיסמה שגויים.", "danger")
            return render_template("auth/login.html", form=form)
        user.last_login = datetime.now(timezone.utc)
        db.session.commit()
        login_user(user, remember=True)
        next_url = request.args.get("next")
        if next_url and next_url.startswith("/"):
            return redirect(next_url)
        return redirect(url_for("questionnaire.show_questionnaire"))
    return render_template("auth/login.html", form=form)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("questionnaire.show_questionnaire"))
    form = RegisterForm()
    if form.validate_on_submit():
        u = User(
            email=form.email.data.strip().lower(),
            first_name=(form.first_name.data or "").strip() or None,
            last_name=(form.last_name.data or "").strip() or None,
        )
        u.set_password(form.password.data)
        db.session.add(u)
        db.session.commit()
        login_user(u, remember=True)
        flash("נרשמת בהצלחה. עכשיו נמלא את שאלון העור.", "success")
        return redirect(url_for("questionnaire.show_questionnaire"))
    return render_template("auth/register.html", form=form)


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for("questionnaire.show_questionnaire"))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user is None:
            flash("לא נמצא משתמש עם האימייל הזה.", "danger")
            return render_template("auth/forgot_password.html", form=form)
        user.set_password(form.password.data)
        db.session.commit()
        flash("הסיסמה אופסה בהצלחה. ניתן להתחבר עם הסיסמה החדשה.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/forgot_password.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("התנתקת בהצלחה.", "info")
    return redirect(url_for("auth.login"))
