"""
=============================================================================
קובץ: community/routes.py
שייך ל: צד שרת (Server-Side)
=============================================================================
תפקיד הקובץ:
    ראוטים (Routes) לפיצ'ר הקהילה — מאפשר למשתמשים לשתף את פרופיל
    העור והשגרה שלהם, ולהגיב (לייק/דיסלייק) על שיתופים של אחרים.

    ראוטים שמוגדרים כאן:
    1. /community                              → צפייה בפיד (GET)
    2. /community/share                        → פרסום שיתוף חדש (POST)
    3. /community/react/<share_id>/<action>    → לייק/דיסלייק (POST)

מבנה הפיצ'ר:
    - כל משתמש מחובר יכול לפרסם שיתוף (snapshot של הפרופיל והשגרה)
    - כל משתמש מחובר יכול לסמן לייק או דיסלייק על כל שיתוף
    - משתמש לא מחובר יכול רק לצפות (קריאה בלבד)
    - לייק/דיסלייק עובד כ-toggle: לחיצה שנייה מבטלת

טפסים:
    - ShareForm    → טופס עם שם תצוגה לפרסום שיתוף
    - ReactionForm → טופס מינימלי (רק CSRF) לכפתורי לייק/דיסלייק
=============================================================================
"""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from sqlalchemy import case, func
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length

from app.extensions import db
from app.models import CommunityReaction, CommunityShare, Routine, SkinProfile
from app.services.audit_logger import log_audit_event

# ─── יצירת Blueprint לקהילה ──────────────────────────────────────────────────
community_bp = Blueprint("community", __name__, url_prefix="")


# =============================================================================
# טפסים
# =============================================================================
class ShareForm(FlaskForm):
    """טופס פרסום שיתוף חדש בקהילה.

    המשתמש בוחר שם תצוגה (nickname) שיוצג ליד הפוסט.
    השם לא חייב להיות השם האמיתי — זו בחירה של המשתמש.
    """
    display_name = StringField(
        "שם לתצוגה בקהילה",
        validators=[DataRequired(), Length(min=2, max=80)],
    )
    submit = SubmitField("פרסמי את השיתוף")


class ReactionForm(FlaskForm):
    """טופס מינימלי לאימות CSRF בלחיצה על לייק/דיסלייק.

    הטופס לא מכיל שדות קלט — רק אסימון CSRF מוסתר (hidden_tag).
    זה מונע מאתר חיצוני לשלוח לייקים מזויפים בשם המשתמש.
    """
    submit = SubmitField("שלחי תגובה")


# =============================================================================
# ראוטים
# =============================================================================

@community_bp.route("/community")
def community_feed():
    """ראוט הפיד — /community — מציג את כל השיתופים של הקהילה.

    הפונקציה עושה כמה דברים:
    1. שולפת את כל השיתופים מה-DB (מהחדש לישן)
    2. מחשבת כמה לייקים/דיסלייקים לכל שיתוף (שאילתת ORM מרוכזת)
    3. אם המשתמש מחובר — בודקת מה הוא כבר סימן על כל שיתוף
    4. מעבירה הכל לתבנית HTML להצגה

    פתוח לכולם: גם משתמשים לא מחוברים יכולים לצפות.
    """
    # שלב 1: שליפת כל השיתופים מהחדש לישן
    shares = CommunityShare.query.order_by(CommunityShare.created_at.desc()).all()
    share_ids = [s.id for s in shares]

    # מילונים לתוצאות — ימולאו בשלב הבא
    reactions_map: dict[str, dict[str, int]] = {}  # {share_id: {likes: N, dislikes: N}}
    user_reactions: dict[str, int] = {}             # {share_id: 1 או -1}

    if share_ids:
        # ─── שלב 2: ספירת לייקים/דיסלייקים ──────────────────────────────
        # שאילתת ORM אחת יעילה (במקום לולאה שעושה שאילתה לכל פוסט)
        # func.sum + case = SQL aggregation — סופרים כמה פעמים value=1 וכמה value=-1
        rows = (
            db.session.query(
                CommunityReaction.share_id.label("share_id"),
                func.sum(case((CommunityReaction.value == 1, 1), else_=0)).label("likes"),
                func.sum(case((CommunityReaction.value == -1, 1), else_=0)).label("dislikes"),
            )
            .filter(CommunityReaction.share_id.in_(share_ids))
            .group_by(CommunityReaction.share_id)
            .all()
        )
        reactions_map = {
            row.share_id: {"likes": int(row.likes or 0), "dislikes": int(row.dislikes or 0)}
            for row in rows
        }

        # ─── שלב 3: מה המשתמש המחובר כבר סימן ──────────────────────────
        if current_user.is_authenticated:
            user_rows = CommunityReaction.query.filter(
                CommunityReaction.share_id.in_(share_ids),
                CommunityReaction.user_id == current_user.id,
            ).all()
            user_reactions = {r.share_id: r.value for r in user_rows}

    # ─── שלב 4: הכנת טפסים והעברה לתבנית ────────────────────────────────
    form = None
    reaction_form = None
    if current_user.is_authenticated:
        form = ShareForm()           # טופס פרסום שיתוף
        reaction_form = ReactionForm()  # טופס לייק/דיסלייק

    return render_template(
        "community/feed.html",
        shares=shares,                   # רשימת השיתופים
        form=form,                       # טופס פרסום (או None אם לא מחובר)
        reaction_form=reaction_form,     # טופס תגובה (או None)
        reactions_map=reactions_map,      # ספירת לייקים/דיסלייקים
        user_reactions=user_reactions,    # מה המשתמש כבר סימן
    )


@community_bp.route("/community/share", methods=["POST"])
@login_required  # חובה להיות מחובר כדי לפרסם
def share_post():
    """ראוט פרסום שיתוף — /community/share (POST בלבד)

    יוצר פוסט חדש בקהילה מתוך הנתונים האישיים של המשתמש.
    הפוסט הוא snapshot (צילום מצב) — לא קישור חי לנתונים.

    שלבים:
    1. ולידציה של שם התצוגה
    2. בדיקה שיש פרופיל ושגרה (אי אפשר לשתף בלי למלא שאלון)
    3. בניית טקסט סיכום מהתשובות
    4. שמירת הפוסט ב-DB
    5. רישום ב-audit log
    """
    form = ShareForm()
    if not form.validate_on_submit():
        log_audit_event(
            "community.share_failed",
            level="warning",
            user_id=current_user.id,
            reason="invalid_form",
        )
        for err in form.display_name.errors:
            flash(err, "danger")
        return redirect(url_for("community.community_feed"))

    # בדיקה שהמשתמש מילא שאלון ויש לו שגרה
    prof = SkinProfile.query.filter_by(user_id=current_user.id).first()
    r = Routine.query.filter_by(user_id=current_user.id).first()
    if not prof or not r:
        log_audit_event(
            "community.share_failed",
            level="warning",
            user_id=current_user.id,
            reason="missing_profile_or_routine",
        )
        flash("יש למלא שאלון וליצור שגרה לפני שיתוף.", "warning")
        return redirect(url_for("questionnaire.show_questionnaire"))

    # בניית טקסט סיכום מתשובות השאלון
    answers = prof.get_answers()
    profile_text = prof.summary_label or ""
    lines = [f"**פרופיל:** {profile_text}", ""]
    lines.append("**פרטים מהשאלון:**")
    for key in sorted(answers.keys()):
        lines.append(f"- {key}: {answers[key]}")
    profile_block = "\n".join(lines)

    # יצירת הפוסט — snapshot של הנתונים הנוכחיים
    post = CommunityShare(
        user_id=current_user.id,
        display_name=form.display_name.data.strip(),
        profile_summary=profile_block,
        morning_routine=r.morning_text,  # עותק (לא קישור)
        evening_routine=r.evening_text,  # עותק (לא קישור)
    )
    db.session.add(post)
    db.session.commit()

    log_audit_event(
        "community.share_success",
        user_id=current_user.id,
        share_id=post.id,
        display_name=post.display_name,
    )
    flash("השיתוף פורסם בהצלחה.", "success")
    return redirect(url_for("community.community_feed"))


@community_bp.route("/community/react/<share_id>/<action>", methods=["POST"])
@login_required
def react_to_share(share_id: str, action: str):
    """ראוט תגובה (לייק/דיסלייק) — /community/react/<share_id>/<action>

    לוגיקת Toggle (מתג):
    - אם המשתמש עוד לא הגיב → יוצר תגובה חדשה
    - אם המשתמש לוחץ על אותה תגובה שוב → מבטל (מוחק)
    - אם המשתמש לוחץ על תגובה שונה → מעדכן (מלייק לדיסלייק או להפך)

    Args:
        share_id: מזהה הפוסט שעליו מגיבים
        action: "like" או "dislike"
    """
    form = ReactionForm()
    if not form.validate_on_submit():
        flash("לא ניתן לעדכן תגובה כרגע. נסי שוב.", "danger")
        return redirect(url_for("community.community_feed"))

    # המרת action לערך מספרי: like=1, dislike=-1
    value = 1 if action == "like" else -1 if action == "dislike" else 0
    if value == 0:
        flash("סוג תגובה לא חוקי.", "danger")
        return redirect(url_for("community.community_feed"))

    # בדיקה שהפוסט קיים
    share = CommunityShare.query.filter_by(id=share_id).first()
    if share is None:
        flash("השיתוף לא נמצא.", "warning")
        return redirect(url_for("community.community_feed"))

    # ─── לוגיקת Toggle ──────────────────────────────────────────────────
    reaction = CommunityReaction.query.filter_by(share_id=share_id, user_id=current_user.id).first()

    if reaction is None:
        # תגובה ראשונה — יוצרים חדשה
        reaction = CommunityReaction(share_id=share_id, user_id=current_user.id, value=value)
        db.session.add(reaction)
        state = "created"
    elif reaction.value == value:
        # אותה תגובה שוב — מבטלים (מוחקים)
        db.session.delete(reaction)
        state = "removed"
    else:
        # תגובה שונה — מעדכנים (למשל: מלייק לדיסלייק)
        reaction.value = value
        state = "updated"

    db.session.commit()

    log_audit_event(
        "community.reaction_changed",
        user_id=current_user.id,
        share_id=share_id,
        action=action,
        state=state,
    )
    # חזרה לדף שממנו הגענו (או לפיד)
    return redirect(request.referrer or url_for("community.community_feed"))
