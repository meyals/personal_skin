"""
=============================================================================
קובץ: extensions.py
שייך ל: צד שרת (Server-Side)
=============================================================================
תפקיד הקובץ:
    קובץ זה מגדיר את הרכיבים הגלובליים (אובייקטים משותפים) שכל שאר הקבצים
    בפרויקט משתמשים בהם. הוא נוצר בנפרד כדי למנוע בעיות של ייבוא מעגלי
    (circular imports) — כלומר מצב שבו קובץ A מייבא מ-B ו-B מייבא מ-A.

רכיבים שמוגדרים כאן:
    1. db (SQLAlchemy) — אובייקט ה-ORM שמחבר את Python למסד הנתונים.
       כל המודלים (טבלאות) ב-models.py יורשים ממנו (db.Model).
       דרכו גם מבצעים שאילתות (db.session.query) ושמירות (db.session.commit).

    2. login_manager (Flask-Login) — מנהל את מערכת ההתחברות של המשתמשים.
       הוא אחראי על:
       - שמירת מזהה המשתמש בעוגיית הסשן (cookie) בדפדפן
       - טעינת המשתמש מה-DB בכל בקשה (דרך user_loader ב-__init__.py)
       - הפניה אוטומטית לדף התחברות אם מנסים לגשת לדף מוגן

איך זה עובד:
    1. הקובץ הזה רק *יוצר* את האובייקטים (בלי לחבר לאפליקציה)
    2. ב-app/__init__.py (פונקציית create_app) קוראים ל:
       - db.init_app(app)           → מחבר את ה-ORM לאפליקציית Flask
       - login_manager.init_app(app) → מחבר את ניהול ההתחברות לאפליקציה
    זה נקרא "Factory Pattern" — יצירה נפרדת מאתחול.
=============================================================================
"""
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

# ─── אובייקט ORM (Object Relational Mapper) ─────────────────────────────────
# SQLAlchemy הוא הגשר בין Python למסד הנתונים.
# במקום לכתוב SQL ידנית כמו:  SELECT * FROM users WHERE email='...'
# אנחנו כותבים Python:        User.query.filter_by(email='...').first()
# כל מודל (טבלה) ב-models.py יורש מ-db.Model
db = SQLAlchemy()

# ─── מנהל התחברות (Session Management) ────────────────────────────────────────
# Flask-Login שומר את מזהה המשתמש בעוגייה (cookie) מוצפנת בדפדפן.
# בכל בקשת HTTP, הוא טוען את המשתמש מה-DB באמצעות הפונקציה user_loader
# שמוגדרת ב-__init__.py.
login_manager = LoginManager()

# login_view: אם משתמש לא מחובר מנסה לגשת לדף שדורש @login_required,
# Flask-Login מפנה אותו אוטומטית לדף ההתחברות (auth.login)
login_manager.login_view = "auth.login"

# ההודעה שתוצג למשתמש כשהוא מופנה לדף ההתחברות
login_manager.login_message = "יש להתחבר כדי לגשת לדף זה."
