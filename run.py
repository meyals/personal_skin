"""נקודת כניסה להרצת שרת ה-Web (Flask) — פיתוח.

חובה להריץ גם שרת אימות TCP בטרמינל נפרד:
    py -3 run_auth_server.py
"""
import os

from app import create_app

app = create_app(os.getenv("FLASK_CONFIG", "development"))

if __name__ == "__main__":
    # 0.0.0.0 — מאפשר גישה ממחשב אחר ברשת (להדגמה בבחינה)
    web_host = os.getenv("FLASK_RUN_HOST", "0.0.0.0")
    web_port = int(os.getenv("FLASK_RUN_PORT", "5000"))
    app.run(debug=True, host=web_host, port=web_port)
