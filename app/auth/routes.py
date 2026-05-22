"""
=============================================================================
קובץ: auth/routes.py
שייך ל: צד שרת (Server-Side) — Flask Web Server
         (משמש גם כלקוח TCP מול שרת האימות!)
=============================================================================
תפקיד הקובץ:
    ראוטים (Routes / Endpoints) לאימות משתמשים באתר.
    ראוט = כתובת URL שהשרת מגיב אליה.

    הקובץ מגדיר 4 ראוטים:
    1. /login          → דף התחברות
    2. /register       → דף הרשמה
    3. /forgot-password → דף איפוס סיסמה
    4. /logout         → ניתוק מהמערכת

ארכיטקטורת אימות — שרת-לקוח (Client-Server):
    הפרויקט הזה לא בודק סיסמאות ישירות ב-Flask!
    במקום זה, יש ארכיטקטורת שרת-לקוח:

    [דפדפן] → HTTP → [Flask (Web Server)] → TCP Socket → [שרת אימות (פורט 5050)]
                                                              ↕
                                                         [מסד נתונים]

    זרימת התחברות:
    1. המשתמש מקליד אימייל וסיסמה בטופס HTML ולוחץ "התחברות"
    2. הדפדפן שולח בקשת HTTP POST ל-Flask
    3. Flask מפעיל ולידציה על הטופס (CSRF, פורמט אימייל)
    4. Flask שולח את הנתונים כ-JSON דרך TCP Socket לשרת האימות
    5. שרת האימות בודק את הסיסמה מול ה-DB ומחזיר תשובה
    6. Flask מקבל את התשובה ויוצר סשן (cookie) בדפדפן

    למה ככה ולא ישירות?
    - הפרדת אחריות (Separation of Concerns)
    - הדגמת ארכיטקטורת שרת-לקוח (דרישת הפרויקט)
    - שרת האימות יכול לרוץ על מחשב אחר ברשת

טפסים (Forms):
    הקובץ מגדיר 3 טפסי FlaskForm (WTForms):
    - LoginForm          → טופס התחברות
    - RegisterForm       → טופס הרשמה
    - ResetPasswordForm  → טופס איפוס סיסמה

    כל טופס כולל:
    - ולידציה אוטומטית (DataRequired, Email, Length...)
    - הגנת CSRF (hidden_tag מייצר אסימון סודי בטופס)
=============================================================================
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

# ─── יצירת Blueprint לאימות ──────────────────────────────────────────────────
# Blueprint = מודול עצמאי עם routes משלו
# url_prefix="" → הראוטים יהיו ישירות תחת / (למשל /login, לא /auth/login)
auth_bp = Blueprint("auth", __name__, url_prefix="")


# =============================================================================
# ולידטור מותאם אישית לחוזק סיסמה
# =============================================================================
def _validate_password_strength(form, field):
    """ולידטור WTForms מותאם אישית — בודק חוזק סיסמה.

    WTForms קורא לפונקציה הזו אוטומטית כשמשתמש שולח טופס.
    אם הסיסמה חלשה, הפונקציה מרימה ValidationError שמוצג כשגיאה בטופס.

    Args:
        form: אובייקט הטופס (לא בשימוש כאן)
        field: השדה שנבדק (password) — field.data מכיל את הטקסט שהוזן
    """
    err = password_strength_error(field.data or "")
    if err:
        raise ValidationError(err)


# =============================================================================
# הגדרת טפסים (Forms) — כל טופס מייצג דף HTML עם שדות קלט
# =============================================================================
class LoginForm(FlaskForm):
    """טופס התחברות.

    FlaskForm:
        מחלקת בסיס מ-Flask-WTF שמוסיפה:
        - הגנת CSRF אוטומטית (hidden_tag בתבנית HTML)
        - ולידציה אוטומטית (validate_on_submit)

    שדות:
        email    → שדה טקסט עם ולידציית אימייל
        password → שדה סיסמה (מוסתר בדפדפן)
        submit   → כפתור שליחה
    """
    email = StringField("אימייל", validators=[DataRequired(), Email()])
    password = PasswordField("סיסמה", validators=[DataRequired()])
    submit = SubmitField("התחברות")


class RegisterForm(FlaskForm):
    """טופס הרשמה — כולל ולידציית חוזק סיסמה ואימות סיסמה כפול.

    שדות:
        email      → אימייל (חובה, פורמט תקין)
        first_name → שם פרטי (אופציונלי, עד 50 תווים)
        last_name  → שם משפחה (אופציונלי)
        password   → סיסמה (חובה, מינימום 8 תווים, חוזק נבדק)
        password2  → אימות סיסמה (חייב להיות זהה ל-password)
    """
    email = StringField("אימייל", validators=[DataRequired(), Email()])
    first_name = StringField("שם פרטי", validators=[Length(max=50)])
    last_name = StringField("שם משפחה", validators=[Length(max=50)])
    password = PasswordField(
        "סיסמה",
        validators=[DataRequired(), Length(min=8, message="לפחות 8 תווים"), _validate_password_strength],
    )
    # EqualTo("password") → בודק שהערך זהה לשדה password
    password2 = PasswordField(
        "אימות סיסמה",
        validators=[DataRequired(), EqualTo("password", message="הסיסמאות אינן תואמות")],
    )
    submit = SubmitField("הרשמה")


class ResetPasswordForm(FlaskForm):
    """טופס איפוס סיסמה — גרסת דמו (ללא שליחת קישור באימייל).

    בפרויקט אמיתי: שולחים קישור חד-פעמי למייל.
    כאן (דמו לימודי): מזינים אימייל + סיסמה חדשה ישירות.
    """
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


# =============================================================================
# פונקציות עזר
# =============================================================================
def _login_user_from_socket_response(resp: dict) -> User | None:
    """טוען את אובייקט User מה-DB אחרי תשובה מוצלחת משרת האימות.

    שרת הסוקטים מחזיר user_id בתשובה. הפונקציה הזו משתמשת ב-ID
    כדי לטעון את אובייקט User המלא מה-DB (עם כל השדות והקשרים).

    Args:
        resp: מילון התשובה משרת הסוקטים (כולל resp["user"]["user_id"])

    Returns:
        אובייקט User מה-DB, או None אם לא נמצא
    """
    user_data = resp.get("user") or {}
    user_id = user_data.get("user_id")
    if not user_id:
        return None
    return db.session.get(User, user_id)


# =============================================================================
# ראוטים (Routes) — כל ראוט = כתובת URL שהשרת מגיב אליה
# =============================================================================

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """ראוט התחברות — /login

    GET (כניסה לדף):
        מציג את טופס ההתחברות (login.html)

    POST (שליחת טופס):
        1. בודק ולידציה של הטופס (CSRF, פורמט אימייל)
        2. שולח את הנתונים לשרת הסוקטים (TCP, פורט 5050)
        3. אם ההתחברות הצליחה:
           - טוען את המשתמש מה-DB
           - יוצר סשן (cookie) בדפדפן באמצעות login_user()
           - רושם את האירוע ב-audit log
           - מפנה לשאלון העור
        4. אם נכשל:
           - מציג הודעת שגיאה
           - רושם את הכישלון ב-audit log (לניטור אבטחה)
    """
    # אם המשתמש כבר מחובר — מפנים לשאלון (אין צורך בהתחברות שוב)
    if current_user.is_authenticated:
        return redirect(url_for("questionnaire.show_questionnaire"))

    form = LoginForm()

    # validate_on_submit() = בודק שזו בקשת POST + כל הולידציות עוברות
    if form.validate_on_submit():
        email = form.email.data.strip().lower()  # נירמול אימייל (אותיות קטנות, ללא רווחים)

        # ─── שליחה לשרת הסוקטים ──────────────────────────────────────────
        # auth_socket_request = פותח חיבור TCP, שולח JSON, מקבל תשובה
        resp = auth_socket_request(
            {
                "action": "login",        # סוג הפעולה
                "email": email,            # אימייל שהוזן
                "password": form.password.data,  # סיסמה שהוזנה
            }
        )

        # ─── טיפול בתשובה ────────────────────────────────────────────────
        if not resp.get("ok"):
            # התחברות נכשלה — רושמים ב-audit ומציגים שגיאה
            log_audit_event(
                "auth.login_failed",
                level="warning",
                email=email,
                reason=resp.get("error", "socket_auth_failed"),
            )
            flash(resp.get("message") or "אימייל או סיסמה שגויים.", "danger")
            return render_template("auth/login.html", form=form)

        # התחברות הצליחה — טוענים את המשתמש מה-DB
        user = _login_user_from_socket_response(resp)
        if user is None:
            flash("שגיאה בטעינת המשתמש אחרי אימות.", "danger")
            return render_template("auth/login.html", form=form)

        # login_user = יוצר עוגיית סשן (cookie) בדפדפן
        # remember=True → העוגייה נשמרת גם אחרי סגירת הדפדפן
        login_user(user, remember=True)
        log_audit_event("auth.login_success", user_id=user.id, email=user.email)

        # redirect לדף הבא — אם המשתמש ניסה לגשת לדף מוגן לפני ההתחברות
        next_url = request.args.get("next")
        if next_url and next_url.startswith("/"):  # מניעת redirect לאתר חיצוני זדוני
            return redirect(next_url)
        return redirect(url_for("questionnaire.show_questionnaire"))

    # GET — מציגים את טופס ההתחברות
    return render_template("auth/login.html", form=form)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """ראוט הרשמה — /register

    זרימה דומה ל-login, אבל:
    1. שולח action="register" לשרת הסוקטים
    2. השרת יוצר משתמש חדש ב-DB (אם האימייל לא קיים)
    3. אחרי הרשמה מוצלחת — מתחבר אוטומטית (login_user)
    4. מפנה לשאלון העור
    """
    if current_user.is_authenticated:
        return redirect(url_for("questionnaire.show_questionnaire"))

    form = RegisterForm()

    if form.validate_on_submit():
        email = form.email.data.strip().lower()

        # שליחה לשרת הסוקטים — כולל שם פרטי ושם משפחה
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

        # הרשמה הצליחה — מתחברים אוטומטית
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
    """ראוט איפוס סיסמה — /forgot-password

    גרסת דמו: המשתמש מזין אימייל + סיסמה חדשה ישירות.
    (בפרויקט אמיתי: שולחים קישור חד-פעמי למייל)

    שולח action="reset_password" לשרת הסוקטים.
    """
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
@login_required  # רק משתמש מחובר יכול להתנתק (הגיוני, לא?)
def logout():
    """ראוט ניתוק — /logout

    מוחק את עוגיית הסשן מהדפדפן.
    לא שולח בקשה לשרת הסוקטים — הסשן הוא רק בצד ה-Flask.

    @login_required = דקורטור שדורש שהמשתמש יהיה מחובר.
    אם לא מחובר — Flask-Login מפנה אוטומטית לדף ההתחברות.
    """
    log_audit_event("auth.logout", user_id=current_user.id, email=current_user.email)
    logout_user()  # מוחק את הסשן
    flash("התנתקת בהצלחה.", "info")
    return redirect(url_for("auth.login"))
