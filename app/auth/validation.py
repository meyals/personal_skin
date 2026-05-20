"""ולידציית חוזק סיסמה — משותף לטפסי Flask ולשרת הסוקטים.

כללים: מינימום 8 תווים, אות באנגלית, ספרה, תו מיוחד.
"""
from __future__ import annotations

import re


def password_strength_error(password: str) -> str | None:
    """בודק חוזק סיסמה.

    Returns:
        הודעת שגיאה בעברית אם לא תקין, או None אם תקין.
    """
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
