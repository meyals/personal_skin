"""
=============================================================================
קובץ: socket_auth_client_demo.py
שייך ל: צד לקוח (Client-Side) — לקוח שורת פקודה להדגמה
=============================================================================
תפקיד הקובץ:
    תוכנית שורת פקודה (CLI) לבדיקת שרת האימות TCP.
    מאפשרת לשלוח בקשות login/register/reset_password/ping
    ישירות משורת הפקודה — בלי דפדפן!

    שימוש עיקרי: הדגמה בבחינה (מחשב שני ברשת)

    דוגמאות הרצה:
        py -3 socket_auth_client_demo.py ping
        py -3 socket_auth_client_demo.py register user@test.com MyPass1!
        py -3 socket_auth_client_demo.py login user@test.com MyPass1!
        py -3 socket_auth_client_demo.py reset_password user@test.com NewPass1!

    חיבור לשרת על מחשב אחר:
        set AUTH_SOCKET_HOST=192.168.1.10
        py -3 socket_auth_client_demo.py ping

    הפונקציה main():
    1. קוראת את הפרמטרים מ-sys.argv (שורת הפקודה)
    2. בונה מילון JSON (payload) לפי הפעולה
    3. שולחת לשרת דרך auth_socket_request() (מ-client.py)
    4. מדפיסה את התשובה כ-JSON מעוצב
    5. מחזירה exit code 0 (הצלחה) או 1 (כישלון)
=============================================================================
"""
from __future__ import annotations

import json
import sys

from app.socket_auth.client import auth_socket_request


def main() -> None:
    """פונקציה ראשית — בונה payload לפי הפקודה בשורת הפקודה ושולחת לשרת.

    sys.argv = רשימת הפרמטרים שהוזנו בשורת הפקודה:
    - sys.argv[0] = שם הקובץ (socket_auth_client_demo.py)
    - sys.argv[1] = הפעולה (ping/login/register/reset_password)
    - sys.argv[2] = אימייל (אם רלוונטי)
    - sys.argv[3] = סיסמה (אם רלוונטי)
    - sys.argv[4] = שם פרטי (אופציונלי, רק ב-register)
    - sys.argv[5] = שם משפחה (אופציונלי, רק ב-register)
    """
    if len(sys.argv) < 2:
        print(__doc__)  # מדפיס את תיעוד הקובץ כהוראות שימוש
        sys.exit(1)

    action = sys.argv[1].lower()
    payload: dict

    # ─── בניית payload לפי הפעולה ─────────────────────────────────────────
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

    # ─── שליחה לשרת וקבלת תשובה ──────────────────────────────────────────
    response = auth_socket_request(payload)

    # הדפסת התשובה כ-JSON מעוצב (indent=2 = הזחה של 2 רווחים)
    print(json.dumps(response, ensure_ascii=False, indent=2))

    # exit code: 0 = הצלחה, 1 = כישלון
    sys.exit(0 if response.get("ok") else 1)


if __name__ == "__main__":
    main()
