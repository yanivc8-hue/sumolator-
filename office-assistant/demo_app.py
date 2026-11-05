"""הדגמה מקומית של העוזר, בלי מערכת המשימות.

    pip install flask anthropic
    python demo_app.py      # ואז לפתוח http://localhost:5055
"""
from flask import Flask

from assistant_ai import assistant_bp

app = Flask(__name__)
app.register_blueprint(assistant_bp)

PAGE = """<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>הדגמה – עוזר AI</title></head>
<body style="font-family:Arial;background:#f7f8f6;padding:24px">
<h2>לוח משימות (הדגמה)</h2>
<div style="background:#fff;border:1px solid #ddd;border-radius:10px;padding:14px;max-width:520px">
<b>עמרני אייל</b> – התאמת בנק לאוקטובר<br><small>אחראית: נינה · יעד 09/11</small></div>
<script>
window.assistantContext = () => "לקוח: עמרני אייל\\nמשימה: התאמת בנק לאוקטובר\\nאחראית: נינה\\nיעד: 09/11";
</script>
<script src="/assistant/static/assistant-widget.js" defer></script>
</body></html>"""


@app.get("/")
def index():
    return PAGE


if __name__ == "__main__":
    app.run(port=5055, debug=True)
