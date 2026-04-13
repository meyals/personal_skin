"""דף קהילה — צפייה בשיתופים ושיתוף פרופיל ושגרה."""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from sqlalchemy import case, func
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length

from app.extensions import db
from app.models import CommunityReaction, CommunityShare, Routine, SkinProfile
from app.services.audit_logger import log_audit_event

community_bp = Blueprint("community", __name__, url_prefix="")


class ShareForm(FlaskForm):
    display_name = StringField(
        "שם לתצוגה בקהילה",
        validators=[DataRequired(), Length(min=2, max=80)],
    )
    submit = SubmitField("פרסמי את השיתוף")


class ReactionForm(FlaskForm):
    submit = SubmitField("שלחי תגובה")


@community_bp.route("/community")
def community_feed():
    shares = CommunityShare.query.order_by(CommunityShare.created_at.desc()).all()
    share_ids = [s.id for s in shares]
    reactions_map: dict[str, dict[str, int]] = {}
    user_reactions: dict[str, int] = {}

    if share_ids:
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
        if current_user.is_authenticated:
            user_rows = CommunityReaction.query.filter(
                CommunityReaction.share_id.in_(share_ids),
                CommunityReaction.user_id == current_user.id,
            ).all()
            user_reactions = {r.share_id: r.value for r in user_rows}

    form = None
    reaction_form = None
    if current_user.is_authenticated:
        form = ShareForm()
        reaction_form = ReactionForm()
    return render_template(
        "community/feed.html",
        shares=shares,
        form=form,
        reaction_form=reaction_form,
        reactions_map=reactions_map,
        user_reactions=user_reactions,
    )


@community_bp.route("/community/share", methods=["POST"])
@login_required
def share_post():
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
    form = ReactionForm()
    if not form.validate_on_submit():
        flash("לא ניתן לעדכן תגובה כרגע. נסי שוב.", "danger")
        return redirect(url_for("community.community_feed"))

    value = 1 if action == "like" else -1 if action == "dislike" else 0
    if value == 0:
        flash("סוג תגובה לא חוקי.", "danger")
        return redirect(url_for("community.community_feed"))

    share = CommunityShare.query.filter_by(id=share_id).first()
    if share is None:
        flash("השיתוף לא נמצא.", "warning")
        return redirect(url_for("community.community_feed"))

    reaction = CommunityReaction.query.filter_by(share_id=share_id, user_id=current_user.id).first()
    if reaction is None:
        reaction = CommunityReaction(share_id=share_id, user_id=current_user.id, value=value)
        db.session.add(reaction)
        state = "created"
    elif reaction.value == value:
        db.session.delete(reaction)
        state = "removed"
    else:
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
    return redirect(request.referrer or url_for("community.community_feed"))
