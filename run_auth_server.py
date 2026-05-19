"""הפעלת שרת אימות מבוסס TCP sockets (login / register / reset_password).

הרצה (טרמינל נפרד מהאתר):
    py -3 run_auth_server.py

משתני סביבה (אופציונלי):
    AUTH_SOCKET_BIND_HOST=0.0.0.0   — מאיזה כתובת להאזין (ברירת מחדל: כל הרשת)
    AUTH_SOCKET_PORT=5050
"""
import os

from app import create_app
from app.socket_auth.server import run_auth_socket_server

app = create_app(os.getenv("FLASK_CONFIG", "development"))

if __name__ == "__main__":
    run_auth_socket_server(app)
