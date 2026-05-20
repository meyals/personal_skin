"""ראוטים לאימות משתמשים — ממשק Web (Flask) + תקשורת TCP לשרת אימות.

זרימת login/register:
  1. משתמש שולח טופס (Flask-WTF + CSRF)
  2. Flask שולח JSON לשרת סוקטים (auth_socket_request)
  3. שרת בודק/שומר ב-DB ומחזיר תשובה
  4. Flask יוצר סשן (login_user) ומפנה לשאלון

logout מתבצע רק ב-Flask — מוחק את הסשן מהדפדפן.
"""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError

from app.auth.validation import password_strength_error
from app.extensions import db
from app.models import User
from app.services.audit_logger import log_audit_event
from app.socket_auth.client import auth_socket_request

auth_bp = Blueprint("auth", __name__, url_prefix="")


def _validate_password_strength(form, field):
    """ולידטור WTForms — דורש אות, ספרה ותו מיוחד (לפני שליחה לשרת)."""
    err = password_strength_error(field.data or "")
    if err:
        raise ValidationError(err)


class LoginForm(FlaskForm):
    """טופס התחברות — כולל אסימון CSRF אוטומטי (hidden_tag)."""

    email = StringField("אימייל", validators=[DataRequired(), Email()])
    password = PasswordField("סיסמה", validators=[DataRequired()])
    submit = SubmitField("התחברות")


class RegisterForm(FlaskForm):
    """טופס הרשמה — ולידציה מקומית + בדיקה בשרת (אימייל כפול)."""

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


class ResetPasswordForm(FlaskForm):
    """איפוס סיסמה לפי אימייל (ללא קישור במייל — דמו לימודי)."""

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


def _login_user_from_socket_response(resp: dict) -> User | None:
    """טוען את אובייקט User מ-DB אחרי תשובה מוצלחת מהשרת."""
    user_data = resp.get("user") or {}
    user_id = user_data.get("user_id")
    if not user_id:
        return None
    return db.session.get(User, user_id)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """GET: מציג טופס. POST: שולח לשרת סוקטים, יוצר סשן בהצלחה."""
    if current_user.is_authenticated:
        return redirect(url_for("questionnaire.show_questionnaire"))
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        resp = auth_socket_request(
            {
                "action": "login",
                "email": email,
                "password": form.password.data,
            }
        )
        if not resp.get("ok"):
            log_audit_event(
                "auth.login_failed",
                level="warning",
                email=email,
                reason=resp.get("error", "socket_auth_failed"),
            )
            flash(resp.get("message") or "אימייל או סיסמה שגויים.", "danger")
            return render_template("auth/login.html", form=form)

        user = _login_user_from_socket_response(resp)
        if user is None:
            flash("שגיאה בטעינת המשתמש אחרי אימות.", "danger")
            return render_template("auth/login.html", form=form)

        login_user(user, remember=True)  # יוצר cookie סשן
        log_audit_event("auth.login_success", user_id=user.id, email=user.email)
        next_url = request.args.get("next")
        if next_url and next_url.startswith("/"):  # מניעת redirect חיצוני זדוני
            return redirect(next_url)
        return redirect(url_for("questionnaire.show_questionnaire"))
    return render_template("auth/login.html", form=form)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """הרשמה דרך שרת סוקטים + התחברות אוטומטית + מעבר לשאלון."""
    if current_user.is_authenticated:
        return redirect(url_for("questionnaire.show_questionnaire"))
    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        resp = auth_socket_request(
            {
                "action": "register",
                "email": email,
                "password": form.password.data,
                "first_name": (form.first_name.data or "").strip(),
                "last_name": (form.last_name.data or "").strip(),
            }
        )
        if not resp.get("ok"):
            log_audit_event(
                "auth.register_failed",
                level="warning",
                email=email,
                reason=resp.get("error", "socket_auth_failed"),
            )
            flash(resp.get("message") or "ההרשמה נכשלה.", "danger")
            return render_template("auth/register.html", form=form)

        user = _login_user_from_socket_response(resp)
        if user is None:
            flash("שגיאה בטעינת המשתמש אחרי הרשמה.", "danger")
            return render_template("auth/register.html", form=form)

        login_user(user, remember=True)
        log_audit_event("auth.register_success", user_id=user.id, email=user.email)
        flash("נרשמת בהצלחה. עכשיו נמלא את שאלון העור.", "success")
        return redirect(url_for("questionnaire.show_questionnaire"))
    return render_template("auth/register.html", form=form)


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """איפוס סיסמה — נשלח לשרת הסוקטים (לא דורש התחברות)."""
    if current_user.is_authenticated:
        return redirect(url_for("questionnaire.show_questionnaire"))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        resp = auth_socket_request(
            {
                "action": "reset_password",
                "email": email,
                "password": form.password.data,
            }
        )
        if not resp.get("ok"):
            log_audit_event(
                "auth.password_reset_failed",
                level="warning",
                email=email,
                reason=resp.get("error", "socket_auth_failed"),
            )
            flash(resp.get("message") or "איפוס הסיסמה נכשל.", "danger")
            return render_template("auth/forgot_password.html", form=form)

        log_audit_event(
            "auth.password_reset_success",
            user_id=(resp.get("user") or {}).get("user_id"),
            email=email,
        )
        flash("הסיסמה אופסה בהצלחה. ניתן להתחבר עם הסיסמה החדשה.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/forgot_password.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    """מסיר את הסשן מהדפדפן — לא קורא לשרת הסוקטים."""
    log_audit_event("auth.logout", user_id=current_user.id, email=current_user.email)
    logout_user()
    flash("התנתקת בהצלחה.", "info")
    return redirect(url_for("auth.login"))
