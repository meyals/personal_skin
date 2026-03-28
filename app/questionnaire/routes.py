"""שאלון עור ויצירת שגרה."""
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

from app.extensions import db
from app.models import Routine, SkinProfile
from app.services.routine_ai import generate_routine

questionnaire_bp = Blueprint("questionnaire", __name__)


def _choices_skin():
    return [
        ("", "— בחרי —"),
        ("dry", "יבש"),
        ("oily", "שומני"),
        ("normal", "רגיל / מאוזן"),
        ("combination", "מעורב (T-שומני, לחיים יבשות)"),
        ("sensitive", "רגיש"),
    ]


def _concerns():
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
    return [
        ("fragrance", "בשמים בקוסמטיקה"),
        ("alcohol", "אלכוהול דנaturing"),
        ("essential_oils", "שמנים אתריים"),
        ("sulfates", "סולפטים חזקים"),
        ("physical_scrub", "גרגרים גסים (סקראב פיזי)"),
    ]


def _goals():
    return [
        ("hydration", "לחות"),
        ("anti_aging", "אנטי-אייג'ינג"),
        ("brightening", "הבהרה"),
        ("soothing", "הרגעה"),
        ("acne_control", "שליטה בפצעונים"),
    ]


class SkinQuestionnaireForm(FlaskForm):
    skin_type = SelectField("סוג עור עיקרי", choices=[], validators=[DataRequired(message="נא לבחור סוג עור")])
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
    concerns = SelectMultipleField("חששות עיקריים (ניתן לבחור כמה)", choices=[], validators=[DataRequired(message="נא לבחור לפחות חשש אחד")])
    sensitivities = SelectMultipleField("רגישויות / להימנעות", choices=[], validators=[Optional()])
    goals = SelectMultipleField("מטרות טיפוח", choices=[], validators=[Optional()])
    budget = RadioField(
        "תקציב חודשי משוער לטיפוח פנים",
        choices=[
            ("low", "נמוך"),
            ("medium", "בינוני"),
            ("high", "גבוה"),
        ],
        validators=[DataRequired()],
    )
    time_morning = IntegerField("דקות זמינות לטיפוח בבוקר", validators=[DataRequired(), NumberRange(min=2, max=60)])
    time_evening = IntegerField("דקות זמינות בערב", validators=[DataRequired(), NumberRange(min=2, max=90)])
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
    water_hard = RadioField(
        "מי ברז בבית",
        choices=[("soft", "רכים"), ("hard", "קשים / אבנית"), ("unknown", "לא יודעת")],
        validators=[DataRequired()],
    )
    sun_exposure = RadioField(
        "חשיפה לשמש יומית",
        choices=[
            ("minimal", "מינימלית"),
            ("moderate", "בינונית"),
            ("high", "גבוהה"),
        ],
        validators=[DataRequired()],
    )
    makeup_frequency = RadioField(
        "תדירות איפור",
        choices=[
            ("daily", "כמעט יומי"),
            ("sometimes", "לפעמים"),
            ("rare", "נדיר / אין"),
        ],
        validators=[DataRequired()],
    )
    spf_habit = RadioField(
        "שימוש ב-SPF",
        choices=[
            ("always", "תמיד בבוקר"),
            ("sometimes", "לפעמים"),
            ("rarely", "לעיתים רחוקות"),
        ],
        validators=[DataRequired()],
    )
    exfoliation = RadioField(
        "אקספוליאציה (פילינג) היום",
        choices=[
            ("never", "לא משתמשת"),
            ("1_2", "1–2 בשבוע"),
            ("3_plus", "3+ בשבוע"),
        ],
        validators=[DataRequired()],
    )
    retinol = RadioField(
        "ניסיון עם רטינול / רטינואיד",
        choices=[
            ("none", "אין ניסיון"),
            ("beginner", "מתחילה / מדי פעם"),
            ("regular", "שימוש קבוע"),
        ],
        validators=[DataRequired()],
    )
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
    uses_actives = BooleanField("משתמשת כיום בחומצות / ויטמין סי / רטינול באופן קבוע")
    notes = TextAreaField("הערות נוספות (אופציונלי)", validators=[Optional()])
    submit = SubmitField("שליחה ויצירת שגרה מותאמת")


def _init_form_choices(form: SkinQuestionnaireForm) -> None:
    form.skin_type.choices = _choices_skin()
    form.concerns.choices = _concerns()
    form.sensitivities.choices = _sens()
    form.goals.choices = _goals()


def _answers_to_dict(form: SkinQuestionnaireForm) -> dict:
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


def _summary_label(answers: dict) -> str:
    st = answers.get("skin_type", "")
    mapping = dict(_choices_skin()[1:])
    skin_he = mapping.get(st, st)
    concerns = answers.get("concerns") or []
    cm = dict(_concerns())
    cs = " · ".join([cm.get(c, c) for c in concerns[:3]])
    if len(concerns) > 3:
        cs += "…"
    return f"{skin_he} — {cs or 'ללא ציון חששות'}"


@questionnaire_bp.route("/questionnaire", methods=["GET", "POST"])
@login_required
def show_questionnaire():
    form = SkinQuestionnaireForm()
    _init_form_choices(form)

    if form.validate_on_submit():
        answers = _answers_to_dict(form)
        prof = SkinProfile.query.filter_by(user_id=current_user.id).first()
        if prof is None:
            prof = SkinProfile(user_id=current_user.id)
            db.session.add(prof)
        prof.set_answers(answers)
        prof.summary_label = _summary_label(answers)

        m_text, e_text, used_ai = generate_routine(answers)
        r = Routine.query.filter_by(user_id=current_user.id).first()
        if r is None:
            r = Routine(user_id=current_user.id)
            db.session.add(r)
        r.morning_text = m_text
        r.evening_text = e_text
        r.used_openai = used_ai
        db.session.commit()
        flash("השאלון נשמר ונוצרה שגרה מותאמת אישית.", "success")
        return redirect(url_for("questionnaire.view_routine"))

    return render_template("questionnaire/form.html", form=form)


@questionnaire_bp.route("/routine", methods=["GET"])
@login_required
def view_routine():
    r = Routine.query.filter_by(user_id=current_user.id).first()
    prof = SkinProfile.query.filter_by(user_id=current_user.id).first()
    if not r or not prof:
        flash("עדיין לא מולא שאלון — נא למלא את השאלון.", "warning")
        return redirect(url_for("questionnaire.show_questionnaire"))
    return render_template(
        "questionnaire/routine.html",
        routine=r,
        profile=prof,
        answers=prof.get_answers(),
    )
