"""עזרי תצוגה — Markdown בטוח ל-HTML."""
import bleach
import markdown
from markupsafe import Markup


def _allowed_tags():
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
    if not text:
        return Markup("")
    raw = markdown.markdown(
        text,
        extensions=["nl2br", "sane_lists"],
        output_format="html",
    )
    clean = bleach.clean(raw, tags=_allowed_tags(), strip=True)
    return Markup(clean)
