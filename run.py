"""נקודת כניסה להרצת השרת — פיתוח."""
import os

from app import create_app

app = create_app(os.getenv("FLASK_CONFIG", "development"))

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
