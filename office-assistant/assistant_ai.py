"""עוזר AI למערכת המשימות של המשרד.

רכיב Flask עצמאי (Blueprint) שעונה לעובדות על שאלות "איך עושים" ו"איפה מוצאים",
לפי קבצי הנהלים בתיקייה knowledge/.

חיבור לשרת הקיים (שלוש שורות):

    from assistant_ai import assistant_bp
    app.register_blueprint(assistant_bp)

ובקובץ .env:

    ANTHROPIC_API_KEY=sk-ant-...
    ASSISTANT_MODEL=claude-opus-5-5   # אופציונלי. לחיסכון: claude-haiku-5-5

בלי מפתח API העוזר עונה מתוך הנהלים בחיפוש מילות מפתח בלבד.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

from flask import Blueprint, jsonify, request, send_from_directory

try:
    import anthropic
except ImportError:  # העוזר עובד גם בלי הספרייה, במצב חיפוש בנהלים
    anthropic = None

log = logging.getLogger("assistant_ai")

BASE_DIR = Path(__file__).resolve().parent
KNOWLEDGE_DIR = Path(os.environ.get("ASSISTANT_KNOWLEDGE_DIR", BASE_DIR / "knowledge"))
STATIC_DIR = BASE_DIR / "static"

MODEL = os.environ.get("ASSISTANT_MODEL", "claude-opus-5-5")
EFFORT = os.environ.get("ASSISTANT_EFFORT", "low")
MAX_TOKENS = 4000
MAX_HISTORY = 12          # כמה הודעות קודמות נשלחות ל-Claude
MAX_QUESTION_CHARS = 2000
MAX_CONTEXT_CHARS = 3000

assistant_bp = Blueprint("assistant_ai", __name__)


# ---------------------------------------------------------------- knowledge

def load_knowledge() -> list[dict]:
    """קורא את קבצי הנהלים. כל כותרת ## היא נושא נפרד לחיפוש."""
    sections = []
    for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        doc_title = path.stem
        m = re.search(r"^#\s+(.+)$", text, re.M)
        if m:
            doc_title = m.group(1).strip()
        parts = re.split(r"^##\s+", text, flags=re.M)
        for part in parts[1:]:
            title, _, body = part.partition("\n")
            sections.append({"doc": doc_title, "title": title.strip(), "body": body.strip()})
    return sections


def knowledge_text() -> str:
    out = []
    for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        out.append(f"<document name=\"{path.stem}\">\n{path.read_text(encoding='utf-8').strip()}\n</document>")
    return "\n\n".join(out)


_WORD = re.compile(r"[\w֐-׿]+")
_STOP = set("""מה איך איפה למי מי מתי למה של את על עם יש אין לי לו לה זה זו אני את אתה הוא היא או כל לא כן
עושים עושה לעשות צריך צריכה אפשר רוצה רוצים מוצאים מוצא למצוא עם גם רק כבר עוד אם כי הזה הזאת""".split())


def _norm_words(text: str) -> list[str]:
    words = []
    for w in _WORD.findall(text.lower()):
        if w in _STOP:
            continue
        # הסרת אותיות שימוש נפוצות בתחילת מילה (ה, ו, ב, ל, מ, ש, כ)
        forms = {w}
        if len(w) > 3 and w[0] in "הובלמשכ":
            forms.add(w[1:])
        for f in list(forms):  # סיומות רבים / סמיכות: כרטיסים, כרטיסי -> כרטיס
            if len(f) > 4 and f[-2:] in ("ים", "ות"):
                forms.add(f[:-2])
            elif len(f) > 4 and f[-1] == "י":
                forms.add(f[:-1])
        words.extend(forms)
    return [w for w in words if len(w) > 1]


def search_knowledge(question: str, limit: int = 2) -> list[dict]:
    q = set(_norm_words(question))
    scored = []
    for sec in load_knowledge():
        title_words = set(_norm_words(sec["title"]))
        body_words = set(_norm_words(sec["body"]))
        score = 3 * len(q & title_words) + len(q & body_words)
        if score >= 2:
            scored.append((score, sec))
    scored.sort(key=lambda x: -x[0])
    return [s for _, s in scored[:limit]]


# ---------------------------------------------------------------- Claude

SYSTEM_INTRO = """אתה העוזר הפנימי של משרד "יניב כהן רואי חשבון". אתה עונה לעובדות המשרד (נינה, מאשה) ולי יניב,
בתוך מערכת המשימות, על שאלות כמו: איך מבצעים פעולה (התאמת בנק, התאמת כרטיסים, קליטת עובד וכו'),
איפה מוצאים נתון או מסמך, ולמי מעבירים נושא.

כללים:
- ענה בעברית, קצר ומעשי. כשיש תהליך, כתוב צעדים ממוספרים.
- הסתמך קודם כל על הנהלים של המשרד שבהמשך. אם הנוהל של המשרד לא מכסה את השאלה, אפשר לענות מידע מקצועי כללי,
  אבל ציין במפורש שזה לא מתוך נהלי המשרד.
- אם אינך בטוח, אמור זאת והצע לשאול את יניב. אל תמציא שמות של לקוחות, סכומים, מועדים או קישורים.
- אם נשלחו פרטי המשימה הפתוחה, התייחס אליהם בתשובה.
- טקסט פשוט: בלי טבלאות, בלי כותרות Markdown. מותר להדגיש מילה בודדת עם **.

נהלי המשרד:
"""


_client = None


def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def ai_enabled() -> bool:
    return anthropic is not None and bool(os.environ.get("ANTHROPIC_API_KEY"))


def ask_claude(question: str, history: list[dict], context: str) -> str:
    messages = []
    for m in history[-MAX_HISTORY:]:
        if m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str) and m["content"].strip():
            messages.append({"role": m["role"], "content": m["content"][:MAX_QUESTION_CHARS * 2]})
    # ה-API דורש שהשיחה תתחיל בהודעת משתמש ושההודעות יתחלפו
    while messages and messages[0]["role"] != "user":
        messages.pop(0)
    cleaned = []
    for m in messages:
        if cleaned and cleaned[-1]["role"] == m["role"]:
            cleaned[-1] = m
        else:
            cleaned.append(m)
    if cleaned and cleaned[-1]["role"] == "user":
        cleaned.pop()

    user_text = question
    if context:
        user_text = f"<open_task>\n{context}\n</open_task>\n\n{question}"
    cleaned.append({"role": "user", "content": user_text})

    response = _get_client().beta.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": EFFORT},
        system=[{
            "type": "text",
            "text": SYSTEM_INTRO + knowledge_text(),
            "cache_control": {"type": "ephemeral"},  # הנהלים נשמרים במטמון, כך ששאלות חוזרות זולות יותר
        }],
        messages=cleaned,
    )
    if response.stop_reason == "refusal":
        return "לא אוכל לענות על השאלה הזו. נסי לנסח אחרת או לשאול את יניב."
    text = "".join(b.text for b in response.content if getattr(b, "type", "") == "text").strip()
    if response.stop_reason == "max_tokens":
        text += "\n\n(התשובה נקטעה. אפשר לבקש המשך.)"
    return text or "לא התקבלה תשובה. נסי שוב."


# ---------------------------------------------------------------- routes

@assistant_bp.post("/api/assistant")
def api_assistant():
    data = request.get_json(silent=True) or {}
    question = str(data.get("question", "")).strip()[:MAX_QUESTION_CHARS]
    if not question:
        return jsonify(error="שאלה ריקה"), 400
    history = data.get("history") if isinstance(data.get("history"), list) else []
    context = str(data.get("context") or "")[:MAX_CONTEXT_CHARS]

    hits = search_knowledge(question)

    if ai_enabled():
        try:
            answer = ask_claude(question, history, context)
            return jsonify(answer=answer, source="ai")
        except anthropic.AuthenticationError:
            log.error("assistant: invalid ANTHROPIC_API_KEY")
            note = "מפתח ה-API לא תקין"
        except anthropic.RateLimitError:
            note = "יותר מדי בקשות כרגע, נסי שוב בעוד דקה"
        except anthropic.APIStatusError as e:
            log.error("assistant: API error %s: %s", e.status_code, e.message)
            note = "שגיאה בשירות ה-AI"
        except anthropic.APIConnectionError:
            note = "אין חיבור לשירות ה-AI"
        return jsonify(answer=_kb_answer(hits), source="kb", note=note)

    return jsonify(answer=_kb_answer(hits), source="kb")


def _kb_answer(hits: list[dict]) -> str:
    if not hits:
        return "לא מצאתי את זה בנהלים של המשרד. נסי לנסח במילים אחרות, או לשאול את יניב."
    return "\n\n".join(f"**{h['title']}**\n{h['body']}" for h in hits)


@assistant_bp.get("/api/assistant/topics")
def api_topics():
    return jsonify(topics=[s["title"] for s in load_knowledge()], ai=ai_enabled())


@assistant_bp.get("/assistant/static/<path:filename>")
def assistant_static(filename):
    return send_from_directory(STATIC_DIR, filename)
