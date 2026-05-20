"""נקודת כניסה לייצור (Production) — Gunicorn / Render.

בפיתוח משתמשים ב-run.py; בשרת ענן Gunicorn טוען את האובייקט `app` מכאן.
משתנה FLASK_CONFIG=production מכבה מצב debug.
"""
import os

from app import create_app

app = create_app(os.getenv("FLASK_CONFIG", "production"))
