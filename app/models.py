"""
=============================================================================
קובץ: models.py
שייך ל: צד שרת (Server-Side)
=============================================================================
תפקיד הקובץ:
    קובץ זה מגדיר את כל הטבלאות במסד הנתונים בצורת מחלקות Python (ORM).
    כל מחלקה כאן מייצגת טבלה אחת במסד הנתונים, וכל שדה (attribute)
    מייצג עמודה בטבלה.

    SQLAlchemy ORM ממיר בין עולם ה-Python לעולם ה-SQL:
    - מחלקה = טבלה
    - אובייקט (instance) = שורה בטבלה
    - שדה (db.Column) = עמודה בטבלה
    - db.relationship = קשר בין טבלאות (JOIN ב-SQL)

טבלאות שמוגדרות כאן:
    1. User — משתמש רשום (אימייל, סיסמה מוצפנת, שם, תאריכים)
    2. SkinProfile — פרופיל עור של משתמש (תשובות השאלון כ-JSON)
    3. Routine — שגרת טיפוח נוכחית (טקסט בוקר + ערב)
    4. RoutineVersion — היסטוריית גרסאות שגרה (כל שליחת שאלון שומרת גרסה)
    5. CommunityShare — פוסט שהמשתמש שיתף בקהילה
    6. CommunityReaction — לייק או דיסלייק על פוסט בקהילה

קשרים בין הטבלאות (ERD — Entity Relationship Diagram):
    User ──1:1──> SkinProfile   (לכל משתמש פרופיל עור אחד)
    User ──1:1──> Routine       (לכל משתמש שגרה נוכחית אחת)
    User ──1:N──> RoutineVersion (לכל משתמש הרבה גרסאות שגרה)
    User ──1:N──> CommunityShare (משתמש יכול לפרסם הרבה שיתופים)
    User ──1:N──> CommunityReaction (משתמש יכול לסמן לייק על הרבה פוסטים)
    CommunityShare ──1:N──> CommunityReaction (לכל פוסט הרבה תגובות)
=============================================================================
"""
import json
import uuid
from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


def _utcnow():
    """מחזיר את הזמן הנוכחי באזור זמן UTC (זמן אוניברסלי).

    משמש כברירת מחדל לשדות created_at / updated_at בכל הטבלאות.
    UTC = זמן אחיד לכל העולם, לא תלוי באזור הזמן של השרת.
    """
    return datetime.now(timezone.utc)


# =============================================================================
# טבלה 1: User — משתמשים רשומים במערכת
# =============================================================================
class User(UserMixin, db.Model):
    """טבלת משתמשים — הטבלה המרכזית במערכת.

    UserMixin:
        מחלקה מ-Flask-Login שמוסיפה אוטומטית מתודות שנדרשות לניהול סשנים:
        - is_authenticated → האם המשתמש מחובר? (תמיד True למשתמש שנטען מה-DB)
        - is_active → האם החשבון פעיל?
        - get_id() → מחזיר את ה-ID כ-string (Flask-Login שומר אותו בעוגייה)

    db.Model:
        מחלקת בסיס של SQLAlchemy. כל מחלקה שיורשת ממנו הופכת לטבלה במסד.

    שדות (עמודות):
        id            → מזהה ייחודי (UUID — מחרוזת אקראית של 36 תווים)
        email         → אימייל — ייחודי, משמש להתחברות
        password_hash → הסיסמה מוצפנת (hash) — לא ניתן לשחזר את המקור!
        first_name    → שם פרטי (אופציונלי)
        last_name     → שם משפחה (אופציונלי)
        created_at    → מתי נוצר החשבון
        last_login    → מתי התחבר לאחרונה
    """

    # שם הטבלה במסד הנתונים (SQL)
    __tablename__ = "users"

    # ─── עמודות (Columns) ────────────────────────────────────────────────────
    # primary_key=True → מזהה ייחודי לכל שורה (כמו תעודת זהות)
    # default=lambda: str(uuid.uuid4()) → יוצר מזהה אקראי אוטומטית
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # unique=True → לא יכולים להיות שני משתמשים עם אותו אימייל
    # nullable=False → חובה למלא (לא יכול להיות ריק)
    # index=True → יוצר אינדקס ב-DB לחיפוש מהיר
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)

    # הסיסמה נשמרת כ-hash (הצפנה חד-כיוונית) — אף אחד לא יכול לראות את הסיסמה המקורית
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)
    last_login = db.Column(db.DateTime)

    # ─── קשרים לטבלאות אחרות (Relationships) ─────────────────────────────────
    # db.relationship = קשר וירטואלי (לא עמודה ב-SQL, אלא קיצור דרך ב-Python)
    # backref="user" → מאפשר גישה הפוכה, למשל: profile.user → מחזיר את המשתמש
    # uselist=False → קשר 1:1 (לא רשימה, אובייקט אחד בלבד)
    # cascade="all, delete-orphan" → מחיקת משתמש מוחקת אוטומטית גם את הנתונים שלו
    skin_profile = db.relationship("SkinProfile", backref="user", uselist=False, cascade="all, delete-orphan")
    routine = db.relationship("Routine", backref="user", uselist=False, cascade="all, delete-orphan")

    # lazy="dynamic" → לא טוען הכל מראש, מאפשר שאילתות נוספות (למשל סינון)
    routine_versions = db.relationship(
        "RoutineVersion",
        backref="user",
        lazy="dynamic",
        cascade="all, delete-orphan",
        order_by="RoutineVersion.version_number.desc()",  # מהחדש לישן
    )
    shares = db.relationship("CommunityShare", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    share_reactions = db.relationship("CommunityReaction", backref="user", lazy="dynamic", cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        """שומר סיסמה חדשה — ממיר אותה ל-hash חד-כיווני (Werkzeug).

        Hash = הצפנה שלא ניתן להפוך:
        - "MyPass1!" → "scrypt:32768:8:1$abc123$..."
        - אי אפשר לחזור מה-hash לסיסמה המקורית
        - כל פעם שמפעילים hash על אותה סיסמה, יוצא ערך אחר (בגלל salt)
        """
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """בודק אם הסיסמה שהמשתמש הקליד תואמת ל-hash שנשמר ב-DB.

        Werkzeug יודע להשוות סיסמה ל-hash בלי לדעת את הסיסמה המקורית.
        מחזיר True אם תואם, False אם לא.
        """
        return check_password_hash(self.password_hash, password)


# =============================================================================
# טבלה 2: SkinProfile — פרופיל עור (תשובות השאלון)
# =============================================================================
class SkinProfile(db.Model):
    """פרופיל עור — שומר את כל תשובות השאלון של המשתמש.

    התשובות נשמרות כ-JSON (מחרוזת טקסט) בעמודה אחת, במקום עמודה נפרדת
    לכל שאלה. זה מאפשר להוסיף שאלות חדשות בלי לשנות את מבנה הטבלה.

    שדות:
        id                  → מזהה ייחודי
        user_id             → מפתח זר — מצביע למשתמש בטבלת users
        questionnaire_json  → כל התשובות כ-JSON (למשל: {"skin_type": "dry", ...})
        summary_label       → סיכום קצר בעברית (למשל: "יבש — פצעונים · יובש")
        updated_at          → מתי עודכן לאחרונה
    """

    __tablename__ = "skin_profiles"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # db.ForeignKey("users.id") = מפתח זר → אומר שהערך בעמודה הזו חייב להתאים ל-id בטבלת users
    # unique=True → כל משתמש יכול להיות רק פרופיל אחד (קשר 1:1)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, unique=True)

    # db.Text = טקסט ארוך (ללא הגבלת אורך), בניגוד ל-db.String שמוגבל
    questionnaire_json = db.Column(db.Text, nullable=False, default="{}")
    summary_label = db.Column(db.String(200))

    # onupdate=_utcnow → מתעדכן אוטומטית בכל פעם שמשנים את השורה
    updated_at = db.Column(db.DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    def get_answers(self) -> dict:
        """ממיר את ה-JSON שנשמר ב-DB למילון Python רגיל.

        JSON = פורמט טקסט סטנדרטי לייצוג נתונים: '{"key": "value"}'
        json.loads = ממיר מ-JSON (מחרוזת) לאובייקט Python (מילון)
        """
        try:
            return json.loads(self.questionnaire_json or "{}")
        except json.JSONDecodeError:
            return {}

    def set_answers(self, data: dict) -> None:
        """שומר מילון Python כ-JSON במסד הנתונים.

        json.dumps = ממיר ממילון Python למחרוזת JSON
        ensure_ascii=False → מאפשר שמירת עברית כמו שהיא (לא קודים)
        """
        self.questionnaire_json = json.dumps(data, ensure_ascii=False)


# =============================================================================
# טבלה 3: Routine — שגרת הטיפוח הנוכחית
# =============================================================================
class Routine(db.Model):
    """שגרת טיפוח נוכחית — בוקר וערב.

    הטקסט נשמר בפורמט Markdown (סימני ## לכותרות, ** להדגשה, - לרשימות).
    בתצוגה בדפדפן, ה-Markdown ממיר ל-HTML דרך הפילטר markdown_safe.

    שדות:
        morning_text  → שגרת בוקר (טקסט Markdown)
        evening_text  → שגרת ערב (טקסט Markdown)
        generated_at  → מתי נוצרה השגרה
        used_openai   → האם נוצרה באמצעות בינה מלאכותית (True) או מנגנון גיבוי (False)
    """

    __tablename__ = "routines"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, unique=True)
    morning_text = db.Column(db.Text, nullable=False, default="")
    evening_text = db.Column(db.Text, nullable=False, default="")
    generated_at = db.Column(db.DateTime, default=_utcnow, nullable=False)
    used_openai = db.Column(db.Boolean, default=False)


# =============================================================================
# טבלה 4: CommunityShare — פוסטים בקהילה
# =============================================================================
class CommunityShare(db.Model):
    """פוסט בקהילה — צילום מצב (snapshot) של פרופיל ושגרה בזמן הפרסום.

    למה snapshot ולא קישור חי לנתונים?
    כי המשתמש עלול לעדכן את השגרה שלו אחרי הפרסום,
    ואנחנו רוצים שהפוסט בקהילה יישאר כפי שהיה ברגע הפרסום.

    שדות:
        display_name     → שם תצוגה שהמשתמש בחר (לא חייב להיות השם האמיתי)
        profile_summary  → סיכום פרופיל העור
        morning_routine  → שגרת בוקר (עותק מ-Routine)
        evening_routine  → שגרת ערב (עותק מ-Routine)
        reactions        → קשר לתגובות (לייקים/דיסלייקים) על הפוסט
    """

    __tablename__ = "community_shares"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    display_name = db.Column(db.String(120), nullable=False)
    profile_summary = db.Column(db.Text, nullable=False)
    morning_routine = db.Column(db.Text, nullable=False)
    evening_routine = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)
    reactions = db.relationship("CommunityReaction", backref="share", lazy="dynamic", cascade="all, delete-orphan")


# =============================================================================
# טבלה 5: CommunityReaction — לייקים ודיסלייקים
# =============================================================================
class CommunityReaction(db.Model):
    """תגובה על פוסט בקהילה — לייק (+1) או דיסלייק (-1).

    UniqueConstraint("share_id", "user_id"):
        אילוץ ייחודיות — משתמש יכול לסמן רק תגובה אחת על כל פוסט.
        אם מנסה לסמן שוב — מעדכנים או מוחקים (toggle).

    שדות:
        share_id  → מפתח זר → לאיזה פוסט התגובה שייכת
        user_id   → מפתח זר → מי סימן את התגובה
        value     → 1 = לייק, -1 = דיסלייק
    """

    __tablename__ = "community_reactions"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    share_id = db.Column(db.String(36), db.ForeignKey("community_shares.id"), nullable=False, index=True)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    value = db.Column(db.Integer, nullable=False)  # 1=like, -1=dislike
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    # אילוץ ייחודיות — מונע מאותו משתמש לסמן פעמיים על אותו פוסט
    __table_args__ = (
        db.UniqueConstraint("share_id", "user_id", name="uq_share_user_reaction"),
    )


# =============================================================================
# טבלה 6: RoutineVersion — היסטוריית גרסאות שגרה
# =============================================================================
class RoutineVersion(db.Model):
    """גרסה היסטורית של שגרת טיפוח.

    כל פעם שמשתמש שולח את השאלון מחדש, נוצרת גרסה חדשה.
    זה מאפשר לראות את ההיסטוריה ולהשוות בין גרסאות.

    שדות:
        version_number  → מספר הגרסה (1, 2, 3, ...)
        morning_text    → שגרת בוקר של הגרסה
        evening_text    → שגרת ערב של הגרסה
        used_openai     → האם נוצר עם AI
        answers_json    → צילום מצב של תשובות השאלון ברגע יצירת הגרסה
    """

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
        """שומר snapshot (צילום מצב) של תשובות השאלון לגרסה זו."""
        self.answers_json = json.dumps(data, ensure_ascii=False)
