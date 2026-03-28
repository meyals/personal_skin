"""דף קהילה — צפייה בשיתופים ושיתוף פרופיל ושגרה."""
from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length

from app.extensions import db
from app.models import CommunityShare, Routine, SkinProfile

community_bp = Blueprint("community", __name__, url_prefix="")


class ShareForm(FlaskForm):
    display_name = StringField(
        "שם לתצוגה בקהילה",
        validators=[DataRequired(), Length(min=2, max=80)],
    )
    submit = SubmitField("פרסמי את השיתוף")


@community_bp.route("/community")
def community_feed():
    shares = (
        CommunityShare.query.order_by(CommunityShare.created_at.desc()).limit(50).all()
    )
    form = None
    if current_user.is_authenticated:
        form = ShareForm()
    return render_template("community/feed.html", shares=shares, form=form)


@community_bp.route("/community/share", methods=["POST"])
@login_required
def share_post():
    form = ShareForm()
    if not form.validate_on_submit():
        for err in form.display_name.errors:
            flash(err, "danger")
        return redirect(url_for("community.community_feed"))

    prof = SkinProfile.query.filter_by(user_id=current_user.id).first()
    r = Routine.query.filter_by(user_id=current_user.id).first()
    if not prof or not r:
        flash("יש למלא שאלון וליצור שגרה לפני שיתוף.", "warning")
        return redirect(url_for("questionnaire.show_questionnaire"))

    answers = prof.get_answers()
    profile_text = prof.summary_label or ""
    # פירוט קצר לתצוגה
    lines = [f"**פרופיל:** {profile_text}", ""]
    lines.append("**פרטים מהשאלון:**")
    for key in sorted(answers.keys()):
        lines.append(f"- {key}: {answers[key]}")
    profile_block = "\n".join(lines)

    post = CommunityShare(
        user_id=current_user.id,
        display_name=form.display_name.data.strip(),
        profile_summary=profile_block,
        morning_routine=r.morning_text,
        evening_routine=r.evening_text,
    )
    db.session.add(post)
    db.session.commit()
    flash("השיתוף פורסם בהצלחה.", "success")
    return redirect(url_for("community.community_feed"))
