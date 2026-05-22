"""
=============================================================================
קובץ: utils.py
שייך ל: צד שרת (Server-Side)
=============================================================================
תפקיד הקובץ:
    פונקציות עזר (Utilities) שמשמשות חלקים שונים באפליקציה.
    כרגע הקובץ כולל פונקציה אחת עיקרית: render_markdown_safe —
    המרת טקסט Markdown ל-HTML בטוח לתצוגה בדפדפן.

מה זה Markdown?
    Markdown הוא שפת סימון פשוטה שממירים ל-HTML:
    - ## כותרת      → <h2>כותרת</h2>
    - **מודגש**     → <b>מודגש</b>
    - - פריט ברשימה → <li>פריט ברשימה</li>

מה זה XSS ולמה צריך bleach?
    XSS = Cross-Site Scripting — התקפה שבה תוקף מחדיר קוד JavaScript
    דרך שדה טקסט. לדוגמה, אם משתמש כותב בשאלון:
        <script>alert('hacked')</script>
    בלי הגנה, הקוד הזה ירוץ בדפדפן של כל מי שצופה בדף!

    bleach.clean() מסיר תגיות HTML מסוכנות (כמו <script>) ומשאיר
    רק תגיות בטוחות (כמו <p>, <h1>, <ul>).

שימוש:
    הפונקציה נרשמת כפילטר Jinja2 ב-__init__.py:
        app.jinja_env.filters["markdown_safe"] = render_markdown_safe
    ואז בתבניות HTML:
        {{ routine.morning_text | markdown_safe }}
=============================================================================
"""
import bleach
import markdown
from markupsafe import Markup


def _allowed_tags():
    """מחזיר רשימת תגיות HTML מותרות לאחר סינון.

    bleach.clean() מסיר כל תגית HTML שלא ברשימה הזו.
    אנחנו מוסיפים תגיות שנדרשות לתצוגת Markdown:
    - p = פסקה
    - h1-h4 = כותרות
    - ul, ol, li = רשימות
    - pre, code = קוד
    - blockquote = ציטוט
    """
    base = set(bleach.sanitizer.ALLOWED_TAGS)
    base.update(
        {
            "p",
            "h1",
            "h2",
            "h3",
            "h4",
            "ul",
            "ol",
            "li",
            "pre",
            "code",
            "blockquote",
        }
    )
    return list(base)


def render_markdown_safe(text: str | None) -> Markup:
    """ממיר טקסט Markdown ל-HTML בטוח לתצוגה בדפדפן.

    שלבי העיבוד:
    1. markdown.markdown() — ממיר Markdown לקוד HTML גולמי
       לדוגמה: "## כותרת" → "<h2>כותרת</h2>"
       extensions:
       - nl2br = ממיר שבירת שורה (\n) ל-<br> (כמו בוואטסאפ)
       - sane_lists = רשימות חכמות יותר

    2. bleach.clean() — מסנן תגיות HTML מסוכנות
       משאיר רק תגיות מהרשימה המותרת (_allowed_tags)
       strip=True → מוחק לגמרי תגיות אסורות (לא רק מנטרל)

    3. Markup() — מסמן ל-Jinja2 ש-HTML הזה בטוח להצגה
       בלי זה, Jinja2 יציג את ה-HTML כטקסט רגיל (עם תגיות)

    Args:
        text: טקסט Markdown (או None/ריק)

    Returns:
        אובייקט Markup עם HTML בטוח ומסונן
    """
    if not text:
        return Markup("")
    # שלב 1: Markdown → HTML
    raw = markdown.markdown(
        text,
        extensions=["nl2br", "sane_lists"],
        output_format="html",
    )
    # שלב 2: סינון תגיות מסוכנות
    clean = bleach.clean(raw, tags=_allowed_tags(), strip=True)
    # שלב 3: סימון כ-HTML בטוח
    return Markup(clean)
