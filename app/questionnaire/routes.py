"""
=============================================================================
קובץ: questionnaire/routes.py
שייך ל: צד שרת (Server-Side)
=============================================================================
תפקיד הקובץ:
    ראוטים לשאלון העור ולתצוגת שגרת הטיפוח.
    זהו הליבה של האפליקציה — כאן המשתמש ממלא שאלון מפורט על העור שלו,
    ובתמורה מקבל שגרת טיפוח מותאמת אישית (בוקר + ערב).

    ראוטים שמוגדרים כאן:
    1. /questionnaire → הצגה ושמירה של שאלון העור (GET + POST)
    2. /routine       → תצוגת השגרה שנוצרה (GET)

זרימת העבודה (Flow):
    1. המשתמש נכנס ל-/questionnaire (GET) → רואה טופס ריק (או מלא אם יש תשובות קודמות)
    2. ממלא את כל השדות ולוחץ "שליחה" (POST)
    3. Flask מפעיל ולידציה על הטופס (כל השדות מולאו? ערכים תקינים?)
    4. התשובות נשמרות ב-SkinProfile (טבלת פרופיל עור)
    5. generate_routine() → יוצר שגרת בוקר/ערב (AI או fallback)
    6. השגרה נשמרת ב-Routine (שגרה נוכחית) + RoutineVersion (היסטוריה)
    7. המשתמש מועבר ל-/routine לצפייה בשגרה

טופס השאלון (SkinQuestionnaireForm):
    שדות רבים ומגוונים:
    - SelectField = תפריט נפתח (dropdown)
    - SelectMultipleField = בחירה מרובה (checkboxes)
    - RadioField = בחירה יחידה (radio buttons)
    - IntegerField = מספר שלם
    - BooleanField = כן/לא (checkbox)
    - TextAreaField = טקסט חופשי
=============================================================================
"""
from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    IntegerField,
    RadioField,
    SelectField,
    SelectMultipleField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, NumberRange, Optional
from wtforms.widgets import CheckboxInput, ListWidget

from app.extensions import db
from app.models import Routine, RoutineVersion, SkinProfile
from app.services.audit_logger import log_audit_event
from app.services.routine_ai import generate_routine

# ─── יצירת Blueprint לשאלון ──────────────────────────────────────────────────
questionnaire_bp = Blueprint("questionnaire", __name__)


# =============================================================================
# רשימות בחירה — מוגדרות כפונקציות כדי שייטענו כל פעם מחדש
# =============================================================================

def _choices_skin():
    """רשימת אפשרויות לשדה 'סוג עור' בטופס.
    כל tuple = (ערך שנשמר ב-DB, טקסט שמוצג למשתמש)
    """
    return [
        ("", "— בחרי —"),       # ברירת מחדל ריקה — מכריח את המשתמש לבחור
        ("dry", "יבש"),
        ("oily", "שומני"),
        ("normal", "רגיל / מאוזן"),
        ("combination", "מעורב (T-שומני, לחיים יבשות)"),
        ("sensitive", "רגיש"),
    ]


def _concerns():
    """רשימת חששות/בעיות עור — המשתמש יכול לבחור כמה."""
    return [
        ("acne", "פצעונים / אקנה"),
        ("dryness", "יובש"),
        ("oiliness", "ברק שומני"),
        ("redness", "אדמומיות"),
        ("dark_circles", "עיגולים כהים"),
        ("wrinkles", "קמטוטים וקמטים"),
        ("hyperpigmentation", "כתמים / פיגמנטציה"),
        ("pores", "נקבוביות בולטות"),
        ("dullness", "מראה עייף / חסר ברק"),
    ]


def _sens():
    """רשימת רגישויות לחומרים — משפיע על ההמלצות (הימנעות ממוצרים מסוימים)."""
    return [
        ("fragrance", "בשמים בקוסמטיקה"),
        ("alcohol", "אלכוהול דנaturing"),
        ("essential_oils", "שמנים אתריים"),
        ("sulfates", "סולפטים חזקים"),
        ("physical_scrub", "גרגרים גסים (סקראב פיזי)"),
    ]


def _goals():
    """רשימת מטרות טיפוח — מה המשתמש רוצה להשיג."""
    return [
        ("hydration", "לחות"),
        ("anti_aging", "אנטי-אייג'ינג"),
        ("brightening", "הבהרה"),
        ("soothing", "הרגעה"),
        ("acne_control", "שליטה בפצעונים"),
    ]


# =============================================================================
# טופס השאלון — הטופס הגדול והמרכזי של האפליקציה
# =============================================================================
class SkinQuestionnaireForm(FlaskForm):
    """טופס שאלון העור — כולל את כל השאלות על מאפייני העור.

    כל השדות נשמרים כמילון JSON ב-SkinProfile.questionnaire_json.
    אחרי שליחה תקינה, generate_routine() מייצר שגרת בוקר/ערב.

    סוגי שדות:
    - SelectField        = תפריט נפתח (dropdown) — בחירה אחת
    - SelectMultipleField = רשימת checkboxes — בחירה מרובה
    - RadioField         = כפתורי radio — בחירה אחת מתוך אפשרויות
    - IntegerField       = מספר שלם (עם min/max)
    - BooleanField       = תיבת סימון (checkbox) — כן/לא
    - TextAreaField      = שדה טקסט חופשי (רב-שורתי)
    """

    # ─── סוג עור ────────────────────────────────────────────────────────────
    # choices=[] → ריק כאן, ימולא ב-_init_form_choices() (כדי לאפשר גמישות)
    skin_type = SelectField("סוג עור עיקרי", choices=[], validators=[DataRequired(message="נא לבחור סוג עור")])

    # ─── טווח גיל ───────────────────────────────────────────────────────────
    age_range = SelectField(
        "טווח גיל",
        choices=[
            ("", "— בחרי —"),
            ("under18", "מתחת ל-18"),
            ("18_25", "18–25"),
            ("26_35", "26–35"),
            ("36_45", "36–45"),
            ("46_55", "46–55"),
            ("56_plus", "56+"),
        ],
        validators=[DataRequired()],
    )

    # ─── חששות עיקריים (בחירה מרובה) ────────────────────────────────────────
    # ListWidget + CheckboxInput = מציג כ-checkboxes ולא כ-select רב-שורות
    concerns = SelectMultipleField(
        "חששות עיקריים (ניתן לבחור כמה)",
        choices=[],
        validators=[DataRequired(message="נא לבחור לפחות חשש אחד")],
        widget=ListWidget(prefix_label=False),
        option_widget=CheckboxInput(),
    )

    # ─── רגישויות (אופציונלי) ────────────────────────────────────────────────
    sensitivities = SelectMultipleField(
        "רגישויות / להימנעות",
        choices=[],
        validators=[Optional()],  # Optional = לא חובה למלא
        widget=ListWidget(prefix_label=False),
        option_widget=CheckboxInput(),
    )

    # ─── מטרות טיפוח (אופציונלי) ────────────────────────────────────────────
    goals = SelectMultipleField(
        "מטרות טיפוח",
        choices=[],
        validators=[Optional()],
        widget=ListWidget(prefix_label=False),
        option_widget=CheckboxInput(),
    )

    # ─── תקציב (RadioField — בחירה אחת) ─────────────────────────────────────
    budget = RadioField(
        "תקציב חודשי משוער לטיפוח פנים",
        choices=[
            ("low", "נמוך"),
            ("medium", "בינוני"),
            ("high", "גבוה"),
        ],
        validators=[DataRequired()],
    )

    # ─── זמן לטיפוח (מספרים) ────────────────────────────────────────────────
    # NumberRange(min=2, max=60) = הערך חייב להיות בין 2 ל-60
    time_morning = IntegerField("דקות זמינות לטיפוח בבוקר", validators=[DataRequired(), NumberRange(min=2, max=60)])
    time_evening = IntegerField("דקות זמינות בערב", validators=[DataRequired(), NumberRange(min=2, max=90)])

    # ─── אקלים ──────────────────────────────────────────────────────────────
    climate = SelectField(
        "אקלים / עונה דומיננטית",
        choices=[
            ("", "— בחרי —"),
            ("hot_humid", "חם ולח"),
            ("hot_dry", "חם ויבש"),
            ("mild", "מתון"),
            ("cold_dry", "קר ויבש"),
        ],
        validators=[DataRequired()],
    )

    # ─── מי ברז ─────────────────────────────────────────────────────────────
    water_hard = RadioField(
        "מי ברז בבית",
        choices=[("soft", "רכים"), ("hard", "קשים / אבנית"), ("unknown", "לא יודעת")],
        validators=[DataRequired()],
    )

    # ─── חשיפה לשמש ─────────────────────────────────────────────────────────
    sun_exposure = RadioField(
        "חשיפה לשמש יומית",
        choices=[
            ("minimal", "מינימלית"),
            ("moderate", "בינונית"),
            ("high", "גבוהה"),
        ],
        validators=[DataRequired()],
    )

    # ─── תדירות איפור ───────────────────────────────────────────────────────
    makeup_frequency = RadioField(
        "תדירות איפור",
        choices=[
            ("daily", "כמעט יומי"),
            ("sometimes", "לפעמים"),
            ("rare", "נדיר / אין"),
        ],
        validators=[DataRequired()],
    )

    # ─── שימוש ב-SPF (הגנה מהשמש) ───────────────────────────────────────────
    spf_habit = RadioField(
        "שימוש ב-SPF",
        choices=[
            ("always", "תמיד בבוקר"),
            ("sometimes", "לפעמים"),
            ("rarely", "לעיתים רחוקות"),
        ],
        validators=[DataRequired()],
    )

    # ─── אקספוליאציה (פילינג) ────────────────────────────────────────────────
    exfoliation = RadioField(
        "אקספוליאציה (פילינג) היום",
        choices=[
            ("never", "לא משתמשת"),
            ("1_2", "1–2 בשבוע"),
            ("3_plus", "3+ בשבוע"),
        ],
        validators=[DataRequired()],
    )

    # ─── ניסיון עם רטינול ────────────────────────────────────────────────────
    retinol = RadioField(
        "ניסיון עם רטינול / רטינואיד",
        choices=[
            ("none", "אין ניסיון"),
            ("beginner", "מתחילה / מדי פעם"),
            ("regular", "שימוש קבוע"),
        ],
        validators=[DataRequired()],
    )

    # ─── הריון / הנקה ────────────────────────────────────────────────────────
    pregnancy = RadioField(
        "הריון / הנקה (למידע בלבד — אין המלצות רפואיות)",
        choices=[
            ("no", "לא"),
            ("pregnant", "הריון"),
            ("nursing", "הנקה"),
            ("unsure", "מעדיפה לא לציין"),
        ],
        validators=[DataRequired()],
    )

    # ─── שימוש בחומצות ───────────────────────────────────────────────────────
    uses_actives = BooleanField("משתמשת כיום בחומצות / ויטמין סי / רטינול באופן קבוע")

    # ─── הערות חופשיות ───────────────────────────────────────────────────────
    notes = TextAreaField("הערות נוספות (אופציונלי)", validators=[Optional()])

    # ─── כפתור שליחה ─────────────────────────────────────────────────────────
    submit = SubmitField("שליחה ויצירת שגרה מותאמת")


# =============================================================================
# פונקציות עזר לטיפול בטופס
# =============================================================================

def _init_form_choices(form: SkinQuestionnaireForm) -> None:
    """טוען את רשימות הבחירה הדינמיות לתוך אובייקט הטופס.

    נקרא לפני הצגת הטופס כדי למלא את ה-choices של שדות שהוגדרו
    עם choices=[] (ריק). זה מאפשר לשנות את הרשימות בקלות.
    """
    form.skin_type.choices = _choices_skin()
    form.concerns.choices = _concerns()
    form.sensitivities.choices = _sens()
    form.goals.choices = _goals()


def _answers_to_dict(form: SkinQuestionnaireForm) -> dict:
    """ממיר את כל נתוני הטופס למילון Python אחיד.

    המילון הזה נשמר כ-JSON ב-SkinProfile.questionnaire_json
    וגם משמש כקלט ליצירת השגרה (generate_routine).
    """
    return {
        "skin_type": form.skin_type.data,
        "age_range": form.age_range.data,
        "concerns": list(form.concerns.data or []),
        "sensitivities": list(form.sensitivities.data or []),
        "goals": list(form.goals.data or []),
        "budget": form.budget.data,
        "time_morning": form.time_morning.data,
        "time_evening": form.time_evening.data,
        "climate": form.climate.data,
        "water_hard": form.water_hard.data,
        "sun_exposure": form.sun_exposure.data,
        "makeup_frequency": form.makeup_frequency.data,
        "spf_habit": form.spf_habit.data,
        "exfoliation": form.exfoliation.data,
        "retinol": form.retinol.data,
        "pregnancy": form.pregnancy.data,
        "uses_actives": bool(form.uses_actives.data),
        "notes": (form.notes.data or "").strip(),
    }


def _hydrate_form_from_answers(form: SkinQuestionnaireForm, answers: dict) -> None:
    """טוען תשובות קודמות לתוך הטופס (לעריכה חוזרת).

    כשמשתמש חוזר לשאלון, הוא רואה את התשובות שמילא בפעם הקודמת
    ולא צריך למלא הכל מהתחלה.
    """
    form.skin_type.data = answers.get("skin_type")
    form.age_range.data = answers.get("age_range")
    form.concerns.data = list(answers.get("concerns") or [])
    form.sensitivities.data = list(answers.get("sensitivities") or [])
    form.goals.data = list(answers.get("goals") or [])
    form.budget.data = answers.get("budget")
    form.time_morning.data = answers.get("time_morning")
    form.time_evening.data = answers.get("time_evening")
    form.climate.data = answers.get("climate")
    form.water_hard.data = answers.get("water_hard")
    form.sun_exposure.data = answers.get("sun_exposure")
    form.makeup_frequency.data = answers.get("makeup_frequency")
    form.spf_habit.data = answers.get("spf_habit")
    form.exfoliation.data = answers.get("exfoliation")
    form.retinol.data = answers.get("retinol")
    form.pregnancy.data = answers.get("pregnancy")
    form.uses_actives.data = bool(answers.get("uses_actives"))
    form.notes.data = answers.get("notes")


def _summary_label(answers: dict) -> str:
    """יוצר תיאור קצר בעברית מתשובות השאלון — לתצוגה בממשק.

    לדוגמה: "יבש — פצעונים · יובש · אדמומיות"
    מוצג בדף השגרה ובפרופיל בקהילה.
    """
    st = answers.get("skin_type", "")
    mapping = dict(_choices_skin()[1:])  # המרה מקוד לעברית (ללא הערך הריק)
    skin_he = mapping.get(st, st)
    concerns = answers.get("concerns") or []
    cm = dict(_concerns())  # המרה מקוד לעברית
    cs = " · ".join([cm.get(c, c) for c in concerns[:3]])  # מציג עד 3 חששות
    if len(concerns) > 3:
        cs += "…"  # אם יש יותר מ-3, מוסיפים שלוש נקודות
    return f"{skin_he} — {cs or 'ללא ציון חששות'}"


# =============================================================================
# ראוטים
# =============================================================================

@questionnaire_bp.route("/questionnaire", methods=["GET", "POST"])
@login_required  # חובה להיות מחובר כדי למלא שאלון
def show_questionnaire():
    """ראוט השאלון — /questionnaire

    GET — הצגת הטופס:
    - יוצר אובייקט טופס
    - אם יש תשובות קודמות ב-DB → טוען אותן לטופס (לעריכה חוזרת)
    - מציג את form.html

    POST — שמירת תשובות ויצירת שגרה:
    1. ולידציה — כל השדות מולאו כנדרש?
    2. שמירת תשובות ב-SkinProfile (JSON)
    3. יצירת שגרה: generate_routine() → בוקר + ערב
    4. שמירת שגרה נוכחית ב-Routine
    5. שמירת גרסה בהיסטוריה (RoutineVersion)
    6. הפניה לדף השגרה (/routine)
    """
    # יצירת אובייקט הטופס וטעינת רשימות בחירה
    form = SkinQuestionnaireForm()
    _init_form_choices(form)

    # בדיקה אם יש פרופיל קיים (תשובות קודמות)
    prof = SkinProfile.query.filter_by(user_id=current_user.id).first()

    # טעינת תשובות קודמות — רק אם זה GET (לא POST)
    if prof and form.is_submitted() is False:
        _hydrate_form_from_answers(form, prof.get_answers())

    # ─── טיפול ב-POST (שליחת טופס) ──────────────────────────────────────
    if form.validate_on_submit():
        # שלב 1: המרת נתוני הטופס למילון
        answers = _answers_to_dict(form)

        # שלב 2: שמירת/עדכון פרופיל עור
        if prof is None:
            prof = SkinProfile(user_id=current_user.id)
            db.session.add(prof)
        prof.set_answers(answers)          # שומר כ-JSON
        prof.summary_label = _summary_label(answers)  # סיכום קצר

        # שלב 3: יצירת שגרת טיפוח (AI או fallback)
        # generate_routine מחזירה: (טקסט_בוקר, טקסט_ערב, האם_AI)
        m_text, e_text, used_ai = generate_routine(answers)

        # שלב 4: שמירת/עדכון שגרה נוכחית
        r = Routine.query.filter_by(user_id=current_user.id).first()
        if r is None:
            r = Routine(user_id=current_user.id)
            db.session.add(r)
        r.morning_text = m_text
        r.evening_text = e_text
        r.used_openai = used_ai

        # שלב 5: יצירת גרסה חדשה בהיסטוריה
        prev_version = (
            RoutineVersion.query.filter_by(user_id=current_user.id)
            .order_by(RoutineVersion.version_number.desc())
            .first()
        )
        next_version = (prev_version.version_number + 1) if prev_version else 1

        rv = RoutineVersion(
            user_id=current_user.id,
            version_number=next_version,
            morning_text=m_text,
            evening_text=e_text,
            used_openai=used_ai,
        )
        rv.set_answers(answers)  # שמירת snapshot של התשובות
        db.session.add(rv)

        # שמירת הכל ב-DB
        db.session.commit()

        log_audit_event(
            "questionnaire.submit_success",
            user_id=current_user.id,
            routine_version=next_version,
            used_openai=used_ai,
        )
        flash(f"השאלון נשמר ונוצרה שגרה מותאמת אישית (גרסה {next_version}).", "success")

        # שלב 6: הפניה לדף השגרה
        return redirect(url_for("questionnaire.view_routine"))

    # ─── טיפול בולידציה שנכשלה ───────────────────────────────────────────
    if form.is_submitted():
        log_audit_event(
            "questionnaire.submit_partial",
            level="warning",
            user_id=current_user.id,
        )
        flash(
            "מילאת את השאלון באופן חלקי, מלאי באופן מלא על מנת לקבל את השגרה שלך!",
            "warning",
        )

    # ─── הצגת הטופס (GET או POST שנכשל) ─────────────────────────────────
    return render_template("questionnaire/form.html", form=form)


@questionnaire_bp.route("/routine", methods=["GET"])
@login_required
def view_routine():
    """ראוט תצוגת שגרה — /routine

    מציג את השגרה האחרונה שנוצרה למשתמש (בוקר + ערב).
    אם אין עדיין פרופיל או שגרה — מפנה חזרה לשאלון.
    """
    r = Routine.query.filter_by(user_id=current_user.id).first()
    prof = SkinProfile.query.filter_by(user_id=current_user.id).first()
    latest_version = (
        RoutineVersion.query.filter_by(user_id=current_user.id)
        .order_by(RoutineVersion.version_number.desc())
        .first()
    )
    if not r or not prof:
        flash("עדיין לא מולא שאלון — נא למלא את השאלון.", "warning")
        return redirect(url_for("questionnaire.show_questionnaire"))

    return render_template(
        "questionnaire/routine.html",
        routine=r,               # שגרה נוכחית (Routine)
        profile=prof,            # פרופיל עור (SkinProfile)
        answers=prof.get_answers(),  # תשובות כמילון (לתצוגה)
        latest_version=latest_version,  # מספר הגרסה האחרונה
    )
