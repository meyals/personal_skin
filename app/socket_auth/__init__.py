"""
=============================================================================
קובץ: socket_auth/__init__.py
שייך ל: צד שרת (Server-Side) + צד לקוח (Client-Side)
=============================================================================
תפקיד הקובץ:
    קובץ __init__.py הופך את התיקייה socket_auth/ לחבילה (package).

    התיקייה socket_auth/ מממשת תקשורת שרת-לקוח מבוססת TCP Sockets:
    - server.py   → שרת TCP שמאזין לחיבורים ומטפל בבקשות אימות (Server-Side)
    - client.py   → לקוח TCP ש-Flask משתמש בו לשלוח בקשות לשרת (Client-Side)
    - protocol.py → פרוטוקול ההודעות: כיצד שולחים ומקבלים JSON מעל TCP (משותף)
    - handlers.py → הלוגיקה העסקית: login, register, reset_password (Server-Side)

    ארכיטקטורה:
    [Flask Web Server] ──TCP──> [Auth Socket Server]
         (client.py)                (server.py + handlers.py)
              ↕                          ↕
    protocol.py (פרוטוקול משותף)      [מסד נתונים]
=============================================================================
"""
