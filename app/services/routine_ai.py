"""
=============================================================================
קובץ: services/routine_ai.py
שייך ל: צד שרת (Server-Side)
=============================================================================
תפקיד הקובץ:
    יצירת שגרת טיפוח מותאמת אישית על בסיס תשובות השאלון.
    הקובץ תומך בשתי שיטות:

    1. OpenAI (בינה מלאכותית):
       - אם יש מפתח API (משתנה סביבה OPENAI_API_KEY)
       - שולח את תשובות המשתמש כ-prompt ל-GPT
       - מקבל שגרה מותאמת ומפורטת

    2. Fallback (גיבוי לוקאלי):
       - אם אין מפתח API (או שקרתה שגיאה)
       - בונה שגרה לפי כללי אצבע פשוטים שכתובים בקוד
       - מבטיח שהמשתמש תמיד מקבל תוצאה (גם בלי AI)

    למה שני מנגנונים?
    - OpenAI עולה כסף ודורש חיבור אינטרנט
    - בפיתוח לא תמיד יש מפתח API
    - חווית משתמש: עדיף שגרה בסיסית מאשר הודעת שגיאה

הפונקציה הראשית: generate_routine(answers)
    קלט: מילון תשובות מהשאלון
    פלט: (טקסט_בוקר, טקסט_ערב, האם_AI)
=============================================================================
"""
from __future__ import annotations

import os
from typing import Any

# ─── ניסיון לייבא את ה-SDK של OpenAI ────────────────────────────────────────
# אם החבילה לא מותקנת → OpenAI = None → נשתמש בגיבוי בלבד
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore


# =============================================================================
# מנגנון גיבוי (Fallback) — שגרה לוקאלית ללא AI
# =============================================================================
def _build_fallback_routine(answers: dict[str, Any]) -> tuple[str, str, bool]:
    """בונה שגרת ברירת מחדל לוקאלית (ללא OpenAI).

    הפונקציה מייצרת טקסט Markdown לשגרת בוקר וערב לפי כללים פשוטים:
    - אם העור יבש → ממליצים על לחות
    - אם יש פצעונים → ממליצים על ניאצינאמיד
    - אם יש רגישות לבשמים → ממליצים על מוצרים ללא בשמים
    - וכו'

    Args:
        answers: מילון תשובות מהשאלון

    Returns:
        tuple של (טקסט_בוקר, טקסט_ערב, False)
        False = לא נוצר עם AI
    """
    skin = answers.get("skin_type") or "normal"
    concerns = answers.get("concerns") or []
    sens = answers.get("sensitivities") or []
    budget = answers.get("budget") or "medium"
    avoid_fragrance = "fragrance" in sens

    # בניית משפט פתיחה מותאם
    intro = f"סוג עור שנבחר: {skin}. מטרות: {', '.join(concerns) if concerns else 'כלליות'}."
    if avoid_fragrance:
        intro += " מומלץ להעדיף מוצרים ללא בשמים."

    # ─── שגרת בוקר (Markdown) ────────────────────────────────────────────
    morning = f"""## שגרת בוקר

{intro}

1. **ניקוי עדין** — קצף/ג׳ל ניקוי מתאים לעור {skin}. עיסוי קצר במים פושרים, שטיפה.
2. **טונר (אופציונלי)** — אם העור צמא למים או אחרי ניקוי מתיחה.
3. **סרום** — לפי חששות: """

    # התאמת סרום לפי בעיות העור
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

    # ─── שגרת ערב (Markdown) ─────────────────────────────────────────────
    evening = f"""## שגרת ערב

1. **הסרת איפור / ניקוי כפול** — אם יש איפור: שמן ניקוי או מיסלר, ואז ניקוי מים.
2. **ניקוי** — אותו מנקה כמו בבוקר (או מנקה עדין יותר בערב אם העור רגיש).
3. **טיפול ממוקד** — """

    # התאמת טיפול ממוקד לפי בעיות
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


# =============================================================================
# הפונקציה הראשית — יצירת שגרה (AI או Fallback)
# =============================================================================
def generate_routine(answers: dict[str, Any]) -> tuple[str, str, bool]:
    """יוצר שגרת טיפוח מותאמת אישית.

    סדר העבודה:
    1. בדיקה: האם יש מפתח API ו-SDK מותקן?
       - אם לא → חזרה ל-fallback (מנגנון גיבוי)
    2. בניית prompt (הנחיה) מתשובות המשתמש
    3. שליחה ל-OpenAI GPT
    4. ניסיון לפצל את התשובה לבוקר/ערב
    5. בכל תקלה → חזרה ל-fallback

    Args:
        answers: מילון תשובות מהשאלון (skin_type, concerns, budget...)

    Returns:
        tuple: (טקסט_בוקר, טקסט_ערב, האם_נוצר_עם_AI)
        - טקסט_בוקר: מחרוזת Markdown עם שגרת הבוקר
        - טקסט_ערב: מחרוזת Markdown עם שגרת הערב
        - האם_נוצר_עם_AI: True אם נוצר עם OpenAI, False אם fallback
    """
    # בדיקה: האם אפשר להשתמש ב-AI?
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key or OpenAI is None:
        return _build_fallback_routine(answers)

    # ─── בניית prompt ────────────────────────────────────────────────────
    client = OpenAI(api_key=api_key)
    payload = _format_answers_for_prompt(answers)

    # System prompt = הנחיה כללית ל-AI (מי הוא, באיזו שפה לענות, מה הפורמט)
    system = (
        "אתה יועץ קוסמטולוגיה להסבר כללי בלבד. אינך מחליף רופא או רוקח. "
        "השב בעברית בלבד. פורמט ברור עם כותרות markdown קצרות, רשימות ממוספרות, "
        "ציון סוגי מוצרים (לא מותגים ספציפיים) ושלבים לבוקר ולערב בנפרד."
    )

    # User prompt = הנתונים הספציפיים של המשתמש + דרישות
    user_msg = f"""לפי נתוני המשתמש הבאים, בנה שגרת טיפוח מפורטת:

{payload}

דרישות:
- חלק "בוקר" וחלק "ערב" — כל אחד עם שלבים ממוספרים, חומרים (סוג מוצר), והנחיות קצרות.
- התחשבות בתקציב, רגישויות, הריון אם צוין, ושימוש ב-SPF בבוקר.
- אם יש ניגוד בין מטרות — עדיפות לבטיחות ולעדינות.
"""

    # ─── שליחה ל-OpenAI ──────────────────────────────────────────────────
    try:
        resp = client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),  # מודל ברירת מחדל
            messages=[
                {"role": "system", "content": system},   # הנחיות כלליות
                {"role": "user", "content": user_msg},    # נתוני המשתמש
            ],
            temperature=0.5,  # 0=מדויק, 1=יצירתי. 0.5 = איזון
        )
        text = (resp.choices[0].message.content or "").strip()

        # ניסיון לפצל את התשובה לבוקר/ערב
        morning, evening = _split_morning_evening(text)
        if not morning or not evening:
            return _build_fallback_routine(answers)  # פיצול נכשל → fallback
        return morning, evening, True  # True = נוצר עם AI

    except Exception:
        # כל שגיאה (רשת, API, JSON...) → חזרה ל-fallback
        return _build_fallback_routine(answers)


# =============================================================================
# פונקציות עזר
# =============================================================================

def _format_answers_for_prompt(a: dict[str, Any]) -> str:
    """ממיר מילון תשובות לפורמט טקסט שמתאים לשילוב ב-prompt של AI.

    למשל:
        - skin_type: dry
        - concerns: ['acne', 'dryness']
        - budget: medium
    """
    lines = []
    for k, v in a.items():
        lines.append(f"- {k}: {v}")
    return "\n".join(lines)


def _split_morning_evening(text: str) -> tuple[str, str]:
    """מפצל תשובה חופשית מ-AI לשני חלקים: בוקר וערב.

    AI מחזיר טקסט אחד ארוך. הפונקציה מנסה לפצל אותו:
    1. מחפשת כותרות markdown (##) עם מילות "בוקר" / "ערב"
    2. מחלקת את הטקסט לשני חלקים

    אם לא נמצאה חלוקה ברורה — חותך באמצע (fallback פשוט).
    """
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

    # fallback: חצי על חצי (לא אידיאלי, אבל עדיף מכלום)
    mid = len(text) // 2
    return text[:mid].strip(), text[mid:].strip()
