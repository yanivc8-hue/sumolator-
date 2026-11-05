# עוזר AI – מערכת המשימות

כפתור "✨ עוזר AI" בלוח המשימות. העובדות שואלות "איך עושים", "איפה מוצאים" או "למי מעבירים",
והעוזר עונה לפי נהלי המשרד שבתיקייה `knowledge/`.

## מה יש כאן
| קובץ | מה הוא עושה |
|---|---|
| `assistant_ai.py` | רכיב לשרת ה-Flask: הנתיב `/api/assistant` ששולח את השאלה ל-Claude |
| `static/assistant-widget.js` | הכפתור וחלון השיחה בלוח |
| `knowledge/*.md` | הנהלים. כל כותרת `##` היא נושא. **לעבור ולהשלים את מה שמסומן [להשלים]** |
| `demo_app.py` | הדגמה מקומית בלי מערכת המשימות |

## התקנה במערכת המשימות
1. מעתיקים את התיקייה `office-assistant` לתיקיית המערכת.
2. `pip install anthropic`
3. בקובץ השרת (איפה שנוצר `app = Flask(...)`):
   ```python
   import sys; sys.path.insert(0, "office-assistant")
   from assistant_ai import assistant_bp
   app.register_blueprint(assistant_bp)
   ```
4. בדף הלוח, לפני `</body>`:
   ```html
   <script src="/assistant/static/assistant-widget.js" defer></script>
   ```
5. ב-`.env`: `ANTHROPIC_API_KEY=sk-ant-...` (מפתח מ-platform.claude.com). המפתח נשאר בשרת ולא מגיע לדפדפן.
6. כדי שהעוזר יידע על איזו משימה עובדים, הלוח מגדיר:
   ```js
   window.assistantContext = () => `לקוח: ${task.client}\nמשימה: ${task.title}\nאחראית: ${task.owner}`;
   ```

בלי מפתח API העוזר עדיין עובד, ומחזיר את הנוהל המתאים מתוך `knowledge/`.

## עלויות
- ברירת מחדל: `claude-opus-5-5` במאמץ נמוך. הנהלים נשמרים במטמון, כך ששאלות חוזרות זולות יותר.
- לחיסכון: `ASSISTANT_MODEL=claude-haiku-5-5` ב-`.env`.
- מומלץ להגדיר תקרת הוצאה חודשית ב-platform.claude.com.

## עדכון הנהלים
עורכים את קבצי ה-md בתיקייה `knowledge/`. אין צורך להפעיל את השרת מחדש – הקבצים נקראים בכל שאלה.
