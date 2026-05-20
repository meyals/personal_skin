"""לקוח TCP — שולח בקשות אימות לשרת הסוקטים (פורט 5050).

משמש את Flask (auth/routes.py) ואת socket_auth_client_demo.py להדגמה.
Flask הוא לקוח Web; ב-login/register הוא גם לקוח Socket.
"""
from __future__ import annotations

import os
import socket
from typing import Any

from app.socket_auth.protocol import recv_message, send_message

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5050
CONNECT_TIMEOUT_SEC = 10


def auth_socket_config() -> tuple[str, int]:
    """קורא כתובת ופורט שרת האימות ממשתני סביבה."""
    host = (os.environ.get("AUTH_SOCKET_HOST") or DEFAULT_HOST).strip()
    port = int(os.environ.get("AUTH_SOCKET_PORT") or DEFAULT_PORT)
    return host, port


def auth_socket_request(payload: dict[str, Any]) -> dict[str, Any]:
    """פותח חיבור TCP, שולח JSON, מקבל תשובה וסוגר.

    Args:
        payload: למשל {"action": "login", "email": "...", "password": "..."}

    Returns:
        מילון תשובה מהשרת, או dict עם ok=False אם החיבור נכשל.
    """
    host, port = auth_socket_config()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # TCP
    sock.settimeout(CONNECT_TIMEOUT_SEC)
    try:
        sock.connect((host, port))
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
        sock.close()
