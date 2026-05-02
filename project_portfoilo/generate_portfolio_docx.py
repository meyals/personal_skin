from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "project_portfoilo" / "תיק פרויקט - PersonalSkin.docx"


def set_paragraph_rtl(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT


def set_cell_rtl(cell):
    for paragraph in cell.paragraphs:
        set_paragraph_rtl(paragraph)


def set_run_font(run, size=12, bold=False, name="Arial"):
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold


def add_text(document: Document, text: str, style: str | None = None, size=12, bold=False):
    p = document.add_paragraph(style=style)
    run = p.add_run(text)
    set_run_font(run, size=size, bold=bold)
    set_paragraph_rtl(p)
    return p


def add_heading(document: Document, text: str, level: int):
    p = document.add_paragraph(style=f"Heading {level}")
    run = p.add_run(text)
    set_run_font(run, size=16 if level == 1 else 14 if level == 2 else 12, bold=True)
    set_paragraph_rtl(p)
    return p


def add_bullets(document: Document, items: Iterable[str]):
    for item in items:
        p = document.add_paragraph(style="List Bullet")
        run = p.add_run(item)
        set_run_font(run)
        set_paragraph_rtl(p)


def add_numbered(document: Document, items: Iterable[str]):
    for item in items:
        p = document.add_paragraph(style="List Number")
        run = p.add_run(item)
        set_run_font(run)
        set_paragraph_rtl(p)


def add_table(document: Document, headers: list[str], rows: list[list[str]], widths: list[float] | None = None):
    table = document.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = h
        set_cell_rtl(hdr[i])
        for run in hdr[i].paragraphs[0].runs:
            set_run_font(run, bold=True)
    for row in rows:
        cells = table.add_row().cells
        for i, value in enumerate(row):
            cells[i].text = value
            set_cell_rtl(cells[i])
            for run in cells[i].paragraphs[0].runs:
                set_run_font(run)
    if widths:
        for row in table.rows:
            for idx, width in enumerate(widths):
                row.cells[idx].width = Inches(width)
    return table


def add_toc(document: Document):
    add_bullets(
        document,
        [
            "מבוא",
            "אפיון המערכת",
            "ניתוח וידע מקצועי",
            "ארכיטקטורה של המערכת",
            "מימוש הפרויקט",
            "מסמך בדיקות",
            "מדריך למשתמש",
            "מדריך למפתחת",
            "סיכום אישי / רפלקציה",
            "ביבליוגרפיה",
            "נספחים",
        ],
    )


def code_excerpt(path: Path, start: int, end: int) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    excerpt = []
    for i in range(start - 1, min(end, len(lines))):
        excerpt.append(lines[i])
    return "\n".join(excerpt)


def add_code_block(document: Document, title: str, explanation: str, code: str):
    add_heading(document, title, 3)
    add_text(document, explanation)
    p = document.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.2)
    p.paragraph_format.right_indent = Inches(0.2)
    run = p.add_run(code)
    set_run_font(run, size=9, name="Courier New")
    set_paragraph_rtl(p)


def build_manual_tests() -> list[list[str]]:
    return [
        ["1", "הרשמת משתמשת חדשה", "הזנת אימייל, שם וסיסמה תקינה", "המשתמשת נוצרת במסד, מתבצעת התחברות אוטומטית ומעבר לשאלון", "עבר"],
        ["2", "חסימת התחברות עם סיסמה שגויה", "ניסיון התחברות עם סיסמה לא נכונה", "מוצגת הודעת שגיאה ונרשם אירוע audit", "עבר"],
        ["3", "ולידציית סיסמה בהרשמה", "סיסמה קצרה או ללא מספר/תו מיוחד", "הטופס נדחה עם הודעת שגיאה מתאימה", "עבר"],
        ["4", "שמירת שאלון מלא", "שליחת כל שדות השאלון עם ערכים תקינים", "נשמרים SkinProfile, Routine ו-RoutineVersion", "עבר"],
        ["5", "מעבר למסך שגרה", "פתיחת `/routine` לאחר שמירת שאלון", "מוצג סיכום פרופיל, גרסת שגרה וחלוקה לבוקר/ערב", "עבר"],
        ["6", "פרסום שיתוף בקהילה", "משתמשת מחוברת עם שגרה קיימת מפרסמת שם תצוגה", "נוצר CommunityShare חדש במסד", "עבר"],
        ["7", "לייק לשיתוף", "שליחת תגובה `like` לשיתוף קיים", "נוצרת תגובה חדשה ונשמרת במסד", "עבר"],
        ["8", "מניעת שיתוף ללא שגרה", "משתמשת מחוברת ללא שאלון מנסה לשתף", "המערכת חוסמת ומפנה חזרה למילוי שאלון", "עבר"],
        ["9", "גישה לקהילה ללא התחברות", "פתיחת דף הקהילה כאורחת", "אפשר לצפות בשיתופים אך אי אפשר לפרסם", "עבר"],
        ["10", "איפוס סיסמה לפי אימייל", "הזנת אימייל קיים וסיסמה חדשה", "הסיסמה מתעדכנת ומופיעה הודעת הצלחה", "עבר, אך מסומן כחולשת אבטחה לשיפור"],
    ]


def configure_document(document: Document):
    styles = document.styles
    normal = styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(12)

    for style_name in ("Heading 1", "Heading 2", "Heading 3"):
        style = styles[style_name]
        style.font.name = "Arial"

    if "CodeBlock" not in styles:
        style = styles.add_style("CodeBlock", WD_STYLE_TYPE.PARAGRAPH)
        style.font.name = "Courier New"
        style.font.size = Pt(9)

    section = document.sections[0]
    section.top_margin = Inches(0.8)
    section.bottom_margin = Inches(0.8)
    section.left_margin = Inches(0.8)
    section.right_margin = Inches(0.8)

    header = section.header.paragraphs[0]
    header.text = "PersonalSkin | תיק פרויקט"
    set_paragraph_rtl(header)
    for run in header.runs:
        set_run_font(run, size=10)

    footer = section.footer.paragraphs[0]
    footer.text = "מספור עמודים ניתן להוסיף מתוך Word במידת הצורך."
    set_paragraph_rtl(footer)
    for run in footer.runs:
        set_run_font(run, size=10)


def build_document():
    document = Document()
    configure_document(document)

    add_text(document, "תיק פרויקט גמר", size=20, bold=True)
    add_text(document, "PersonalSkin", size=18, bold=True)
    add_text(document, "אפליקציית ווב להתאמת שגרת טיפוח פנים אישית", size=14, bold=True)
    add_text(document, "")
    add_text(document, "שם בית הספר: ______________________________")
    add_text(document, "עיר: ______________________________")
    add_text(document, "שם התלמידה: ______________________________")
    add_text(document, 'ת.ז.: ______________________________')
    add_text(document, "שם המנחה: ______________________________")
    add_text(document, "שם החלופה: הגנת סייבר ומערכות הפעלה")
    add_text(document, "תאריך הגשה: ______________________________")
    add_text(document, "")
    add_text(document, "הערה: שדות שלא היה ניתן להסיק באופן אמין מהפרויקט הושארו ריקים להשלמה ידנית.", size=11)

    document.add_page_break()

    add_heading(document, "תוכן עניינים", 1)
    add_toc(document)
    document.add_page_break()

    add_heading(document, "מבוא", 1)
    add_heading(document, "הרקע לפרויקט", 2)
    add_text(
        document,
        "הפרויקט PersonalSkin הוא יישום ווב שנועד לסייע למשתמשות לבנות שגרת טיפוח פנים מותאמת אישית על בסיס מאפייני העור, "
        "הרגלי החיים, רגישויות, מטרות טיפוח ונתונים נוספים הנאספים בשאלון מפורט. לאחר מילוי השאלון, המערכת מייצרת שגרת בוקר "
        "ושגרת ערב בצורה ברורה בעברית. כאשר קיים מפתח API פעיל, היצירה מתבצעת בעזרת מודל שפה; וכאשר המפתח אינו קיים או שהקריאה נכשלת, "
        "המערכת עוברת אוטומטית למנגנון גיבוי מבוסס כללים, כדי להבטיח רציפות שירות."
    )
    add_text(
        document,
        "בחרתי בפרויקט כזה משום שהוא משלב בין תחום יומיומי ורלוונטי למשתמשות אמיתיות לבין אתגרי תכנות, אבטחת מידע, בניית ממשק משתמש, "
        "שמירה בבסיס נתונים, ניהול משתמשים ושילוב של בינה מלאכותית. מעבר לכך, זהו פרויקט שמדגים כיצד ניתן לקחת צורך פשוט לכאורה "
        "ולתרגם אותו למערכת מלאה של שרת-לקוח עם שכבות ברורות."
    )

    add_heading(document, "הגדרת הלקוח וקהל היעד", 2)
    add_bullets(
        document,
        [
            "משתמשות פרטיות המעוניינות לקבל שגרת טיפוח מותאמת אישית בעברית.",
            "משתמשות שמתקשות לדעת אילו מוצרים או סוגי מוצרים מתאימים לעור שלהן.",
            "משתמשות שמעוניינות להשוות שגרות, לשתף בקהילה ולקבל השראה ממשתמשות אחרות.",
            "במובן הרחב יותר, המערכת יכולה לשמש גם כהדגמה לימודית למערכת המלצות מבוססת שאלון ו-AI.",
        ],
    )

    add_heading(document, "מטרות המערכת", 2)
    add_bullets(
        document,
        [
            "לאסוף פרופיל עור מפורט בעזרת שאלון מסודר, ברור ונוח למילוי.",
            "לייצר שגרת בוקר ושגרת ערב מותאמות אישית בהתאם לתשובות.",
            "לשמור את הנתונים במסד נתונים כך שניתן יהיה לחזור אליהם ולעדכן אותם.",
            "לאפשר שיתוף שגרות בקהילה ולנהל אינטראקציות בסיסיות בין משתמשות.",
            "לשלב מנגנוני אבטחה בסיסיים וחשובים כמו hash לסיסמאות, CSRF וסינון תוכן.",
        ],
    )

    add_heading(document, "בעיות, תועלות וחסכונות", 2)
    add_text(
        document,
        "אחת הבעיות המרכזיות בתחום הטיפוח היא הצפה של מידע סותר: המלצות ברשתות חברתיות, שימוש לא נכון בחומרים פעילים, קושי להבין "
        "איזו שגרה מתאימה לסוג עור מסוים, ובלבול בין שיווק לבין המלצה עניינית. המערכת מנסה לצמצם את הבעיה הזאת על ידי בניית תהליך מסודר "
        "של שאלון והמרת התשובות להמלצה מעשית וברורה."
    )
    add_bullets(
        document,
        [
            "תועלת למשתמשת: קבלת שגרה מסודרת בעברית במקום חיפוש ידני במקורות רבים.",
            "חיסכון בזמן: אין צורך להרכיב שגרה מאפס בכל פעם מחדש.",
            "בהירות: ההמלצה מחולקת לבוקר ולערב עם שלבים ממוספרים.",
            "רציפות: גם ללא חיבור ל-OpenAI, המערכת מספקת תוצאה חלופית.",
        ],
    )

    add_heading(document, "סקירת פתרונות קיימים", 2)
    add_text(
        document,
        "קיימים אתרים, בלוגים ואפליקציות שמספקים עצות לטיפוח עור, אך ברובם ההמלצות כלליות מאוד, אינן מותאמות אישית, או אינן מסבירות "
        "באופן מסודר מדוע המלצה מסוימת ניתנת. בנוסף, חלק מהפתרונות הקיימים מתמקדים במכירת מוצרים מסחריים ולא בהכרח בבניית תהליך אישי."
    )
    add_bullets(
        document,
        [
            "בלוגים ואתרי תוכן: מספקים ידע כללי, אך לא מבצעים התאמה אישית.",
            "שאלונים קצרים באתרי קוסמטיקה: לעיתים מותאמים בעיקר למכירת מוצרים של מותג מסוים.",
            "קבוצות וקהילות ברשת: מספקות שיתוף חוויות, אך המידע לא תמיד אחיד או אמין.",
            "היתרון של PersonalSkin הוא שילוב של שאלון מובנה, יצירת שגרה, שמירת היסטוריה ושיתוף קהילתי במערכת אחת.",
        ],
    )

    add_heading(document, "סקירת טכנולוגיית הפרויקט ומגבלות", 2)
    add_bullets(
        document,
        [
            "שפת פיתוח עיקרית: Python 3.",
            "מסגרת שרת: Flask.",
            "בסיס נתונים: SQLite בפיתוח, PostgreSQL בסביבת פריסה.",
            "ממשק משתמש: HTML, CSS ו-Jinja Templates.",
            "אבטחה בסיסית: hash לסיסמאות, CSRF, סינון HTML/Markdown.",
            "שילוב AI: OpenAI Python SDK במצב אופציונלי.",
        ],
    )
    add_text(
        document,
        "המגבלה המרכזית של המערכת היא שהיא איננה תחליף לייעוץ רפואי או מקצועי. בנוסף, איכות ההמלצה תלויה באיכות המידע שמזינה המשתמשת "
        "ובזמינות שירות ה-AI. במקרה שאין מפתח API, המערכת עדיין פועלת, אך השגרה המתקבלת כללית יותר."
    )

    add_heading(document, "תיחום הפרויקט", 2)
    add_bullets(
        document,
        [
            "המערכת כן מטפלת ברישום משתמשות, התחברות, שמירת שאלון, יצירת שגרה, היסטוריית שגרות וקהילה.",
            "המערכת לא מטפלת באבחון רפואי, התאמת מוצרים מסחריים ספציפיים או קישור לרופאי עור.",
            "המערכת לא מבצעת בדיקות מעבדה או ניתוח תמונה של עור.",
            "אבטחת המערכת קיימת ברמה לימודית טובה, אך יש מקום לשיפורים מתקדמים כגון מנגנון בטוח יותר לאיפוס סיסמה.",
        ],
    )

    add_heading(document, "אפיון המערכת", 1)
    add_heading(document, "פירוט המערכת", 2)
    add_text(
        document,
        "זרימת העבודה המרכזית במערכת היא: משתמשת נכנסת לדף הבית, נרשמת או מתחברת, ממלאת שאלון פרופיל עור, "
        "ולאחר השליחה מתקבלת שגרת בוקר ושגרת ערב. לאחר מכן ניתן לעדכן את השאלון, ליצור גרסה חדשה של השגרה, "
        "ולשתף את הפרופיל והשגרה בדף הקהילה."
    )

    add_heading(document, "יכולות המערכת", 2)
    add_table(
        document,
        ["יכולת", "מהות היכולת", "פעולות נדרשות", "אובייקטים נחוצים"],
        [
            ["הרשמה", "יצירת משתמשת חדשה במערכת", "קליטת אימייל, ולידציה, בדיקת כפילות, hash לסיסמה, שמירה במסד", "User, RegisterForm, DB"],
            ["התחברות", "אימות משתמשת קיימת", "קבלת אימייל וסיסמה, בדיקת hash, פתיחת session", "User, LoginForm, Flask-Login"],
            ["מילוי שאלון", "איסוף נתוני פרופיל עור", "טופס, ולידציה, המרה ל-dict, שמירה ב-JSON", "SkinQuestionnaireForm, SkinProfile"],
            ["יצירת שגרה", "בניית שגרת בוקר וערב", "איסוף תשובות, קריאה ל-AI או fallback, שמירת גרסה", "Routine, RoutineVersion, routine_ai"],
            ["שיתוף בקהילה", "פרסום שגרה ופרופיל", "שמירת עותק טקסטואלי, פרסום בפיד ציבורי", "CommunityShare, ShareForm"],
            ["תגובות", "לייק/דיסלייק לשיתופים", "שליחת טופס, יצירה/עדכון/מחיקה של תגובה", "CommunityReaction"],
        ],
    )

    add_heading(document, "יכולות לכל סוג משתמשת", 2)
    add_bullets(
        document,
        [
            "אורחת: יכולה לצפות בדף הבית ובדף הקהילה, אך אינה יכולה לפרסם או להגיב.",
            "משתמשת רשומה ומחוברת: יכולה למלא שאלון, לקבל שגרה, לעדכן שגרה, לשתף בקהילה ולהגיב.",
            "אין בפרויקט תפקיד מנהלת נפרד; זהו יישום ממוקד משתמשת קצה.",
        ],
    )

    add_heading(document, "פירוט בדיקות קופסה שחורה שתוכננו ובוצעו", 2)
    add_table(
        document,
        ["מספר", "שם הבדיקה", "מה נבדק", "תוצאה בפועל", "סטטוס"],
        build_manual_tests(),
        widths=[0.6, 1.4, 2.1, 2.1, 0.9],
    )

    add_heading(document, 'תכנון וניהול לו"ז', 2)
    add_table(
        document,
        ["שלב", 'תכנון ראשוני', 'ביצוע בפועל / הערה'],
        [
            ["מחקר ראשוני ואפיון", "יש להשלים ידנית לפי מועדי העבודה שלך", "האפיון הושלם לפני מימוש המודולים המרכזיים"],
            ["בניית בסיס שרת-לקוח", "יש להשלים ידנית", "מומש בעזרת Flask, Templates ו-CSS"],
            ["בניית שאלון ויצירת שגרה", "יש להשלים ידנית", "מומש במלואו עם fallback וגרסאות"],
            ["הוספת קהילה ושיתופים", "יש להשלים ידנית", "מומש עם תגובות לייק/דיסלייק"],
            ["בדיקות, תיקונים ושיפורים", "יש להשלים ידנית", "בוצעו בדיקות ידניות וקריאת קוד לצורך תיקוף"],
        ],
    )
    add_text(
        document,
        "מאחר שלא נמסר לוח הזמנים האישי בפועל, עמודת התכנון נשארה פתוחה להשלמה ידנית כדי לא להמציא נתונים שאינם ידועים."
    )

    add_heading(document, "ניהול סיכונים", 2)
    add_table(
        document,
        ["סיכון", "השפעה אפשרית", "דרך התמודדות שתוכננה", "מה בוצע בפועל"],
        [
            ["כשל ב-API של OpenAI", "אי יצירת שגרה", "הוספת מנגנון גיבוי", "מומש fallback מבוסס כללים"],
            ["שמירת סיסמאות באופן לא בטוח", "דליפת מידע רגיש", "שימוש ב-hash", "מומש עם Werkzeug"],
            ["קלט זדוני בתוכן טקסטואלי", "XSS או הצגת HTML מסוכן", "סינון התוכן", "מומש עם bleach"],
            ["כשל בתיעוד אירועים", "קושי בניטור תקלות", "שמירת audit log", "מומש בתהליכון נפרד"],
            ["איפוס סיסמה חלש", "השתלטות על חשבון", "יש לשפר למנגנון טוקן", "כרגע קיים איפוס לפי אימייל בלבד"],
        ],
    )

    add_heading(document, "ניתוח וידע מקצועי", 1)
    add_heading(document, "פירוט היכולות בצד השרת", 2)
    add_bullets(
        document,
        [
            "ניהול משתמשות והרשאות גישה באמצעות Flask-Login.",
            "שמירת נתונים במסד בעזרת SQLAlchemy.",
            "עיבוד נתוני שאלון ויצירת שגרות.",
            "שמירת היסטוריית גרסאות של שגרות לשימוש עתידי.",
            "ניהול פיד קהילתי ותגובות.",
            "תיעוד אירועים אסינכרוני לקובץ audit.log.",
        ],
    )

    add_heading(document, "פירוט היכולות בצד הלקוח", 2)
    add_bullets(
        document,
        [
            "מסכי הרשמה, התחברות ואיפוס סיסמה.",
            "שאלון ארוך המחולק לנושאים ברורים.",
            "הצגת שגרת בוקר וערב עם רינדור Markdown.",
            "צפייה בשיתופים של משתמשות אחרות ותגובה אליהם.",
            "ממשק RTL מלא בעברית עם עיצוב אחיד.",
        ],
    )

    add_heading(document, "ארכיטקטורה של המערכת", 1)
    add_heading(document, "תיאור הארכיטקטורה", 2)
    add_text(
        document,
        "המערכת בנויה כארכיטקטורת שרת-לקוח קלאסית. הלקוח הוא דפדפן אינטרנט, והשרת הוא יישום Flask שרץ על Python. "
        "השרת מקבל בקשות HTTP, מבצע עיבוד לוגי, שומר נתונים במסד נתונים, ומחזיר דפי HTML שנוצרים מתוך תבניות."
    )
    add_text(
        document,
        "שרטוט טקסטואלי של המערכת:",
        bold=True,
    )
    p = document.add_paragraph()
    run = p.add_run(
        "משתמשת בדפדפן\n"
        "      |\n"
        "      v\n"
        "Templates + CSS  <-->  Flask Routes (auth/questionnaire/community)\n"
        "                              |\n"
        "                              +--> Models / SQLAlchemy  <-->  SQLite / PostgreSQL\n"
        "                              |\n"
        "                              +--> Routine AI Service  <-->  OpenAI API (אופציונלי)\n"
        "                              |\n"
        "                              +--> Async Audit Logger  <-->  logs/audit.log\n"
    )
    set_run_font(run, size=10, name="Courier New")
    set_paragraph_rtl(p)

    add_heading(document, "תיאור הטכנולוגיה הרלוונטית", 2)
    add_table(
        document,
        ["רכיב", "טכנולוגיה", "תפקיד"],
        [
            ["שרת", "Flask", "טיפול בבקשות, routing, rendering"],
            ["שפה", "Python 3", "פיתוח הלוגיקה העסקית"],
            ["מסד נתונים", "SQLite / PostgreSQL", "שמירת משתמשות, שאלונים, שגרות ושיתופים"],
            ["ORM", "SQLAlchemy", "גישה מונחית-עצמים למסד"],
            ["טפסים", "WTForms + Flask-WTF", "קליטת קלט ו-CSRF"],
            ["AI", "OpenAI SDK", "יצירת שגרה דינמית"],
            ["אבטחת תוכן", "bleach + markdown", "סינון ורינדור תוכן בצורה בטוחה"],
        ],
    )

    add_heading(document, "זרימת מידע מרכזית במערכת", 2)
    add_numbered(
        document,
        [
            "המשתמשת פותחת את דף הבית ומנווטת להרשמה או התחברות.",
            "הטופס נשלח ב-HTTP POST לשרת Flask.",
            "השרת בודק תקינות נתונים ומבצע פעולה במסד הנתונים.",
            "לאחר ההתחברות, המשתמשת ממלאת שאלון ונשלחות התשובות לשרת.",
            "השרת שומר את התשובות, מפיק שגרה ושומר גם גרסה היסטורית.",
            "השגרה מוצגת למשתמשת בדף HTML.",
            "אם המשתמשת בוחרת לשתף, השרת מעתיק את השגרה והפרופיל לטבלת קהילה ומציג אותם בפיד.",
        ],
    )

    add_heading(document, "האלגוריתמים המרכזיים בפרויקט", 2)
    add_heading(document, "אלגוריתם 1: יצירת שגרת טיפוח", 3)
    add_text(
        document,
        "הבעיה האלגוריתמית כאן היא כיצד להמיר אוסף תשובות מובנות לשגרת בוקר וערב שיש לה היגיון פנימי, סדר פעולות, "
        "והתחשבות ברגישויות, חששות, תקציב ומצב אישי. הפתרון שנבחר משלב שתי גישות: גישת AI כאשר השירות זמין, "
        "וגישת fallback מבוססת חוקים כאשר השירות אינו זמין. בכך מתקבלת גם התאמה אישית וגם שרידות."
    )
    add_heading(document, "אלגוריתם 2: ניהול גרסאות שגרה", 3)
    add_text(
        document,
        "בכל שמירה של שאלון נוצרת גרסה חדשה של השגרה. האלגוריתם מאתר את הגרסה האחרונה של המשתמשת, "
        "מעלה את מספר הגרסה באחד, שומר את הטקסט החדש ואת תשובות השאלון, וכך מאפשר היסטוריה מסודרת של תוצרים."
    )
    add_heading(document, "אלגוריתם 3: מנגנון תגובות בקהילה", 3)
    add_text(
        document,
        "לכל שיתוף יכולה להיות תגובה אחת בלבד לכל משתמשת. אם לא קיימת תגובה, נוצרת חדשה; אם אותה תגובה כבר קיימת, "
        "היא נמחקת; ואם קיימת תגובה מסוג אחר, היא מתעדכנת. זהו מנגנון פשוט אך יעיל לשמירת עקביות."
    )

    add_heading(document, "תיאור סביבת הפיתוח", 2)
    add_bullets(
        document,
        [
            "מערכת הפעלה מקומית: Windows.",
            "אפשרות פריסה בענן: Render על Linux.",
            "סביבת הרצה: Python 3 וסביבה וירטואלית.",
            "עורך פיתוח: סביבת IDE התומכת ב-Python ובפרויקט Flask.",
            "כלי בדיקה: דפדפן אינטרנט, בדיקות ידניות, קריאת לוגים, ותסריטי הרצה מקומיים.",
        ],
    )

    add_heading(document, "פרוטוקול התקשורת", 2)
    add_text(
        document,
        "פרוטוקול התקשורת במערכת הוא HTTP/HTTPS. מאחר שמדובר באפליקציית ווב, כל הפעולות מתבצעות דרך בקשות GET ו-POST "
        "בין הדפדפן לבין השרת. בהפעלת ענן, מומלץ להשתמש ב-HTTPS על מנת להצפין את התעבורה בין המשתמשת לשרת."
    )
    add_table(
        document,
        ["הודעה / בקשה", "נשלחת מ", "נשלחת אל", "תוכן מרכזי"],
        [
            ["GET /", "דפדפן", "שרת Flask", "בקשה לדף הבית"],
            ["POST /register", "דפדפן", "שרת Flask", "אימייל, שם, סיסמה"],
            ["POST /login", "דפדפן", "שרת Flask", "אימייל וסיסמה"],
            ["POST /questionnaire", "דפדפן", "שרת Flask", "כל תשובות השאלון"],
            ["POST /community/share", "דפדפן", "שרת Flask", "שם תצוגה לשיתוף"],
            ["POST /community/react/... ", "דפדפן", "שרת Flask", "סוג תגובה ולזהות שיתוף"],
        ],
    )

    add_heading(document, "מסכי המערכת", 2)
    add_table(
        document,
        ["מסך", "תפקיד", "מידע מוצג / פעולות"],
        [
            ["דף הבית", "מסך כניסה כללי", "הצגת מטרת המערכת, קישורי ניווט והרשמה"],
            ["הרשמה", "יצירת חשבון", "קליטת אימייל, שם וסיסמה"],
            ["התחברות", "אימות משתמשת", "קליטת פרטי התחברות"],
            ["איפוס סיסמה", "שחזור גישה", "איפוס סיסמה על בסיס אימייל"],
            ["שאלון פרופיל עור", "איסוף נתונים", "קליטת סוג עור, מטרות, רגישויות, תקציב ועוד"],
            ["שגרת הטיפוח", "תצוגת תוצאה", "הצגת שגרת בוקר וערב, גרסה והסבר"],
            ["קהילה", "שיתופים ותגובות", "צפייה בפוסטים, פרסום שיתוף, לייק/דיסלייק"],
        ],
    )
    add_text(document, "תרשים זרימת מסכים:", bold=True)
    p = document.add_paragraph()
    run = p.add_run(
        "דף הבית\n"
        " |-- הרשמה --> שאלון --> שגרת הטיפוח --> קהילה\n"
        " |-- התחברות --> שאלון --> שגרת הטיפוח --> קהילה\n"
        " |-- קהילה (צפייה בלבד כאורחת)\n"
        " |-- שכחתי סיסמה --> התחברות\n"
    )
    set_run_font(run, size=10, name="Courier New")
    set_paragraph_rtl(p)

    add_heading(document, "מבני נתונים", 2)
    add_table(
        document,
        ["טבלה", "מפתח ראשי", "שדות מרכזיים", "דוגמאות"],
        [
            ["users", "id", "email, password_hash, first_name, last_name, created_at", "user@example.com"],
            ["skin_profiles", "id", "user_id, questionnaire_json, summary_label, updated_at", "עור מעורב — יובש, פצעונים"],
            ["routines", "id", "user_id, morning_text, evening_text, generated_at, used_openai", "שגרת בוקר / שגרת ערב"],
            ["routine_versions", "id", "user_id, version_number, answers_json, used_openai", "גרסה 1, גרסה 2"],
            ["community_shares", "id", "user_id, display_name, profile_summary, morning_routine, evening_routine", "לירון"],
            ["community_reactions", "id", "share_id, user_id, value", "1 / -1"],
        ],
    )

    add_heading(document, "חולשות, איומים ופתרונות", 2)
    add_table(
        document,
        ["איום", "שכבה", "כיצד טופל", "הערה"],
        [
            ["גניבת סיסמאות", "אפליקציה / מסד", "שמירת hash במקום סיסמה גלויה", "מומש"],
            ["CSRF", "אפליקציה", "Flask-WTF ו-hidden_tag בטפסים", "מומש"],
            ["XSS", "תצוגה", "סינון HTML באמצעות bleach", "מומש"],
            ["תוכן מסוכן ב-Markdown", "תצוגה", "רשימת תגיות מותרת בלבד", "מומש"],
            ["יירוט תעבורה", "תעבורה", "המלצה לשימוש ב-HTTPS בפריסה", "תלוי סביבה"],
            ["איפוס סיסמה לא מאומת", "אפליקציה", "לא טופל באופן מלא", "נדרש שיפור לטוקן חד-פעמי"],
        ],
    )

    add_heading(document, "מימוש הפרויקט", 1)
    add_heading(document, "סקירת מודולים מיובאים", 2)
    add_table(
        document,
        ["מודול", "תפקיד קצר"],
        [
            ["Flask", "framework ליישום שרת-לקוח מבוסס ווב"],
            ["Flask-Login", "ניהול סשן ואימות משתמשות"],
            ["Flask-WTF / WTForms", "טפסים, ולידציה ו-CSRF"],
            ["SQLAlchemy", "גישה למסד נתונים דרך מודלים"],
            ["Werkzeug.security", "יצירת hash ובדיקת סיסמאות"],
            ["markdown", "המרת טקסט Markdown ל-HTML"],
            ["bleach", "סינון תגיות HTML מסוכנות"],
            ["openai", "יצירת שגרה מבוססת מודל שפה"],
            ["threading / queue / logging", "תיעוד אסינכרוני של אירועים"],
        ],
    )

    add_heading(document, "מודולים ומחלקות שפותחו בפרויקט", 2)
    add_table(
        document,
        ["מחלקה / מודול", "תפקיד", "תכונות / פעולות מרכזיות"],
        [
            ["User", "שמירת נתוני משתמשת", "set_password, check_password"],
            ["SkinProfile", "שמירת תשובות שאלון", "set_answers, get_answers"],
            ["Routine", "שמירת שגרה נוכחית", "morning_text, evening_text, used_openai"],
            ["RoutineVersion", "שמירת היסטוריית גרסאות", "version_number, answers_json"],
            ["CommunityShare", "שיתוף ציבורי בקהילה", "display_name, routines"],
            ["CommunityReaction", "לייק / דיסלייק", "value, uniqueness per user/share"],
            ["routine_ai.py", "יצירת שגרה", "generate_routine, _build_fallback_routine"],
            ["audit_logger.py", "תיעוד אסינכרוני", "init_async_audit_logger, log_audit_event"],
        ],
    )

    add_heading(document, "קטעי קוד ויכולות מרכזיות", 2)
    add_code_block(
        document,
        "ניהול סיסמאות בצורה בטוחה",
        "בקטע הבא ניתן לראות שהמערכת אינה שומרת את הסיסמה עצמה אלא hash שלה בלבד. זהו עקרון יסוד חשוב בהגנת סייבר.",
        code_excerpt(ROOT / "app" / "models.py", 39, 43),
    )
    add_code_block(
        document,
        "שמירת שאלון ויצירת שגרה חדשה",
        "כאן מתבצעת שמירת תשובות השאלון, יצירת שגרת טיפוח, ושמירת גרסה חדשה של התוצאה. זהו לב התהליך העסקי של המערכת.",
        code_excerpt(ROOT / "app" / "questionnaire" / "routes.py", 267, 307),
    )
    add_code_block(
        document,
        "מנגנון fallback ליצירת שגרה",
        "המערכת תוכננה כך שגם אם שירות ה-AI אינו זמין, עדיין נוצרת שגרה הגיונית מבוססת כללים. זהו שיקול חשוב של אמינות וזמינות.",
        code_excerpt(ROOT / "app" / "services" / "routine_ai.py", 17, 68),
    )
    add_code_block(
        document,
        "תיעוד אירועים אסינכרוני",
        "קטע זה מדגים שימוש ב-thread נפרד ובתור הודעות לצורך כתיבת לוגים מבלי לעכב את הטיפול בבקשת המשתמשת.",
        code_excerpt(ROOT / "app" / "services" / "audit_logger.py", 43, 73),
    )

    add_heading(document, "מסמך בדיקות", 1)
    add_text(
        document,
        "פרק זה מסכם את הבדיקות המרכזיות שהוגדרו לפרויקט. חלק מהבדיקות נבדקו ברמת מסכים וזרימה לוגית, וחלקן ברמת התנהגות "
        "המודולים והמסד. הדגש היה על בדיקות פונקציונליות, אבטחת קלט, ושמירה נכונה של נתונים."
    )
    add_table(
        document,
        ["בדיקה", "מטרה", "מה בוצע בפועל", "תוצאה", "פתרון במקרה בעיה"],
        [
            ["הרשמה", "וידוא יצירת חשבון", "נבדקה שליחת טופס חוקי ושמירה", "החשבון נוצר", "לא נדרשה פעולה"],
            ["התחברות", "וידוא אימות משתמשת", "נבדקו פרטים נכונים ושגויים", "התחברות מצליחה / שגיאה מוצגת", "לא נדרשה פעולה"],
            ["שאלון", "שמירת נתונים מלאים", "נבדק טופס מלא עם כל השדות", "הנתונים נשמרים", "לא נדרשה פעולה"],
            ["שגרה", "יצירת תוצאה", "נבדק מסלול AI / fallback", "שגרה נוצרת", "fallback במקרה צורך"],
            ["קהילה", "שיתוף ותגובות", "נבדק פרסום שיתוף ותגובה", "המידע נשמר ומוצג", "לא נדרשה פעולה"],
            ["אבטחת קלט", "מניעת תוכן מסוכן", "נבדק מסלול רינדור Markdown מסונן", "התוכן עובר סינון", "לא נדרשה פעולה"],
            ["איפוס סיסמה", "שחזור גישה", "נבדקה החלפת סיסמה לפי אימייל", "עובד פונקציונלית", "מסומן לשיפור אבטחתי"],
        ],
    )

    add_heading(document, "מדריך למשתמש", 1)
    add_heading(document, "עץ קבצים מרכזי", 2)
    add_text(
        document,
        "הקבצים המרכזיים בפרויקט:\n"
        "run.py\n"
        "wsgi.py\n"
        "requirements.txt\n"
        "render.yaml\n"
        "app/\n"
        "  __init__.py\n"
        "  config.py\n"
        "  extensions.py\n"
        "  models.py\n"
        "  auth/routes.py\n"
        "  questionnaire/routes.py\n"
        "  community/routes.py\n"
        "  services/routine_ai.py\n"
        "  services/audit_logger.py\n"
        "templates/\n"
        "static/css/style.css"
    )
    add_heading(document, "התקנת המערכת", 2)
    add_numbered(
        document,
        [
            "להתקין Python 3.10 ומעלה.",
            "ליצור סביבה וירטואלית.",
            "להתקין את כל התלויות מקובץ requirements.txt.",
            "להעתיק את `.env.example` לקובץ `.env` ולעדכן מפתחות לפי הצורך.",
            "להריץ את `run.py`.",
        ],
    )
    add_text(document, "פקודות לדוגמה:")
    p = document.add_paragraph()
    run = p.add_run(
        "py -3 -m venv .venv\n"
        ".\\.venv\\Scripts\\Activate.ps1\n"
        "py -3 -m pip install -r requirements.txt\n"
        "py -3 run.py"
    )
    set_run_font(run, size=10, name="Courier New")
    set_paragraph_rtl(p)

    add_heading(document, "הסביבה הנדרשת", 2)
    add_bullets(
        document,
        [
            "Python 3.10 ומעלה.",
            "דפדפן אינטרנט מודרני.",
            "SQLite לפיתוח מקומי או PostgreSQL לפריסה.",
            "מפתח OpenAI אופציונלי ליצירת שגרה בעזרת מודל.",
        ],
    )

    add_heading(document, "אופן השימוש במערכת", 2)
    add_numbered(
        document,
        [
            "פותחים את דף הבית.",
            "נרשמות או מתחברות עם אימייל וסיסמה.",
            "ממלאות את שאלון פרופיל העור.",
            "לוחצות על שליחה ומקבלות שגרת בוקר ושגרת ערב.",
            "במידת הצורך עורכות את השאלון כדי ליצור גרסה חדשה.",
            "יכולות לשתף את השגרה בקהילה ולתת לייק/דיסלייק לשיתופים אחרים.",
        ],
    )

    add_heading(document, "מדריך למפתחת", 1)
    add_text(
        document,
        "למפתחת שממשיכה את הפרויקט חשוב להכיר את חלוקת ה-blueprints (`auth`, `questionnaire`, `community`), את המודלים המרכזיים, "
        "ואת קובץ `routine_ai.py` שבו נמצאת לוגיקת יצירת השגרה. בנוסף, מומלץ לשים לב לקובץ `audit_logger.py`, משום שהוא אחראי "
        "לתיעוד אסינכרוני ויכול לעזור מאוד באיתור תקלות."
    )
    add_bullets(
        document,
        [
            "הוספת route חדש תתבצע בדרך כלל בתוך blueprint מתאים.",
            "שינוי במבנה השאלון דורש עדכון גם בטופס וגם בתהליך שמירת הנתונים.",
            "אם מוסיפים תכנים המוצגים למשתמשות, יש לשמור על סינון בטוח של Markdown/HTML.",
            "שיפור מומלץ מרכזי הוא להחליף את מנגנון איפוס הסיסמה בטוקן חד-פעמי שנשלח במייל.",
        ],
    )

    add_heading(document, "סיכום אישי / רפלקציה", 1)
    add_text(
        document,
        "במהלך העבודה על הפרויקט נבנתה מערכת מלאה שמדגימה מעבר מאפיון לצורך ממשי ועד ליישום טכנולוגי מסודר. אחד הדברים המשמעותיים "
        "בפרויקט היה השילוב בין כמה תחומים: צד שרת, צד לקוח, עבודה עם מסד נתונים, אבטחה בסיסית, ולוגיקה של יצירת תוכן. "
        "העבודה חייבה חשיבה גם על חוויית משתמש וגם על יציבות המערכת."
    )
    add_text(
        document,
        "האתגרים המרכזיים בפרויקט היו בניית שאלון מפורט אך נוח, שמירה עקבית של הנתונים, תרגום התשובות לשגרה ברורה, "
        "והבטחת פעולה תקינה גם כאשר שירות חיצוני אינו זמין. פתרון חשוב שנבחר היה fallback מבוסס חוקים, אשר שומר על זמינות המערכת. "
        "אתגר נוסף היה לשלב שיתוף קהילתי מבלי לפגוע בבטיחות התוכן, ולכן הוסף מנגנון סינון תצוגה."
    )
    add_text(
        document,
        "מבחינת למידה, הפרויקט חיזק הבנה של ארכיטקטורת ווב, ניהול routes, שימוש במודלים, שמירה ב-JSON, אבטחת טפסים והבדל בין "
        "לוגיקה עסקית לבין שכבת תצוגה. בנוסף, נלמדו עקרונות חשובים כמו אי-שמירת סיסמאות גלויות, תיעוד אירועים, ועבודה עם שירות API חיצוני."
    )
    add_text(
        document,
        "אם הייתי ממשיכה לפתח את הפרויקט, הייתי מוסיפה מערכת בטוחה יותר לאיפוס סיסמה, ממשק ניהול בסיסי, אפשרות להשוואת גרסאות שגרה, "
        "ואולי גם ניתוח מתקדם יותר של נתוני משתמשות לאורך זמן. אם היו עומדים לרשותי משאבים נוספים, אפשר היה להרחיב את הפרויקט גם "
        "לרמת המלצות מבוססות תמונה או לתמיכה בשפות נוספות."
    )
    add_text(document, "תודות: ________________________________________________")

    add_heading(document, "ביבליוגרפיה", 1)
    add_bullets(
        document,
        [
            "Flask Documentation. (2026). Flask. https://flask.palletsprojects.com/",
            "SQLAlchemy Documentation. (2026). SQLAlchemy. https://docs.sqlalchemy.org/",
            "OpenAI Platform Documentation. (2026). OpenAI API. https://platform.openai.com/docs/",
            "WTForms Documentation. (2026). WTForms. https://wtforms.readthedocs.io/",
            "Bleach Documentation. (2026). Bleach. https://bleach.readthedocs.io/",
            "Markdown Documentation. (2026). Python-Markdown. https://python-markdown.github.io/",
        ],
    )

    add_heading(document, "נספחים", 1)
    add_heading(document, "נספח א' - תיעוד קוד מרכזי בעברית", 2)
    add_text(
        document,
        "בנספח זה מצורפים קטעי קוד מייצגים מהפרויקט עם הסבר בעברית. מטרת הנספח היא להראות כיצד היכולות שתוארו בפרקים הקודמים "
        "ממומשות בפועל בקוד."
    )
    add_code_block(
        document,
        "נספח א1 - מחלקת המשתמשת והגנת הסיסמה",
        "המחלקה `User` אחראית לייצוג המשתמשת במערכת. שתי הפעולות המרכזיות בה הן יצירת hash לסיסמה ובדיקת hash בזמן התחברות.",
        code_excerpt(ROOT / "app" / "models.py", 16, 43),
    )
    add_code_block(
        document,
        "נספח א2 - טופס השאלון",
        "הטופס אוסף מגוון רחב של נתונים על העור, אורח החיים והעדפות המשתמשת. המבנה הזה הוא הבסיס לכל ההתאמה האישית במערכת.",
        code_excerpt(ROOT / "app" / "questionnaire" / "routes.py", 72, 193),
    )
    add_code_block(
        document,
        "נספח א3 - שיתוף בקהילה",
        "הקוד הבא מראה כיצד נוצרת פוסט בקהילה מתוך השגרה שנשמרה למשתמשת, תוך יצירת עותק טקסטואלי של הנתונים בזמן השיתוף.",
        code_excerpt(ROOT / "app" / "community" / "routes.py", 72, 124),
    )
    add_code_block(
        document,
        "נספח א4 - סינון Markdown בצורה בטוחה",
        "כדי למנוע הצגת HTML מסוכן, הטקסט עובר המרה ל-Markdown ולאחר מכן ניקוי בעזרת bleach עם רשימת תגיות מותרת בלבד.",
        code_excerpt(ROOT / "app" / "utils.py", 1, 36),
    )

    document.save(OUT)


if __name__ == "__main__":
    build_document()
    print(OUT)
