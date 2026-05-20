"""שרת TCP לאימות — מאזין לחיבורים ומטפל ב-login/register/reset.

ארכיטקטורה:
- Process נפרד: run_auth_server.py
- TCP SOCK_STREAM (מעל IP)
- Thread נפרד לכל לקוח מחובר
- גישה ל-DB דרך Flask app context (ORM)
"""
from __future__ import annotations

import os
import socket
from threading import Thread

from flask import Flask

from app.socket_auth.handlers import handle_auth_request
from app.socket_auth.protocol import recv_message, send_message

DEFAULT_BIND_HOST = "0.0.0.0"  # מאזין מכל ממשק רשת (גם מחשב שני)
DEFAULT_PORT = 5050


def _server_bind_config() -> tuple[str, int]:
    """כתובת ופורט להאזנה — מ-env או ברירת מחדל."""
    host = (os.environ.get("AUTH_SOCKET_BIND_HOST") or DEFAULT_BIND_HOST).strip()
    port = int(os.environ.get("AUTH_SOCKET_PORT") or DEFAULT_PORT)
    return host, port


def _handle_client(connection: socket.socket, address: tuple[str, int], app: Flask) -> None:
    """מטפל בלקוח יחיד — רץ ב-thread נפרד.

    זרימה:
    1. קריאת JSON מהלקוח
    2. handle_auth_request — בדיקה מול DB
    3. שליחת תשובת JSON
    4. סגירת חיבור (בקשה אחת לחיבור)
    """
    peer = f"{address[0]}:{address[1]}"
    try:
        with app.app_context():  # נדרש לגישה ל-SQLAlchemy
            while True:
                try:
                    request = recv_message(connection)
                except (ConnectionError, ValueError, OSError):
                    break

                try:
                    response = handle_auth_request(request)
                except Exception:
                    app.logger.exception("Socket auth handler failed from %s", peer)
                    response = {
                        "ok": False,
                        "error": "server_error",
                        "message": "שגיאה פנימית בשרת האימות",
                    }

                try:
                    send_message(connection, response)
                except OSError:
                    break

                break  # לקוח Flask סוגר אחרי תשובה אחת
    finally:
        connection.close()


def run_auth_socket_server(app: Flask) -> None:
    """לולאה ראשית — bind, listen, accept, הפעלת thread לכל לקוח.

    חוסם עד Ctrl+C. מיועד לטרמינל נפרד מ-run.py.
    """
    bind_host, port = _server_bind_config()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((bind_host, port))
    server.listen(32)

    print(f"[Auth Socket Server] מאזין על TCP {bind_host}:{port} (SOCK_STREAM)")
    print("פעולות נתמכות: login, register, reset_password, ping")

    try:
        while True:
            conn, addr = server.accept()
            worker = Thread(
                target=_handle_client,
                args=(conn, addr, app),
                daemon=True,
                name=f"auth-socket-{addr[0]}:{addr[1]}",
            )
            worker.start()
    except KeyboardInterrupt:
        print("\n[Auth Socket Server] עוצר...")
    finally:
        server.close()
