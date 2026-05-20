"""לקוח שורת פקודה לבדיקת שרת האימות — להדגמה בבחינה (מחשב שני).

דוגמה (שרת על 192.168.1.10):
    set AUTH_SOCKET_HOST=192.168.1.10
    py -3 socket_auth_client_demo.py ping
    py -3 socket_auth_client_demo.py register user@test.com MyPass1!
    py -3 socket_auth_client_demo.py login user@test.com MyPass1!
"""
from __future__ import annotations

import json
import sys

from app.socket_auth.client import auth_socket_request


def main() -> None:
    """בונה payload לפי argv ושולח לשרת הסוקטים."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    action = sys.argv[1].lower()
    payload: dict

    if action == "ping":
        payload = {"action": "ping"}
    elif action == "login" and len(sys.argv) >= 4:
        payload = {"action": "login", "email": sys.argv[2], "password": sys.argv[3]}
    elif action == "register" and len(sys.argv) >= 4:
        payload = {
            "action": "register",
            "email": sys.argv[2],
            "password": sys.argv[3],
            "first_name": sys.argv[4] if len(sys.argv) > 4 else "",
            "last_name": sys.argv[5] if len(sys.argv) > 5 else "",
        }
    elif action == "reset_password" and len(sys.argv) >= 4:
        payload = {"action": "reset_password", "email": sys.argv[2], "password": sys.argv[3]}
    else:
        print("שימוש: ping | login <email> <password> | register <email> <password> [first] [last]")
        sys.exit(1)

    response = auth_socket_request(payload)
    print(json.dumps(response, ensure_ascii=False, indent=2))
    sys.exit(0 if response.get("ok") else 1)


if __name__ == "__main__":
    main()
