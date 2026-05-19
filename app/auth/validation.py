"""ולידציית סיסמה — משותף לטפסי Flask ולשרת הסוקטים."""
from __future__ import annotations

import re


def password_strength_error(password: str) -> str | None:
    """מחזיר הודעת שגיאה בעברית או None אם הסיסמה תקינה."""
    value = password or ""
    if len(value) < 8:
        return "הסיסמה חייבת להכיל לפחות 8 תווים."
    if not re.search(r"[A-Za-z]", value):
        return "הסיסמה חייבת להכיל לפחות אות אחת באנגלית."
    if not re.search(r"\d", value):
        return "הסיסמה חייבת להכיל לפחות מספר אחד."
    if not re.search(r"[^A-Za-z0-9]", value):
        return "הסיסמה חייבת להכיל לפחות תו מיוחד אחד."
    return None
