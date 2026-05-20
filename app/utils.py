"""עזרי תצוגה — המרת Markdown ל-HTML בטוח.

משמש להצגת שגרות טיפוח ותוכן קהילה בדפדפן.
הגנה מ-XSS: רק תגיות HTML מותרות נשארות אחרי סינון bleach.
"""
import bleach
import markdown
from markupsafe import Markup


def _allowed_tags():
    """רשימת תגיות HTML מותרות אחרי סינון (מעבר לברירת מחדל של bleach)."""
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
    """ממיר Markdown ל-HTML ומסנן תגיות מסוכנות.

    שלבים:
    1. Markdown → HTML גולמי
    2. bleach.clean — מסיר script ותגיות לא מורשות
    3. Markup — מסמן ל-Jinja שה-HTML בטוח להצגה

    נקרא מהתבניות: {{ routine.morning_text | markdown_safe }}
    """
    if not text:
        return Markup("")
    raw = markdown.markdown(
        text,
        extensions=["nl2br", "sane_lists"],
        output_format="html",
    )
    clean = bleach.clean(raw, tags=_allowed_tags(), strip=True)
    return Markup(clean)
