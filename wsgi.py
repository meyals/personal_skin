"""
=============================================================================
קובץ: wsgi.py
שייך ל: צד שרת (Server-Side) — נקודת כניסה לייצור (Production)
=============================================================================
תפקיד הקובץ:
    נקודת כניסה לסביבת ייצור (Render / שרת ענן).
    Gunicorn (שרת WSGI מקצועי) טוען את האובייקט `app` מהקובץ הזה.

    ההבדל מ-run.py:
    - run.py = פיתוח (debug, שרת Flask מובנה)
    - wsgi.py = ייצור (Gunicorn, ללא debug)

    שרת אימות TCP:
    בפיתוח מריצים את שרת האימות בטרמינל נפרד (run_auth_server.py).
    בייצור (Render) — שרת האימות רץ כשירות worker נפרד (ראו render.yaml).

    WSGI = Web Server Gateway Interface:
    תקן שמגדיר איך שרת web (כמו Gunicorn) מתקשר עם אפליקציית Python.
    Gunicorn קורא ל-app ומעביר לו בקשות HTTP.
=============================================================================
"""
import os
#import threading

from app import create_app
#from app.socket_auth.server import run_auth_socket_server

# ─── יצירת אפליקציית Flask במצב ייצור ────────────────────────────────────────
app = create_app(os.getenv("FLASK_CONFIG", "production"))


# def _start_auth_server():
#     """מפעיל את שרת האימות TCP ברקע.
#
#     מתעלם מ-OSError אם הפורט כבר תפוס (למשל ב-Gunicorn עם מספר workers).
#     כל worker מנסה להפעיל את שרת האימות, אבל רק הראשון מצליח.
#     """
#     try:
#         run_auth_socket_server(app)
#     except OSError as e:
#         print(f"[wsgi] Auth socket server not started (port busy?): {e}")
#
#
# # ─── הפעלת שרת אימות TCP ב-thread ברקע ───────────────────────────────────────
# # daemon=True → ה-thread נסגר אוטומטית כשהתהליך הראשי נסגר
# _auth_thread = threading.Thread(
#     target=_start_auth_server,
#     daemon=True,
#     name="auth-socket-server",
# )
# _auth_thread.start()
