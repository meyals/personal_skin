"""מודלים — Users, פרופיל עור, שגרה, שיתופים בקהילה."""
import json
import uuid
from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


def _utcnow():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)
    last_login = db.Column(db.DateTime)

    skin_profile = db.relationship("SkinProfile", backref="user", uselist=False, cascade="all, delete-orphan")
    routine = db.relationship("Routine", backref="user", uselist=False, cascade="all, delete-orphan")
    routine_versions = db.relationship(
        "RoutineVersion",
        backref="user",
        lazy="dynamic",
        cascade="all, delete-orphan",
        order_by="RoutineVersion.version_number.desc()",
    )
    shares = db.relationship("CommunityShare", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    share_reactions = db.relationship("CommunityReaction", backref="user", lazy="dynamic", cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class SkinProfile(db.Model):
    """תשובות השאלון + סיכום טקסטואלי לתצוגה."""

    __tablename__ = "skin_profiles"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, unique=True)
    # JSON: כל שדות השאלון (מבנה קבוע בקוד הטפסים)
    questionnaire_json = db.Column(db.Text, nullable=False, default="{}")
    # טקסט קצר לתצוגה בקהילה
    summary_label = db.Column(db.String(200))
    updated_at = db.Column(db.DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    def get_answers(self) -> dict:
        try:
            return json.loads(self.questionnaire_json or "{}")
        except json.JSONDecodeError:
            return {}

    def set_answers(self, data: dict) -> None:
        self.questionnaire_json = json.dumps(data, ensure_ascii=False)


class Routine(db.Model):
    """שגרת בוקר/ערב — טקסט מפורט (נוצר ע\"י AI או גיבוי כללי)."""

    __tablename__ = "routines"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, unique=True)
    morning_text = db.Column(db.Text, nullable=False, default="")
    evening_text = db.Column(db.Text, nullable=False, default="")
    generated_at = db.Column(db.DateTime, default=_utcnow, nullable=False)
    used_openai = db.Column(db.Boolean, default=False)


class CommunityShare(db.Model):
    """פוסט ציבורי — פרופיל ושגרה (עותק טקסט בזמן השיתוף)."""

    __tablename__ = "community_shares"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    display_name = db.Column(db.String(120), nullable=False)
    profile_summary = db.Column(db.Text, nullable=False)
    morning_routine = db.Column(db.Text, nullable=False)
    evening_routine = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)
    reactions = db.relationship("CommunityReaction", backref="share", lazy="dynamic", cascade="all, delete-orphan")


class CommunityReaction(db.Model):
    """תגובת לייק/דיסלייק של משתמש על שיתוף בקהילה."""

    __tablename__ = "community_reactions"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    share_id = db.Column(db.String(36), db.ForeignKey("community_shares.id"), nullable=False, index=True)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    # 1=like, -1=dislike
    value = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("share_id", "user_id", name="uq_share_user_reaction"),
    )


class RoutineVersion(db.Model):
    """היסטוריית גרסאות שגרה לכל משתמש."""

    __tablename__ = "routine_versions"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    version_number = db.Column(db.Integer, nullable=False)
    morning_text = db.Column(db.Text, nullable=False, default="")
    evening_text = db.Column(db.Text, nullable=False, default="")
    generated_at = db.Column(db.DateTime, default=_utcnow, nullable=False)
    used_openai = db.Column(db.Boolean, default=False)
    answers_json = db.Column(db.Text, nullable=False, default="{}")

    def set_answers(self, data: dict) -> None:
        self.answers_json = json.dumps(data, ensure_ascii=False)
