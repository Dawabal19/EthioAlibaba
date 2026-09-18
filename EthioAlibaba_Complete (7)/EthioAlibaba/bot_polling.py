"""EthioAlibaba Admin Bot — Long Polling Mode.

No public URL / HTTPS needed. Just run this alongside (or instead of) the webhook.
    python bot_polling.py

Commands (send to your bot in Telegram):
    /start                       — welcome message
    /track ETHA1B2C3             — view one order
    /orders                      — last 10 orders
    /status ETHA1B2C3 New Status — update order status
    /help                        — command list
"""
import os, time, sqlite3, requests
from datetime import datetime

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8986314898:AAFghduqDUPRLZVIOWgsWNZw8jwmkHMoyy4")
CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "1931570585")
DB_PATH   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ethioalibaba.db")
API = f"https://api.telegram.org/bot{BOT_TOKEN}"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def reply(chat_id, text):
    requests.post(f"{API}/sendMessage",
                  json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
                  timeout=10)

def handle(text, chat_id):
    if str(chat_id) != str(CHAT_ID):
        return reply(chat_id, "⛔ This bot is private.")
    text = text.strip()

    if text == "/start":
        reply(chat_id, "👋 EthioAlibaba Admin Bot\n\nCommands:\n/track ORDER_ID\n/orders\n/status ORDER_ID TEXT\n/help")

    elif text.startswith("/track"):
        parts = text.split()
        if len(parts) < 2:
            return reply(chat_id, "❌ Usage: /track ETHA1B2C3")
        oid = parts[1].upper()
        conn = get_db()
        order = conn.execute("SELECT * FROM orders WHERE id = ?", (oid,)).fetchone()
        history = conn.execute("SELECT status, time, note FROM status_history WHERE order_id = ? ORDER BY id", (oid,)).fetchall()
        conn.close()
        if not order:
            return reply(chat_id, f"❌ Order #{oid} not found.")
        hist = "\n".join([f"• {h['status']} — {h['time']}" for h in history]) or "No history"
        reply(chat_id,
              f"📦 Order #{order['id']}\n━━━━━━━━━━━━\n"
              f"📋 Status: {order['status']}\n"
              f"📦 {order['category']} x {order['quantity']}\n"
              f"👤 {order['full_name']} | 📱 {order['phone']}\n"
              f"📍 {order['city']} | 💴 {order['total_etb']:,.0f} ETB\n\n"
              f"📜 History:\n{hist}")

    elif text == "/orders":
        conn = get_db()
        rows = conn.execute("SELECT id, category, status, total_etb, created_at FROM orders ORDER BY created_at DESC LIMIT 10").fetchall()
        conn.close()
        if not rows:
            return reply(chat_id, "📭 No orders yet.")
        lines = [f"#{r['id']} | {r['category']} | {r['status']} | {r['total_etb']:,.0f} ETB" for r in rows]
        reply(chat_id, "📋 Last 10 Orders\n━━━━━━━━━━━━\n" + "\n".join(lines))

    elif text.startswith("/status"):
        parts = text.split(maxsplit=2)
        if len(parts) < 3:
            return reply(chat_id, "❌ Usage: /status ORDER_ID New Status")
        oid, new_status = parts[1].upper(), parts[2]
        conn = get_db()
        order = conn.execute("SELECT id FROM orders WHERE id = ?", (oid,)).fetchone()
        if not order:
            conn.close()
            return reply(chat_id, f"❌ Order #{oid} not found.")
        conn.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, oid))
        conn.execute("INSERT INTO status_history (order_id, status, time, note) VALUES (?, ?, ?, ?)",
                     (oid, new_status, datetime.now().strftime("%H:%M"), "Updated via Telegram bot"))
        conn.commit()
        conn.close()
        reply(chat_id, f"✅ Order #{oid} → {new_status}")

    elif text == "/help":
        reply(chat_id, "ℹ️ Commands\n/track ORDER_ID\n/orders\n/status ORDER_ID TEXT\n/help")
    else:
        reply(chat_id, "🤖 Unknown command. Send /help")

def main():
    print("🤖 EthioAlibaba Polling Bot started...")
    offset = 0
    while True:
        try:
            r = requests.get(f"{API}/getUpdates",
                             params={"offset": offset, "timeout": 30}, timeout=40)
            data = r.json()
            for upd in data.get("result", []):
                offset = upd["update_id"] + 1
                msg = upd.get("message")
                if msg and msg.get("text"):
                    handle(msg["text"], msg["chat"]["id"])
        except requests.exceptions.Timeout:
            continue
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
