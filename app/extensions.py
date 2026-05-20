"""רכיבים גלובליים המשותפים לכל המודולים.

- db: חיבור ORM למסד הנתונים (SQLite מקומי / PostgreSQL בייצור).
- login_manager: ניהול סשן משתמש (Flask-Login) אחרי התחברות מוצלחת.
"""
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

# אובייקט ORM — מודלים ב-models.py יורשים מ-db.Model
db = SQLAlchemy()

# מנהל התחברות — טוען משתמש מ-DB לפי מזהה בסשן (cookie)
login_manager = LoginManager()
login_manager.login_view = "auth.login"  # לאן להפנות אם לא מחוברים
login_manager.login_message = "יש להתחבר כדי לגשת לדף זה."
