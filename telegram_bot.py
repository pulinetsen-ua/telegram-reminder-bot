import requests
import time
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

# ─── Настройки ───────────────────────────────────────────────────────────────
BOT_TOKEN = "8952145944:AAGujDqRN8BcshBgjH8Ll_05CpmVaKczC4w"
SHEETS_URL = "https://script.google.com/macros/s/AKfycbyFYpMeGjbE3ufAlz7n3_WfIWBW-3z-f18RTiJohfHdAtmPoNm_PQ3wwHFtN4sFMUWG/exec"

REMINDER_HOUR   = 9
REMINDER_MINUTE = 15
PORT = 10000  # Render использует этот порт
# ─────────────────────────────────────────────────────────────────────────────

API = f"https://api.telegram.org/bot{BOT_TOKEN}"
user_states = {}


# ─── HTTP-сервер (нужен для Render) ──────────────────────────────────────────

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")
    def log_message(self, format, *args):
        pass  # отключаем лишние логи

def run_http_server():
    server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
    server.serve_forever()


# ─── Telegram ─────────────────────────────────────────────────────────────────

def get_updates(offset):
    try:
        r = requests.get(f"{API}/getUpdates", params={"timeout": 30, "offset": offset}, timeout=35)
        return r.json().get("result", [])
    except Exception:
        return []


def send(chat_id, text):
    try:
        requests.post(f"{API}/sendMessage", json={"chat_id": chat_id, "text": text}, timeout=10)
    except Exception as e:
        print(f"Ошибка отправки: {e}")


# ─── Google Sheets ────────────────────────────────────────────────────────────

def save_to_sheets(user_id, date, description):
    try:
        r = requests.post(SHEETS_URL,
                          json={"id": str(user_id), "date": date, "description": description},
                          timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"Ошибка записи в таблицу: {e}")
        return False


def get_todays_tasks(date_str):
    try:
        r = requests.get(SHEETS_URL,
                         params={"action": "get_today", "date": date_str},
                         timeout=10)
        data = r.json()
        if data.get("status") == "ok":
            return data.get("tasks", [])
    except Exception as e:
        print(f"Ошибка чтения таблицы: {e}")
    return []


# ─── Ежедневные напоминания ───────────────────────────────────────────────────

def send_reminders():
    today = datetime.now().strftime("%d.%m.%y")
    print(f"[{datetime.now().strftime('%H:%M')}] Проверяю задачи на {today}...")
    tasks = get_todays_tasks(today)
    if not tasks:
        print("  Задач на сегодня нет.")
        return
    for task in tasks:
        chat_id = task.get("id")
        desc    = task.get("description", "")
        send(chat_id, f"🔔 Напоминание на сегодня:\n📝 {desc}")
        print(f"  → Отправлено {chat_id}: {desc}")


def reminder_worker():
    sent_on = None
    while True:
        now = datetime.now()
        if now.hour == REMINDER_HOUR and now.minute == REMINDER_MINUTE:
            today = now.strftime("%Y-%m-%d")
            if sent_on != today:
                send_reminders()
                sent_on = today
        time.sleep(30)


# ─── Обработка команд бота ────────────────────────────────────────────────────

def handle(update):
    msg = update.get("message")
    if not msg:
        return

    chat_id = msg["chat"]["id"]
    text = msg.get("text", "").strip()

    if text == "/add":
        user_states[chat_id] = {"state": "waiting_date"}
        send(chat_id, "📅 Введи дату напоминания в формате ДД.ММ.ГГ\n(например: 20.06.26)")
        return

    if text == "/cancel":
        if chat_id in user_states:
            del user_states[chat_id]
        send(chat_id, "❌ Отменено.")
        return

    if chat_id in user_states:
        state = user_states[chat_id]["state"]

        if state == "waiting_date":
            parts = text.split(".")
            if len(parts) != 3 or not all(p.isdigit() for p in parts):
                send(chat_id, "⚠️ Неверный формат. Введи дату как ДД.ММ.ГГ, например: 20.06.26")
                return
            user_states[chat_id]["date"] = text
            user_states[chat_id]["state"] = "waiting_desc"
            send(chat_id, f"✅ Дата: {text}\n\n📝 Теперь введи описание задачи:")

        elif state == "waiting_desc":
            date = user_states[chat_id]["date"]
            desc = text
            del user_states[chat_id]
            ok = save_to_sheets(chat_id, date, desc)
            if ok:
                send(chat_id, f"✅ Напоминание добавлено!\n📅 {date}\n📝 {desc}")
            else:
                send(chat_id, "❌ Ошибка при сохранении. Проверь настройки скрипта.")
        return

    send(chat_id, "Привет! Используй /add чтобы добавить напоминание.")


# ─── Запуск ───────────────────────────────────────────────────────────────────

def main():
    print(f"🤖 Бот запущен. Напоминания в {REMINDER_HOUR:02d}:{REMINDER_MINUTE:02d}.")

    # HTTP-сервер для Render
    threading.Thread(target=run_http_server, daemon=True).start()
    print(f"🌐 HTTP-сервер запущен на порту {PORT}")

    # Поток напоминаний
    threading.Thread(target=reminder_worker, daemon=True).start()

    offset = 0
    while True:
        updates = get_updates(offset)
        for upd in updates:
            handle(upd)
            offset = upd["update_id"] + 1
        if not updates:
            time.sleep(1)


if __name__ == "__main__":
    main()
