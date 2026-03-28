"""
יצירת שגרת טיפוח — בינה מלאכותית (OpenAI) או גיבוי לפי כללים.
המלצות אינן תחליף לייעוץ רפואי.
"""
from __future__ import annotations

import os
from typing import Any

# ניסיון לייבא את ה-SDK; אם אין מפתח — נשתמש בגיבוי בלבד
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore


def _build_fallback_routine(answers: dict[str, Any]) -> tuple[str, str, bool]:
    """שגרה מובנית בעברית לפי תשובות (ללא API)."""
    skin = answers.get("skin_type") or "normal"
    concerns = answers.get("concerns") or []
    sens = answers.get("sensitivities") or []
    budget = answers.get("budget") or "medium"
    avoid_fragrance = "fragrance" in sens

    intro = f"סוג עור שנבחר: {skin}. מטרות: {', '.join(concerns) if concerns else 'כלליות'}."
    if avoid_fragrance:
        intro += " מומלץ להעדיף מוצרים ללא בשמים."

    morning = f"""## שגרת בוקר

{intro}

1. **ניקוי עדין** — קצף/ג׳ל ניקוי מתאים לעור {skin}. עיסוי קצר במים פושרים, שטיפה.
2. **טונר (אופציונלי)** — אם העור צמא למים או אחרי ניקוי מתיחה.
3. **סרום** — לפי חששות: """
    if "acne" in concerns:
        morning += "ניתן לשקול סרום עם ניאצינאמיד או חומצה אזלאית בהתאמה הדרגתית. "
    elif "dryness" in concerns:
        morning += "סרום היאלורוני או סרום לחות. "
    else:
        morning += "סרום לפי צורך (לחות/הבהרה). "

    morning += f"""
4. **קרם לחות** — שכבה לפי עובי שמתאימה לעור {skin} ולתקציב ({budget}).
5. **מקדים SPF** — קרם לחות עם SPF או שכבת קרם הגנה נפרדת (מינימום SPF 30), מריחה סבירה.

**טיפ:** המתנה דקה בין שכבות לספיגה טובה יותר.
"""

    evening = f"""## שגרת ערב

1. **הסרת איפור / ניקוי כפול** — אם יש איפור: שמן ניקוי או מיסלר, ואז ניקוי מים.
2. **ניקוי** — אותו מנקה כמו בבוקר (או מנקה עדין יותר בערב אם העור רגיש).
3. **טיפול ממוקד** — """
    if "wrinkles" in concerns or "hyperpigmentation" in concerns:
        evening += "בערב מתאימים לעיתים רטינואיד/מוצרים עם רטינול בהדרגה (לא בהריון/הנקה — יש להתייעץ). "
    elif "acne" in concerns:
        evening += "טיפול נקודתי או סרום לפצעונים לפי המלצת רוקח/רופא עור. "
    else:
        evening += "סרום לפי מטרה (לחות/הרגעה). "

    evening += f"""
4. **קרם לחות** — עשיר יותר מבבוקר אם העור יבש; שכבה דקה אם שמני.
5. **שפתיים / אזור עיניים** — לפי צורך.

**טיפ:** 2–3 פעמים בשבוע ניתן להוסיף אקספוליאציה עדינה *רק אם* העור אינו מגורה — לא באותו לילה כרטינול חזק.
"""
    return morning.strip(), evening.strip(), False


def generate_routine(answers: dict[str, Any]) -> tuple[str, str, bool]:
    """
    מחזיר: (טקסט בוקר, טקסט ערב, האם נוצר עם OpenAI).
    """
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key or OpenAI is None:
        return _build_fallback_routine(answers)

    client = OpenAI(api_key=api_key)
    payload = _format_answers_for_prompt(answers)
    system = (
        "אתה יועץ קוסמטולוגיה להסבר כללי בלבד. אינך מחליף רופא או רוקח. "
        "השב בעברית בלבד. פורמט ברור עם כותרות markdown קצרות, רשימות ממוספרות, "
        "ציון סוגי מוצרים (לא מותגים ספציפיים) ושלבים לבוקר ולערב בנפרד."
    )
    user_msg = f"""לפי נתוני המשתמש הבאים, בנה שגרת טיפוח מפורטת:

{payload}

דרישות:
- חלק "בוקר" וחלק "ערב" — כל אחד עם שלבים ממוספרים, חומרים (סוג מוצר), והנחיות קצרות.
- התחשבות בתקציב, רגישויות, הריון אם צוין, ושימוש ב-SPF בבוקר.
- אם יש ניגוד בין מטרות — עדיפות לבטיחות ולעדינות.
"""

    try:
        resp = client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.5,
        )
        text = (resp.choices[0].message.content or "").strip()
        morning, evening = _split_morning_evening(text)
        if not morning or not evening:
            return _build_fallback_routine(answers)
        return morning, evening, True
    except Exception:
        return _build_fallback_routine(answers)


def _format_answers_for_prompt(a: dict[str, Any]) -> str:
    lines = []
    for k, v in a.items():
        lines.append(f"- {k}: {v}")
    return "\n".join(lines)


def _split_morning_evening(text: str) -> tuple[str, str]:
    """מנסה לפצל תשובה אחת לשני חלקים."""
    lower = text.lower()
    if "##" in text or "בוקר" in text or "ערב" in text:
        parts = text.split("##")
        chunks = [p.strip() for p in parts if p.strip()]
        morning_bits = []
        evening_bits = []
        current = None
        for c in chunks:
            cl = c.lower()
            if "בוקר" in c[:80] or "morning" in cl[:80]:
                current = "m"
                morning_bits.append("## " + c if not c.startswith("##") else c)
            elif "ערב" in c[:80] or "evening" in cl[:80] or "לילה" in c[:40]:
                current = "e"
                evening_bits.append("## " + c if not c.startswith("##") else c)
            elif current == "m":
                morning_bits.append(c)
            elif current == "e":
                evening_bits.append(c)
        m = "\n\n".join(morning_bits).strip()
        e = "\n\n".join(evening_bits).strip()
        if m and e:
            return m, e
    # fallback: חצי על חצי
    mid = len(text) // 2
    return text[:mid].strip(), text[mid:].strip()
