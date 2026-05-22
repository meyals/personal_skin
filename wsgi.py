"""נקודת כניסה לייצור (Production) — Gunicorn / Render.

בפיתוח משתמשים ב-run.py; בשרת ענן Gunicorn טוען את האובייקט `app` מכאן.
משתנה FLASK_CONFIG=production מכבה מצב debug.

שרת האימות TCP (socket_auth) מופעל אוטומטית ב-thread רקע
כך שאין צורך בתהליך נפרד ב-Render.
"""
import os
import threading

from app import create_app
from app.socket_auth.server import run_auth_socket_server

app = create_app(os.getenv("FLASK_CONFIG", "production"))

def _start_auth_server():
    """מפעיל שרת אימות TCP — מתעלם אם הפורט כבר תפוס (worker נוסף)."""
    try:
        run_auth_socket_server(app)
    except OSError as e:
        print(f"[wsgi] Auth socket server not started (port busy?): {e}")

# הפעלת שרת אימות TCP ברקע — daemon thread נסגר עם התהליך הראשי
_auth_thread = threading.Thread(
    target=_start_auth_server,
    daemon=True,
    name="auth-socket-server",
)
_auth_thread.start()

