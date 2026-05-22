"""
=============================================================================
קובץ: socket_auth/server.py
שייך ל: צד שרת (Server-Side) — שרת אימות TCP
=============================================================================
תפקיד הקובץ:
    שרת TCP שמאזין לחיבורים ומטפל בבקשות אימות (login/register/reset).
    זהו "צד השרת" בארכיטקטורת שרת-לקוח של מערכת האימות.

    הרצה:
    - בפיתוח: py -3 run_auth_server.py (טרמינל נפרד מ-Flask)
    - בייצור (Render): wsgi.py מפעיל אותו אוטומטית ב-thread ברקע

    ארכיטקטורה:
    ┌─────────────────────────────────────────────────┐
    │ run_auth_socket_server()                        │
    │   bind(0.0.0.0:5050)  → מאזין מכל כתובת       │
    │   listen(32)          → תור של עד 32 חיבורים   │
    │   while True:                                   │
    │     accept()          → מקבל חיבור חדש         │
    │     Thread → _handle_client()  → thread נפרד    │
    │       recv_message()   → קורא JSON מהלקוח      │
    │       handle_auth_request() → לוגיקה + DB      │
    │       send_message()   → שולח תשובה JSON       │
    │       close()          → סוגר חיבור            │
    └─────────────────────────────────────────────────┘

    כל לקוח מטופל ב-thread נפרד כדי שהשרת יוכל לטפל
    במספר חיבורים במקביל (concurrency).

    Thread = daemon:
    - daemon=True → ה-thread נסגר אוטומטית כשהתוכנית הראשית נסגרת
    - אם היה False, ה-threads היו ממשיכים לרוץ גם אחרי Ctrl+C
=============================================================================
"""
from __future__ import annotations

import os
import socket
from threading import Thread

from flask import Flask

from app.socket_auth.handlers import handle_auth_request
from app.socket_auth.protocol import recv_message, send_message

# ─── ברירות מחדל ─────────────────────────────────────────────────────────────
DEFAULT_BIND_HOST = "0.0.0.0"  # מאזין מכל ממשק רשת (גם ממחשב אחר ברשת)
DEFAULT_PORT = 5050            # פורט ברירת מחדל


def _server_bind_config() -> tuple[str, int]:
    """קורא כתובת ופורט להאזנה ממשתני סביבה.

    משתני סביבה:
    - AUTH_SOCKET_BIND_HOST → מאיזו כתובת להאזין (ברירת מחדל: 0.0.0.0 = הכל)
    - AUTH_SOCKET_PORT → פורט (ברירת מחדל: 5050)

    Returns:
        tuple של (host, port)
    """
    host = (os.environ.get("AUTH_SOCKET_BIND_HOST") or DEFAULT_BIND_HOST).strip()
    port = int(os.environ.get("AUTH_SOCKET_PORT") or DEFAULT_PORT)
    return host, port


def _handle_client(connection: socket.socket, address: tuple[str, int], app: Flask) -> None:
    """מטפל בלקוח יחיד — רץ ב-thread נפרד.

    זרימה:
    1. קריאת הודעת JSON מהלקוח (recv_message)
    2. ניתוב לפונקציה המתאימה (handle_auth_request)
    3. שליחת תשובת JSON חזרה ללקוח (send_message)
    4. סגירת החיבור (בקשה אחת לחיבור)

    app.app_context():
        נדרש כי SQLAlchemy עובד רק בתוך "הקשר אפליקציה" (app context).
        ה-thread הזה רץ מחוץ ל-request של Flask, אז צריך ליצור הקשר ידנית.

    Args:
        connection: אובייקט socket של הלקוח המחובר
        address: (IP, port) של הלקוח — לצורכי לוג
        app: אובייקט Flask — נדרש לגישה ל-DB
    """
    peer = f"{address[0]}:{address[1]}"  # כתובת הלקוח לתצוגה בלוגים
    try:
        with app.app_context():
            while True:
                # ─── קריאת בקשה ─────────────────────────────────────────
                try:
                    request = recv_message(connection)
                except (ConnectionError, ValueError, OSError):
                    break  # הלקוח ניתק או שלח הודעה לא תקינה

                # ─── עיבוד הבקשה ────────────────────────────────────────
                try:
                    response = handle_auth_request(request)
                except Exception:
                    app.logger.exception("Socket auth handler failed from %s", peer)
                    response = {
                        "ok": False,
                        "error": "server_error",
                        "message": "שגיאה פנימית בשרת האימות",
                    }

                # ─── שליחת תשובה ────────────────────────────────────────
                try:
                    send_message(connection, response)
                except OSError:
                    break  # הלקוח ניתק

                break  # לקוח Flask סוגר אחרי תשובה אחת (one-shot)
    finally:
        # תמיד סוגרים את החיבור — גם אם הייתה שגיאה
        connection.close()


def run_auth_socket_server(app: Flask) -> None:
    """לולאה ראשית של שרת האימות — bind → listen → accept → thread.

    שלבים:
    1. יצירת socket TCP
    2. SO_REUSEADDR — מאפשר להפעיל מחדש מיד אחרי סגירה (ללא "Address in use")
    3. bind — קישור לכתובת ופורט
    4. listen — התחלת האזנה (תור של עד 32 חיבורים ממתינים)
    5. לולאת accept — מחכה לחיבור חדש ומפעילה thread לטפל בו

    הלולאה חוסמת (blocking) עד Ctrl+C.

    Args:
        app: אובייקט Flask — מועבר ל-threads לגישה ל-DB
    """
    bind_host, port = _server_bind_config()

    # יצירת socket TCP
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # SO_REUSEADDR = מאפשר לעשות bind מיד אחרי שהשרת נסגר
    # בלי זה, צריך לחכות כמה דקות עד שהמערכת משחררת את הפורט
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # bind = קישור ה-socket לכתובת IP ופורט ספציפיים
    server.bind((bind_host, port))

    # listen = התחלת האזנה. 32 = כמה חיבורים יכולים לחכות בתור
    server.listen(32)

    print(f"[Auth Socket Server] מאזין על TCP {bind_host}:{port} (SOCK_STREAM)")
    print("פעולות נתמכות: login, register, reset_password, ping")

    try:
        while True:
            # accept = חוסם עד שמגיע חיבור חדש
            # מחזיר: (socket חדש ללקוח, כתובת הלקוח)
            conn, addr = server.accept()

            # יצירת thread חדש לטיפול בלקוח (לא חוסם את הלולאה)
            worker = Thread(
                target=_handle_client,
                args=(conn, addr, app),
                daemon=True,  # נסגר אוטומטית עם התהליך הראשי
                name=f"auth-socket-{addr[0]}:{addr[1]}",
            )
            worker.start()
    except KeyboardInterrupt:
        print("\n[Auth Socket Server] עוצר...")
    finally:
        server.close()
