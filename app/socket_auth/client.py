"""
=============================================================================
קובץ: socket_auth/client.py
שייך ל: צד לקוח (Client-Side) — לקוח TCP
=============================================================================
תפקיד הקובץ:
    לקוח TCP שפותח חיבור לשרת האימות ושולח בקשות login/register/reset.

    מי משתמש בלקוח הזה?
    1. Flask (auth/routes.py) — כשמשתמש מנסה להתחבר/להירשם דרך האתר
    2. socket_auth_client_demo.py — תוכנית שורת פקודה להדגמה בבחינה

    ב-Flask הזרימה היא:
    [דפדפן] → HTTP POST → [Flask] → auth_socket_request() → TCP → [שרת אימות]

    הפונקציה הראשית: auth_socket_request(payload)
    - פותח חיבור TCP חדש לשרת האימות
    - שולח מילון JSON (בקשה)
    - מקבל מילון JSON (תשובה)
    - סוגר את החיבור
    - אם יש שגיאה (שרת לא זמין, timeout) — מחזיר מילון עם ok=False

    הערה: כל בקשה פותחת חיבור חדש וסוגרת אותו. אין connection pool.
=============================================================================
"""
from __future__ import annotations

import os
import socket
from typing import Any

from app.socket_auth.protocol import recv_message, send_message

# ─── ברירות מחדל ─────────────────────────────────────────────────────────────
DEFAULT_HOST = "127.0.0.1"   # localhost — אותו מחשב
DEFAULT_PORT = 5050           # הפורט שעליו שרת האימות מאזין
CONNECT_TIMEOUT_SEC = 10     # זמן מקסימלי לחכות לחיבור (שניות)


def auth_socket_config() -> tuple[str, int]:
    """קורא את כתובת ופורט שרת האימות ממשתני סביבה.

    משתני סביבה:
    - AUTH_SOCKET_HOST → כתובת IP של שרת האימות (ברירת מחדל: 127.0.0.1)
    - AUTH_SOCKET_PORT → פורט (ברירת מחדל: 5050)

    Returns:
        tuple של (host, port) — למשל ("127.0.0.1", 5050)
    """
    host = (os.environ.get("AUTH_SOCKET_HOST") or DEFAULT_HOST).strip()
    port = int(os.environ.get("AUTH_SOCKET_PORT") or DEFAULT_PORT)
    return host, port


def auth_socket_request(payload: dict[str, Any]) -> dict[str, Any]:
    """שולח בקשת אימות לשרת TCP ומחזיר את התשובה.

    זרימת העבודה:
    1. יצירת socket TCP (AF_INET = IPv4, SOCK_STREAM = TCP)
    2. הגדרת timeout (כדי לא לחכות לנצח אם השרת לא עונה)
    3. חיבור לשרת (connect)
    4. שליחת בקשה כ-JSON (send_message)
    5. קבלת תשובה כ-JSON (recv_message)
    6. סגירת החיבור (finally → תמיד נסגר, גם אם יש שגיאה)

    טיפול בשגיאות:
    - TimeoutError → השרת לא הגיב בזמן
    - ConnectionRefusedError → השרת לא רץ (לא הפעילו run_auth_server.py)
    - OSError → שגיאת רשת כללית

    Args:
        payload: מילון בקשה, למשל:
                 {"action": "login", "email": "a@b.com", "password": "MyPass1!"}

    Returns:
        מילון תשובה מהשרת, למשל:
        - הצלחה: {"ok": true, "user": {"user_id": "abc", "email": "a@b.com"}}
        - כישלון: {"ok": false, "error": "invalid_credentials", "message": "..."}
        - שגיאת חיבור: {"ok": false, "error": "connection_refused", "message": "..."}
    """
    host, port = auth_socket_config()

    # יצירת socket TCP
    # AF_INET = IPv4 (כתובת IP רגילה)
    # SOCK_STREAM = TCP (חיבור אמין, מסודר)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(CONNECT_TIMEOUT_SEC)

    try:
        # חיבור לשרת (TCP 3-way handshake מתבצע כאן)
        sock.connect((host, port))

        # שליחת בקשה וקבלת תשובה (דרך protocol.py)
        send_message(sock, payload)
        return recv_message(sock)

    except (TimeoutError, socket.timeout):
        return {
            "ok": False,
            "error": "socket_timeout",
            "message": f"שרת האימות לא זמין ב-{host}:{port}. הריצי קודם: py -3 run_auth_server.py",
        }
    except ConnectionRefusedError:
        return {
            "ok": False,
            "error": "connection_refused",
            "message": f"לא ניתן להתחבר לשרת האימות ב-{host}:{port}. הריצי קודם: py -3 run_auth_server.py",
        }
    except OSError as exc:
        return {
            "ok": False,
            "error": "socket_error",
            "message": f"שגיאת רשת: {exc}",
        }
    finally:
        # finally = נקודת ניקוי — תמיד סוגרים את ה-socket, גם אם הייתה שגיאה
        sock.close()
