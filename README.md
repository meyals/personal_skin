# PersonalSkin

אפליקציית ווב (Flask) להתאמת שגרת טיפוח פנים אישית: משתמשים נרשמים, ממלאים שאלון פרופיל עור מפורט, ומקבלים שגרת **בוקר** ו**ערב** בטקסט — שנוצרת באמצעות **מודל שפה (OpenAI)** כשמוגדר מפתח API, או לפי **מצב גיבוי** מבוסס כללים כשאין מפתח או כשהקריאה נכשלת. קיים גם **דף קהילה** לצפייה בשיתופים של משתמשים ולפרסום עותק של הפרופיל והשגרה (עם שם לתצוגה).

הממשק והתוכן מוצגים בעברית וכיוון **RTL**. ההמלצות מיועדות להסבר כללי בלבד ואינן תחליף לייעוץ רפואי או מקצועי.

---

## מה האפליקציה עושה (זרימה קצרה)

1. **דף הבית** — קישורים להרשמה, התחברות, או צפייה בקהילה (גם ללא התחברות).
2. **הרשמה / התחברות** — משתמשים מאומתים עם אימייל וסיסמה; סיסמאות נשמרות כ־hash (Werkzeug). סשן נשמר עם Flask-Login (`remember=True`).
3. **שאלון עור** — לאחר התחברות: טופס עם סוג עור, גיל, חששות, רגישויות, מטרות, תקציב, זמן זמין, אקלים, הרגלי SPF, איפור, אקספוליאציה, רטינול, הריון/הנקה, ועוד. השמירה יוצרת/מעדכנת `SkinProfile` ו־`Routine` במסד.
4. **שגרה** — הטקסט מוצג כ־Markdown מסונן (Bleach) ל־HTML. אם נעשה שימוש ב־OpenAI, השדה `used_openai` במסד משקף זאת.
5. **קהילה** — פיד של עד 50 שיתופים אחרונים; משתמש מחובר יכול לפרסם פוסט עם שם לתצוגה (עותק טקסט של פרופיל ושגרה בזמן הפרסום).

מסד הנתונים הוא **SQLite** (`personal_skin.db` בספריית ההרצה, אלא אם הוגדר `DATABASE_URL`). הקובץ נוצר אוטומטית בעת עליית האפליקציה (`db.create_all()`).

---

## דרישות

- Python **3.10+** (נבדק עם 3.12)
- חבילות Python: ראו `requirements.txt`

---

## עמידה בדרישות הפרויקט (מפורט)

להלן מיפוי מפורט של דרישות ההגשה מול המימוש בפועל בפרויקט:

### 1) מימוש לפחות 2 מחלקות שונות הכוללות עצמים ופעולות על העצמים

קיים מימוש מלא של מספר מחלקות ב־`app/models.py`, כולל פעולות (methods) על עצמים:

- `User`:
  - שדות: `email`, `password_hash`, `first_name`, `last_name`, ועוד.
  - פעולות על עצם: `set_password()`, `check_password()`.
- `SkinProfile`:
  - שדות: `questionnaire_json`, `summary_label`, `updated_at`.
  - פעולות על עצם: `set_answers()`, `get_answers()`.
- מחלקות נוספות: `Routine`, `RoutineVersion`, `CommunityShare`.

בפועל נוצרים עצמים מהמחלקות האלה ברישום, מילוי שאלון, יצירת שגרה ושיתוף בקהילה, ונשמרים במסד הנתונים.

### 2) מערכת שרת-לקוח

המערכת ממומשת כיישום Web בתצורת שרת-לקוח:

- **שרת**: Flask (Python), כולל ניתוב בקבצי:
  - `app/auth/routes.py`
  - `app/questionnaire/routes.py`
  - `app/community/routes.py`
- **לקוח**: דפדפן אינטרנט (HTML/CSS ב־`templates/` + `static/css/`).
- **פרוטוקול תקשורת**: HTTP/HTTPS בין לקוח לשרת.
- **תמיכה במספר משתמשים**: השרת מטפל בבקשות של משתמשים שונים, עם סשן נפרד לכל משתמש דרך Flask-Login.

### 3) שימוש בבינה מלאכותית (בונוס)

קיים שימוש ב־AI בשירות יצירת שגרה:

- קובץ: `app/services/routine_ai.py`
- שימוש ב־OpenAI (`chat.completions.create`) ליצירת שגרת בוקר/ערב לפי תשובות השאלון.
- כאשר אין `OPENAI_API_KEY` או שיש כשל API, מופעל מנגנון גיבוי מבוסס כללים כדי לשמור על רציפות תפקודית.

### 4) מערכת הפעלה

הפרויקט ניתן להרצה בסביבות מערכת הפעלה שונות:

- **Windows** (פיתוח מקומי באמצעות PowerShell ו־Python)
- **Linux** (סביבת הרצה בענן ב־Render)

בנוסף, קיימות הוראות מפורטות ב־README להפעלה, עצירה והפעלה מחדש של השירות.

### 5) הצפנת סיסמאות

סיסמאות אינן נשמרות כטקסט גלוי:

- שימוש ב־`werkzeug.security` ל־hash של סיסמאות (`generate_password_hash`).
- אימות סיסמה מתבצע עם `check_password_hash`.
- המימוש נמצא ב־`app/models.py` ונעשה בו שימוש בזרימות הרשמה, התחברות ואיפוס סיסמה.

### 6) ממשק משתמש

קיים ממשק משתמש מלא מבוסס Web:

- תבניות HTML: `templates/`
- עיצוב CSS: `static/css/style.css`
- מסכים מרכזיים:
  - דף בית
  - הרשמה / התחברות / שכחתי סיסמה
  - שאלון פרופיל עור
  - תצוגת שגרה מותאמת
  - דף קהילה ושיתופים

---

## עמידה בדרישות תקשורת, אבטחה ותשתיות (Checklist)

### האם קיים פרוטוקול תקשורת ברור

כן. המערכת עובדת במודל לקוח-שרת מבוסס HTTP/HTTPS:

- הדפדפן (לקוח) מתקשר עם Flask (שרת) דרך Routes.
- בייצור (Render) הגישה מתבצעת ב־HTTPS.

### שימוש ב-Threads בפרויקט

כן. קיימת מערכת לוגים אסינכרונית מבוססת Thread נפרד:

- קובץ: `app/services/audit_logger.py`
- מנגנון: `Queue` + `Thread` ייעודי (`audit-log-worker`).
- ה-main thread של הבקשה לא כותב לוג ישירות לדיסק; הוא רק שולח אירוע לתור.

### עבודה עם קבצים / API / רכיבי מערכת

כן, בכל שלושת הרבדים:

- **קבצים**: תבניות `templates/`, עיצוב `static/css/`, קבצי קונפיג (`.env`, `render.yaml`), וקובץ לוג `logs/audit.log`.
- **API חיצוני**: OpenAI ב־`app/services/routine_ai.py`.
- **רכיבי מערכת**: משתני סביבה, שרת WSGI (`gunicorn`), תהליך פריסה בענן.

### הצפנה של מידע רגיש

כן, עבור סיסמאות:

- סיסמאות נשמרות כ-Hash באמצעות `generate_password_hash`.
- אימות סיסמה נעשה עם `check_password_hash`.
- הסיסמה עצמה אינה נשמרת כטקסט גלוי במסד הנתונים.

### טיפול בפרצות אבטחה

כן, קיימים מנגנוני הגנה מרכזיים:

- **CSRF Protection** דרך Flask-WTF.
- **XSS Mitigation**: סינון Markdown/HTML עם `bleach`.
- **Password Policy**: דרישה לאותיות, מספרים ותו מיוחד.
- **Audit Logging**: תיעוד אירועי אבטחה (למשל login failure, password reset).

### תעבורה מוצפנת TLS או שיטה אחרת

כן. בסביבת Render התעבורה למשתמשים מתבצעת דרך HTTPS (TLS).

### ממשק משתמש אטרקטיבי

כן. יש ממשק Web מלא, אחיד ו־RTL בעברית:

- דפי בית, הרשמה, התחברות, שכחתי סיסמה.
- שאלון עור, שגרת טיפוח מותאמת, קהילה.
- עיצוב CSS מותאם בתיקיית `static/css/`.

### עבודה עם בסיס נתונים או שמירה לקבצים (JSON)

כן:

- **בסיס נתונים**: SQLite בפיתוח / PostgreSQL בפרודקשן (`DATABASE_URL`).
- **JSON**: תשובות שאלון נשמרות כ־JSON בטבלאות (`questionnaire_json`, `answers_json`).

---

## התקנה (פעם ראשונה)

```text
cd personal_skin
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
py -3 -m pip install -r requirements.txt
```

ב־Linux/macOS ניתן להחליף את הפעלת ה־venv ב־`source .venv/bin/activate`.

---

## הפעלה, עצירה והפעלה מחדש

כל הפקודות מניחות שאתם בספריית שורש הפרויקט (`personal_skin`) ושה־venv מופעל אם משתמשים בו.

### הפעלה (הרצת שרת הפיתוח)

```text
py -3 run.py
```

ברירת המחדל: `http://127.0.0.1:5000` — `debug=True` (שרת הפיתוח של Flask).

אלטרנטיבה מקובלת:

```text
set FLASK_APP=run.py
py -3 -m flask run --host 127.0.0.1 --port 5000
```

(ב־PowerShell: `$env:FLASK_APP="run.py"` לפני `flask run`.)

### עצירה

- בחלון הטרמינל שבו רץ השרת: **Ctrl+C** (SIGINT) — עוצר את התהליך.

### הפעלה מחדש

1. עצירה עם **Ctrl+C**.
2. הרצה שוב של `py -3 run.py` (או `flask run` כמעלה).

### הערות לסביבת ייצור

- הקוד ב־`run.py` מיועד ל**פיתוח** (שרת מובנה של Flask). לייצור מומלץ שרת WSGI (למשל Gunicorn בלינוקס, Waitress בווינדוס) מאחורי reverse proxy עם HTTPS.
- משתנה סביבה **`FLASK_CONFIG`**: `development` (ברירת מחדל) או `production` — ראו `app/config.py` (ב־production מוגדר `DEBUG = False`).

---

## הגדרות (קובץ `.env`)

1. העתיקו `.env.example` ל־`.env` בשורש הפרויקט.
2. **`FLASK_SECRET_KEY`** — מחרוזת אקראית ארוכה לחתימת סשן ו־CSRF; **חובה לשנות בייצור**.
3. **`OPENAI_API_KEY`** — אופציונלי. ללא מפתח, או אם ה־SDK/הקריאה נכשלים, תופעל שגרת הגיבוי.
4. **`OPENAI_MODEL`** — אופציונלי; ברירת מחדל בקוד: `gpt-4o-mini`.
5. **`DATABASE_URL`** — אופציונלי; אם לא מוגדר, משתמשים ב־`sqlite:///personal_skin.db`.
6. **`FLASK_CONFIG`** — `development` או `production`.

---

## פריסה ל-Render (URL קבוע)

כדי לקבל URL ציבורי קבוע לאפליקציה, הפרויקט כולל כעת קובץ `render.yaml` עם הגדרות ברירת מחדל ל-Web Service.

### מה נוסף בפרויקט לצורך Render

- `render.yaml` — הגדרת שירות Render (build/start/env).
- `wsgi.py` — נקודת כניסה לשרת production (`wsgi:app`).
- `gunicorn` ו־`psycopg2-binary` נוספו ל־`requirements.txt`.
- בסיס נתונים מנוהל (`Render Postgres`) מוגדר ב־`render.yaml` ומחובר דרך `DATABASE_URL`.

### שלבי Deploy

1. דחפו את הקוד ל־GitHub (כולל `render.yaml` ו־`wsgi.py`).
2. ב־Render בחרו **New +** -> **Blueprint** (מומלץ, מזהה `render.yaml`) או **Web Service**.
3. חברו את הריפו ובצעו deploy.
4. ב־Environment Variables הגדירו לפחות:
   - `OPENAI_API_KEY` (אם רוצים יצירת שגרה דרך מודל)
   - `FLASK_SECRET_KEY` (אם לא משתמשים ב־`generateValue` מה־Blueprint)
   - אופציונלי: `OPENAI_MODEL`
5. לאחר deploy תקבלו URL בסגנון:
   - `https://personal-skin.onrender.com`

### חשוב לגבי 24/7

- URL של Render הוא קבוע כל עוד שם השירות נשאר קבוע.
- כדי שהשירות יהיה פעיל **24/7 ללא sleep**, השתמשו בתוכנית בתשלום (למשל `Starter`).
- בתוכניות חינמיות שירותים עשויים \"להירדם\" לאחר חוסר פעילות.
- כדי שכל המשתמשים יראו אותם שיתופים מכל מחשב, חובה לעבוד עם `DATABASE_URL` של Postgres (ולא SQLite מקומי).

---

## למפתחים

### טכנולוגיות (סטאק)

| שכבה | טכנולוגיה |
|------|-----------|
| שפת שרת | Python 3 |
| מסגרת ווב | Flask 3 |
| ORM / DB | Flask-SQLAlchemy, SQLite (ברירת מחדל) |
| אימות | Flask-Login, סיסמאות ב־hash (Werkzeug) |
| טפסים / CSRF | Flask-WTF, WTForms, `email-validator` |
| תצוגת טקסט עשיר | `markdown`, `bleach` (סינון HTML), `markupsafe` |
| הגדרות | `python-dotenv` |
| AI (אופציונלי) | OpenAI Python SDK (`openai`), Chat Completions |

### מבנה תיקיות

| נתיב | תיאור |
|------|--------|
| `run.py` | נקודת כניסה; יוצר אפליקציה עם `FLASK_CONFIG` |
| `app/__init__.py` | `create_app`, רישום blueprints, `db.create_all()` |
| `app/config.py` | `DevelopmentConfig` / `ProductionConfig` |
| `app/extensions.py` | `SQLAlchemy`, `LoginManager` |
| `app/models.py` | `User`, `SkinProfile`, `Routine`, `CommunityShare` |
| `app/auth/` | הרשמה, התחברות, התנתקות |
| `app/questionnaire/` | שאלון ושגרה |
| `app/community/` | פיד ושיתוף |
| `app/services/routine_ai.py` | יצירת שגרה (OpenAI או גיבוי) |
| `app/utils.py` | פילטר Jinja `markdown_safe` |
| `templates/` | תבניות HTML (עברית) |
| `static/css/` | עיצוב |

### פרוטוקולים והתנהגות טכנית

- **HTTP**: הדפדפן מדבר עם שרת Flask ב־HTTP מקומי (פיתוח). בייצור יש להפעיל **HTTPS** מול המשתמש (למשל TLS ב־reverse proxy).
- **סשן ואימות**: Flask-Login מזהה משתמש לפי סשן; דפים שדורשים התחברות מפנים ל־`/login` (`login_manager.login_view`).
- **CSRF**: `WTF_CSRF_ENABLED = True` (ברירת מחדל); טפסי WTForms כוללים אסימון CSRF.
- **מסד נתונים**: SQLite קובץ מקומי; לגיבוי — העתקת קובץ ה־`.db` (כשהשרת לא כותב אליו, או אחרי עצירה נקייה).
- **OpenAI**: נעשה שימוש ב־**Chat Completions API** (`client.chat.completions.create`). התוכן נשלח כ־prompt מערכת + משתמש; אין בפרויקט זה endpoint REST חיצוני ללקוח — רק שרת־ל־שרת מול OpenAI.
- **Markdown**: תוכן שגרה ופוסטים מעובר דרך Markdown ואז **Bleach** עם רשימת תגים מותרים — להפחתת XSS.

### דיווח על באגים ובקשות

- **מאגר Git**: ניתן לדווח באמצעות **Issues** ב־GitHub (אם הפרויקט מופיע שם), או בערוץ שבו הצוות מנהל משימות.
- מומלץ לצרף: גרסת Python, מערכת הפעלה, צעדים לשחזור, פלט שגיאה מהטרמינל (ללא מפתחות API או סיסמאות), וצילום מסך אם רלוונטי.
- אל תדביקו ל־Issues את תוכן `.env` או מפתחות.

### סקריפט עזר (אופציונלי)

- `upload-to-github.ps1` — סקריפט PowerShell לעזרה בהעלאת המאגר ל־GitHub (דורש `git` ו־`gh`). לא נדרש להרצת האפליקציה.

---

## הערה משפטית

ההמלצות באפליקציה מיועדות להסבר כללי בלבד ואינן תחליף לייעוץ רפואי, רוקחי או מקצועי.
