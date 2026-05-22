"""
=============================================================================
קובץ: run_auth_server.py
שייך ל: צד שרת (Server-Side) — הפעלת שרת אימות TCP בפיתוח
=============================================================================
תפקיד הקובץ:
    מפעיל את שרת האימות TCP (Socket Server) בטרמינל נפרד.
    נדרש בסביבת פיתוח בלבד — בייצור wsgi.py מטפל בזה אוטומטית.

    הרצה:
        py -3 run_auth_server.py

    השרת מאזין על פורט 5050 (ברירת מחדל) ומטפל בבקשות:
    - login (התחברות)
    - register (הרשמה)
    - reset_password (איפוס סיסמה)
    - ping (בדיקת חיים)

    משתני סביבה אופציונליים:
    - AUTH_SOCKET_BIND_HOST → מאיזו כתובת להאזין (ברירת מחדל: 0.0.0.0)
    - AUTH_SOCKET_PORT → פורט (ברירת מחדל: 5050)
=============================================================================
"""
import os

from app import create_app
from app.socket_auth.server import run_auth_socket_server

# ─── יצירת אפליקציית Flask (נדרש לגישה ל-DB דרך app context) ─────────────────
app = create_app(os.getenv("FLASK_CONFIG", "development"))

if __name__ == "__main__":
    # מפעיל את שרת האימות — חוסם עד Ctrl+C
    run_auth_socket_server(app)
