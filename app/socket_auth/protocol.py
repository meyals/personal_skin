"""
=============================================================================
קובץ: socket_auth/protocol.py
שייך ל: משותף לשרת וללקוח (Server + Client)
=============================================================================
תפקיד הקובץ:
    מגדיר את פרוטוקול התקשורת (Communication Protocol) בין הלקוח לשרת.
    פרוטוקול = כללים שמגדירים איך שני צדדים מדברים זה עם זה.

    הבעיה: TCP הוא פרוטוקול "זרם" (stream) — הוא לא מבדיל בין הודעות.
    אם שולחים "Hello" ואז "World", הצד השני עלול לקבל "HelloWorld" ביחד
    או "Hel" ו-"loWorld" בנפרד. אין גבולות הודעה!

    הפתרון: Length-Prefixed Protocol (פרוטוקול עם כותרת אורך)
    כל הודעה מורכבת משני חלקים:
    ┌──────────────────┬───────────────────────────────────────┐
    │ 4 בתים: אורך    │ גוף ההודעה: JSON בקידוד UTF-8       │
    │ (big-endian)     │                                       │
    └──────────────────┴───────────────────────────────────────┘

    דוגמה:
    - בקשה: {"action": "login", "email": "a@b.com", "password": "MyPass1!"}
    - תשובה: {"ok": true, "user": {"user_id": "abc-123", "email": "a@b.com"}}

    הגנה:
    - MAX_MESSAGE_BYTES = 64KB — מגבלת גודל הודעה (מונע התקפות)
    - בדיקה שהגוף הוא מילון JSON (לא מערך או מחרוזת)

פונקציות:
    send_message(sock, payload) → שולח מילון JSON לצד השני
    recv_message(sock) → מקבל מילון JSON מהצד השני
    _recv_exact(sock, size) → קורא בדיוק N בתים (עוזר ל-recv_message)
=============================================================================
"""
from __future__ import annotations

import json
import socket
import struct
from typing import Any

# ─── מגבלת גודל הודעה ────────────────────────────────────────────────────────
# 64KB = 65,536 בתים — מספיק לכל בקשת/תשובת JSON רגילה
# מונע התקפות שבהן שולחים הודעות ענק כדי לצרוך זיכרון
MAX_MESSAGE_BYTES = 64 * 1024


def _recv_exact(sock: socket.socket, size: int) -> bytes:
    """קורא בדיוק `size` בתים מהסוקט.

    למה צריך פונקציה מיוחדת?
    כי sock.recv(size) עלול להחזיר פחות בתים ממה שביקשנו!
    TCP יכול לפצל הודעה למספר חלקים. הפונקציה הזו ממתינה
    עד שמתקבלים כל הבתים הדרושים.

    Args:
        sock: אובייקט socket (חיבור TCP פתוח)
        size: כמה בתים לקרוא

    Returns:
        bytes באורך בדיוק size

    Raises:
        ConnectionError: אם החיבור נסגר לפני שהתקבלו כל הבתים
    """
    chunks: list[bytes] = []
    received = 0
    while received < size:
        part = sock.recv(size - received)
        if not part:
            raise ConnectionError("החיבור נסגר לפני שקיבלנו את כל ההודעה")
        chunks.append(part)
        received += len(part)
    return b"".join(chunks)


def send_message(sock: socket.socket, payload: dict[str, Any]) -> None:
    """שולח מילון JSON לצד השני של חיבור TCP.

    שלבים:
    1. ממיר מילון Python → מחרוזת JSON → בתים (UTF-8)
    2. בודק שהגודל לא חורג מהמגבלה
    3. בונה כותרת אורך (4 בתים, big-endian)
    4. שולח כותרת + גוף ביחד

    struct.pack(">I", length):
    - ">" = big-endian (הבית הגדול ראשון)
    - "I" = unsigned int (4 בתים, 0 עד 4 מיליארד)

    Args:
        sock: חיבור TCP פתוח
        payload: מילון Python לשליחה
    """
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    if len(data) > MAX_MESSAGE_BYTES:
        raise ValueError("ההודעה גדולה מדי")
    # שולחים [4 בתים אורך] + [גוף ההודעה]
    sock.sendall(struct.pack(">I", len(data)) + data)


def recv_message(sock: socket.socket) -> dict[str, Any]:
    """מקבל הודעת JSON מחיבור TCP ומחזיר מילון Python.

    שלבים:
    1. קורא 4 בתים ראשונים = אורך הגוף
    2. בודק שהאורך תקין (לא 0, לא גדול מדי)
    3. קורא את הגוף (JSON כבתים)
    4. ממיר בתים → מחרוזת UTF-8 → מילון Python
    5. בודק שהתוצאה היא מילון (dict), לא מערך או מחרוזת

    Args:
        sock: חיבור TCP פתוח

    Returns:
        מילון Python עם תוכן ההודעה
    """
    # שלב 1: קריאת כותרת אורך
    header = _recv_exact(sock, 4)
    length = struct.unpack(">I", header)[0]

    # שלב 2: בדיקת תקינות
    if length == 0 or length > MAX_MESSAGE_BYTES:
        raise ValueError("גודל הודעה לא חוקי")

    # שלב 3-4: קריאה והמרה
    body = _recv_exact(sock, length)
    parsed = json.loads(body.decode("utf-8"))

    # שלב 5: וידוא שזה מילון
    if not isinstance(parsed, dict):
        raise ValueError("ההודעה חייבת להיות אובייקט JSON")
    return parsed
