from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer
from datetime import datetime
import sqlite3
import uuid
import os
import requests
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ethioalibaba-secret-key-2026-change-in-production'
# Database always next to this file (same folder as bot_polling.py)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['DATABASE'] = os.path.join(BASE_DIR, 'ethioalibaba.db')
CORS(app, resources={r"/api/*": {"origins": "*"}})

# ========== TELEGRAM CONFIG ==========
# Set these as environment variables in production!
#   export TELEGRAM_BOT_TOKEN="your-bot-token"
#   export TELEGRAM_CHAT_ID="your-chat-id"
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8986314898:AAFghduqDUPRLZVIOWgsWNZw8jwmkHMoyy4")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "1931570585")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

# ========== PRICING ==========
EXCHANGE_RATE = 55.0
CUSTOMS_RATE = 0.15
SERVICE_FEE = 5.0

SHIPPING = {
    "Electronics": {"base": 5.0, "per_kg": 11.0},
    "Fashion":     {"base": 3.0, "per_kg": 10.0},
    "Machinery":   {"base": 15.0, "per_kg": 12.0},
    "Home & Garden":{"base": 8.0, "per_kg": 11.0},
    "Beauty":      {"base": 3.0, "per_kg": 10.0},
    "Other":       {"base": 6.0, "per_kg": 11.0}
}

DELIVERY = {
    "Addis Ababa": 0, "Adama": 3, "Bahir Dar": 4,
    "Dire Dawa": 4, "Hawassa": 3.5, "Mekelle": 5,
    "Jimma": 4, "Gondar": 4.5, "Other": 6
}

# ========== TOKEN SERIALIZER ==========
token_serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

# ========== DATABASE SETUP ==========
def get_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT, phone TEXT, email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY, user_id INTEGER,
            product_link TEXT, category TEXT, quantity INTEGER,
            unit_price REAL, weight REAL,
            product_cost REAL, shipping_cost REAL, customs_tax REAL,
            local_delivery REAL, service_fee REAL,
            total_usd REAL, total_etb REAL,
            full_name TEXT, phone TEXT, address TEXT, city TEXT,
            telebirr_id TEXT, notes TEXT, lat TEXT, lng TEXT,
            status TEXT DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS status_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT, status TEXT, time TEXT, note TEXT,
            FOREIGN KEY (order_id) REFERENCES orders(id)
        )
    """)
    conn.commit()
    conn.close()
    print("✅ Database ready")

init_db()

# ========== HELPERS ==========
def telegram(text):
    try:
        r = requests.post(TELEGRAM_API, json={
            "chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"
        }, timeout=10)
        return r.json().get("ok", False)
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

def send_telegram_reply(chat_id, text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10
        )
    except Exception as e:
        print(f"Reply error: {e}")

def generate_token(user_id):
    return token_serializer.dumps({"user_id": user_id})

def verify_token(token):
    try:
        data = token_serializer.loads(token, max_age=86400*7)
        return data.get("user_id")
    except:
        return None

def get_current_user():
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]
        user_id = verify_token(token)
        if user_id:
            conn = get_db()
            user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            conn.close()
            if user:
                return dict(user)
    return None

def row_to_dict(row):
    return {key: row[key] for key in row.keys()}

# ========== FRONTEND PAGES ==========
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register')
def register_page():
    return render_template('register.html')

# ========== AUTH ROUTES ==========
@app.route('/api/register', methods=['POST'])
def register():
    d = request.json
    username = d.get('username', '').strip().lower()
    password = d.get('password', '')
    full_name = d.get('fullName', '')
    phone = d.get('phone', '')
    email = d.get('email', '')

    if not username or not password:
        return jsonify({"success": False, "error": "Username and password required"}), 400
    if len(password) < 6:
        return jsonify({"success": False, "error": "Password must be at least 6 characters"}), 400

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, full_name, phone, email) VALUES (?, ?, ?, ?, ?)",
            (username, generate_password_hash(password), full_name, phone, email)
        )
        conn.commit()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        token = generate_token(user['id'])
        conn.close()
        return jsonify({
            "success": True, "token": token,
            "user": {"id": user['id'], "username": user['username'], "fullName": user['full_name'], "phone": user['phone']}
        })
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"success": False, "error": "Username already exists"}), 409

@app.route('/api/login', methods=['POST'])
def login():
    d = request.json
    username = d.get('username', '').strip().lower()
    password = d.get('password', '')

    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()

    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({"success": False, "error": "Invalid username or password"}), 401

    token = generate_token(user['id'])
    return jsonify({
        "success": True, "token": token,
        "user": {"id": user['id'], "username": user['username'], "fullName": user['full_name'], "phone": user['phone']}
    })

@app.route('/api/me', methods=['GET'])
def me():
    user = get_current_user()
    if not user:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    return jsonify({"success": True, "user": {
        "id": user['id'], "username": user['username'],
        "fullName": user['full_name'], "phone": user['phone'], "email": user['email']
    }})

# ========== CALCULATE ==========
@app.route('/api/calculate', methods=['POST'])
def calculate():
    try:
        d = request.json
        cat = d.get('category', 'Other')
        qty = int(d.get('quantity', 1) or 1)
        price = float(d.get('unitPrice', 0) or 0)
        weight = float(d.get('weight', 1) or 1)
        city = d.get('city', 'Addis Ababa')

        s = SHIPPING.get(cat, SHIPPING["Other"])
        ship = (s["base"] + s["per_kg"] * weight) * qty
        product = price * qty
        tax = product * CUSTOMS_RATE
        delivery = DELIVERY.get(city, 6) * qty
        sub = product + ship + tax + delivery
        total_usd = sub + SERVICE_FEE
        total_etb = total_usd * EXCHANGE_RATE

        return jsonify({
            "success": True,
            "breakdown": {
                "productCost": round(product, 2), "quantity": qty, "unitPrice": round(price, 2),
                "shippingCost": round(ship, 2),
                "shippingDetails": f"Air Cargo: Base ${s['base']} + ${s['per_kg']}/kg x {weight}kg | 10-15 days",
                "customsTax": round(tax, 2), "customsRate": "15%",
                "localDelivery": round(delivery, 2), "city": city,
                "serviceFee": SERVICE_FEE, "subtotal": round(sub, 2),
                "totalUSD": round(total_usd, 2), "totalETB": round(total_etb, 2),
                "exchangeRate": EXCHANGE_RATE
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ========== SEND ORDER ==========
@app.route('/api/send-order', methods=['POST'])
def send_order():
    try:
        d = request.json
        user = get_current_user()
        oid = "ETH" + uuid.uuid4().hex[:6].upper()
        bd = d.get('priceBreakdown', {})
        lat = d.get('lat', '')
        lng = d.get('lng', '')

        loc_link = f"https://maps.google.com/?q={lat},{lng}" if lat and lng else "Not shared"
        loc_text = f"\n📍 <b>Location:</b> <a href=\"{loc_link}\">🗺️ View on Maps</a>" if lat and lng else "\n📍 Location: Not shared"

        conn = get_db()
        conn.execute("""
            INSERT INTO orders (id, user_id, product_link, category, quantity, unit_price, weight,
                product_cost, shipping_cost, customs_tax, local_delivery, service_fee,
                total_usd, total_etb, full_name, phone, address, city, telebirr_id,
                notes, lat, lng, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (oid, user['id'] if user else None, d.get('productLink', ''), d.get('category', ''),
            d.get('quantity', 1), d.get('unitPrice', 0), d.get('weight', 1),
            bd.get('productCost', 0), bd.get('shippingCost', 0), bd.get('customsTax', 0),
            bd.get('localDelivery', 0), bd.get('serviceFee', 0), bd.get('totalUSD', 0), bd.get('totalETB', 0),
            d.get('fullName', ''), d.get('phone', ''), d.get('address', ''), d.get('city', ''),
            d.get('telebirrId', ''), d.get('notes', ''), lat, lng, 'Pending'))

        conn.execute("INSERT INTO status_history (order_id, status, time, note) VALUES (?, ?, ?, ?)",
            (oid, 'Order Placed', datetime.now().strftime('%Y-%m-%d %H:%M'), 'Order received and pending review'))
        conn.commit()
        conn.close()

        msg = f"""🛒 <b>NEW ORDER #{oid}</b>
━━━━━━━━━━━━━━━━━━━━
🔗 <b>Product:</b> {d.get('productLink','N/A')[:80]}...
📦 <b>Category:</b> {d.get('category','N/A')} | Qty: {d.get('quantity',1)}
💰 <b>PRICE:</b>
   📦 Product:    ${bd.get('productCost',0):,.2f} USD
   🚢 Shipping:   ${bd.get('shippingCost',0):,.2f} USD
   🏛️ Gumruk:     ${bd.get('customsTax',0):,.2f} USD (15%)
   🚚 Delivery:   ${bd.get('localDelivery',0):,.2f} USD
   🔧 Service:    ${bd.get('serviceFee',0):,.2f} USD
   ─────────────────────────
   💵 <b>TOTAL:</b>     ${bd.get('totalUSD',0):,.2f} USD
   💴 <b>TOTAL:</b>     {bd.get('totalETB',0):,.0f} ETB
👤 <b>Customer:</b> {d.get('fullName','N/A')}
📱 <b>Phone:</b> {d.get('phone','N/A')}
📍 <b>Address:</b> {d.get('address','N/A')}, {d.get('city','N/A')}
💳 <b>Telebirr:</b> {d.get('telebirrId','N/A')}
📝 <b>Notes:</b> {d.get('notes') or 'None'}{loc_text}
⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}
📊 Status: <b>Pending</b>"""

        sent = telegram(msg)
        print(f"✅ Order {oid} saved | Telegram: {'Sent' if sent else 'Failed'}")
        return jsonify({"success": True, "orderId": oid, "telegramSent": sent})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ========== TRACK ORDER ==========
@app.route('/api/track/<oid>', methods=['GET'])
def track(oid):
    conn = get_db()
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (oid.upper(),)).fetchone()
    if not order:
        conn.close()
        return jsonify({"success": False, "error": "Order not found"}), 404
    history = conn.execute("SELECT status, time, note FROM status_history WHERE order_id = ? ORDER BY id", (oid.upper(),)).fetchall()
    conn.close()
    o = row_to_dict(order)
    o['statusHistory'] = [dict(h) for h in history]
    return jsonify({"success": True, "order": o})

# ========== MY ORDERS ==========
@app.route('/api/my-orders', methods=['GET'])
def my_orders():
    user = get_current_user()
    if not user:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    conn = get_db()
    orders = conn.execute(
        "SELECT id, category, quantity, total_usd, total_etb, status, created_at FROM orders WHERE user_id = ? ORDER BY created_at DESC",
        (user['id'],)).fetchall()
    conn.close()
    return jsonify({"success": True, "orders": [dict(o) for o in orders]})

# ========== UPDATE STATUS ==========
@app.route('/api/update-status', methods=['POST'])
def update_status():
    d = request.json
    oid = d.get('orderId', '').upper()
    st = d.get('status', '')
    note = d.get('note', '')

    conn = get_db()
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (oid,)).fetchone()
    if not order:
        conn.close()
        return jsonify({"success": False, "error": "Not found"}), 404

    conn.execute("UPDATE orders SET status = ? WHERE id = ?", (st, oid))
    conn.execute("INSERT INTO status_history (order_id, status, time, note) VALUES (?, ?, ?, ?)",
        (oid, st, datetime.now().strftime('%H:%M'), note or 'Status updated'))
    conn.commit()
    conn.close()

    telegram(f"📊 <b>UPDATE #{oid}</b>\nStatus: <b>{st}</b>\n⏰ {datetime.now().strftime('%H:%M')}")
    return jsonify({"success": True})

# ========== AI CHATBOT ==========
CHATBOT_KNOWLEDGE = {
    "greetings": ["hello", "hi", "hey", "selam", "ሰላም", "ሀይ", "ሀሎ", "good morning", "good afternoon", "good evening"],
    "order": ["how to order", "order", "place order", "ይዘዙ", "እንዴት እንደምናዘዝ", "order yaqetel", "how do i buy", "መሸጥ", "መግዛት", "ዘዝ", "ይዘዙኝ", "buy", "purchase", "ይግዙ", "እንዴት መግዛት", "መሸመት", "alibaba", "አሊባባ", "order form", "order now", "place an order"],
    "payment": ["telebirr", "payment", "pay", "ክፍያ", "ገንዘብ", "how to pay", "ቴሌብር", "መክፈል", "price", "cost", "ዋጋ", "ብር", "birr", "dollar", "usd", "መቼ ክፍያ", "ዋጋው ስንት", "how much", "total cost", "calculate", "calculator", "live price"],
    "delivery": ["delivery", "shipping", "how long", "time", "days", "መላኪያ", "መሸኘት", "እንዴት ይደርሳል", "መቼ", "when", "መቼ ይደርሳል", "delivery time", "shipping time", "መቼ ይመጣል", "days", "weeks", "አየር", "air cargo", "sea", "ship"],
    "tracking": ["track", "where is my order", "status", "tracking", "ትራክ", "ትራኪንግ", "ትዕዛዜ የት አለ", "order yet ale", "my order", "order status", "ትዕዛዜ", "ትዕዛዝ", "ትዕዛዜን መከታተል", "track order", "check order"],
    "customs": ["customs", "tax", "duty", "gumruk", "ጉምሩክ", "ታክስ", "tax yelem", "do i pay customs", "customs fee", "duty fee", "ጉምሩክ ታክስ", "ጉምሩክ ክፍያ", "customs included", "tax included"],
    "categories": ["what can i order", "categories", "products", "ምን ምን አለ", "category", "ዓይነት", "ምንድን ነው", "what do you sell", "what products", "electronics", "fashion", "machinery", "home", "beauty", "phone", "clothes", "shoes"],
    "refund": ["refund", "money back", "return", "return policy", "ገንዘብ መመለስ", "return yelem", "damage", "broken", "wrong item", "not received", "lost", "ተሰበረ", "የተሳሳተ", "አልደረሰኝም", "ጠፋ", "money back guarantee"],
    "contact": ["phone", "call", "contact", "support", "help", "call center", "ስልክ", "አድራሻ", "address", "telegram", "whatsapp", "email", "call me", "ደውል", "እርዳኝ", "help me", "support", "customer service", "agent", "ሰው", "person"],
    "location": ["location", "gps", "map", "address", "where are you", "addis ababa", "location share", "gps location", "my address", "delivery address", "አድራሻ", "አድራሻ መስጠት", "gps share", "location button"],
    "account": ["login", "register", "account", "sign up", "sign in", "username", "password", "my account", "my orders", "profile", "መለያ", "መመዝገብ", "መግባት", "login yelem", "register yelem", "create account", "new account", "የኔ ትዕዛዞች", "orders"],
    "features": ["features", "what can this site do", "how does it work", "website", "app", "function", "capability", "what is ethioalibaba", "about", "who are you", "what do you do", "services", "website features", "what is this"],
    "goodbye": ["bye", "goodbye", "ciao", "bay", "ቻው", "ደህና ሁን", "thank you", "thanks", "አመሰግናለሁ", "መልካም", "see you", "talk later"],
    "complaint": ["slow", "late", "problem", "issue", "error", "bug", "not working", "failed", "የተሳሳተ", "ችግር", "ጥያቄ", "ስህተት", "አይሰራም", "slow delivery", "late delivery", "where is my money", "scam", "fraud", "cheat"],
    "group_buy": ["group", "bulk", "wholesale", "minimum order", "moq", "group buying", "share shipping", "together", "friends", "business", "b2b", "company", "shop", "store", "wholesale", "ቡድን", "ጋር", "አብረን", "business", "company", "shop"]
}

CHATBOT_RESPONSES = {
    "greetings": ["""👋 ሰላም! እኔ EthioAlibaba AI Assistant ነኝ። እንዴት ልረዳዎት እንደምችል ይንገሩኝ።

Hello! How can I help you today?

💡 Try asking:
• 'እንዴት እንደምናዘዝ' (How to order)
• 'ዋጋ' (Price)
• 'መላኪያ' (Delivery)
• 'ትራክ' (Track)"""],
    "order": ["""📦 **እንዴት እንደምናዘዝ:**

1️⃣ Alibaba.com ላይ ምርትዎን ይፈልጉ
2️⃣ የምርቱን ሊንክ ይቅዱ
3️⃣ ወደ EthioAlibaba ድህረ-ገጽ ይመለሱ
4️⃣ 'Place Order' ላይ ይሙሉ
5️⃣ Telebirr ይክፈሉ

✅ እኛ ሁሉንም ነገር እንከታተላለን!"""],
    "payment": ["""💳 **ክፍያ:**

✅ Telebirr ብቻ!
📱 Send to: +251 91 234 5852

💰 Live Calculator ዋጋውን ያሳያል:
• Product Cost
• Shipping ($10-12/kg)
• Customs Tax 15%
• Local Delivery
• Service Fee $5

📊 1 USD = 55 ETB

**All costs included — no hidden fees!**"""],
    "delivery": ["""🚚 **መላኪያ:**

🛫 Ethio-China Air Cargo
💵 $10-12 per kg
⏱️ 10-15 days

📍 Nationwide delivery:
• Addis Ababa (Free)
• Adama, Hawassa, Bahir Dar, Dire Dawa
• Mekelle, Jimma, Gondar

🚪 Door-to-Door!"""],
    "tracking": ["""🔍 **ትራኪንግ:**

**Method 1:** Website → 'Track Order' → Enter Order ID
**Method 2:** Telegram Bot → `/track ETHA1B2C3`
**Method 3:** Login → 'My Orders'

📊 Status: Order Placed → Processing → Shipped → Delivered"""],
    "customs": ["""🏛️ **ጉምሩክ:**

❌ **No extra fees!** Everything included!

Live Calculator shows:
✅ Product Cost
✅ International Shipping
✅ Customs Tax 15%
✅ Local Delivery
✅ Service Fee $5

**One price only — nothing extra!**"""],
    "categories": ["""📦 **ምን ምን ማዘዝ ይቻላል?**

• 📱 Electronics — Phones, accessories, gadgets
• 👕 Fashion — Clothes, shoes, bags, jewelry
• ⚙️ Machinery — Industrial tools, parts
• 🏠 Home & Garden — Furniture, decor, kitchen
• 💄 Beauty — Cosmetics, skincare
• 📦 Other — Toys, sports, automotive

**Almost anything on Alibaba!**"""],
    "refund": ["""🛡️ **ገንዘብ መመለስ:**

✅ Product never arrives → Full refund
✅ Wrong item → Full refund
✅ Damaged in transit → We replace it
✅ Not as described → Full refund

🛡️ Buyer Protection Guarantee
📞 Problem? Call: +251 91 234 5852"""],
    "contact": ["""📞 **አግኙን:**

📱 Phone: +251 91 234 5852
📧 Email: hello@ethioalibaba.com
📍 Address: Addis Ababa, Ethiopia
💬 Telegram/WhatsApp: +251 91 234 5852

⏰ Available 24/7!"""],
    "location": ["""📍 **GPS Location:**

When placing order, click 'Share My Location':
✅ Exact address for delivery
✅ Door-to-door service
✅ No mistakes

**How:** Order form → 'Share My Location' → Allow browser permission → Done!"""],
    "account": ["""👤 **መለያ (Account):**

**Why register?**
• Track your orders
• View order history
• Quick checkout
• Auto-fill details

**How:**
1. Click 'Login / Register'
2. Choose 'Register' tab
3. Enter username, password, details
4. Click 'Create Account'

**Or login with existing account.**"""],
    "features": ["""🌟 **EthioAlibaba Features:**

🛒 Order from Alibaba with Telebirr
💰 Live Price Calculator
📍 GPS Location for delivery
🔍 Track your orders
🤖 AI Chatbot (24/7)
👤 User Account system
📱 Telegram Bot integration
🛡️ Buyer Protection
🚚 Nationwide delivery"""],
    "goodbye": ["""👋 ደህና ሁኑ! ሌላ ጥያቄ ካለዎት በማንኛውም ጊዜ ይመለሱ።

Goodbye! Come back anytime!

📞 Need help? Call: +251 91 234 5852"""],
    "complaint": ["""😔 **ይቅርታ ለችግሩ!**

Please tell us:
• Order ID (if you have one)
• What happened?
• When did it occur?

📞 **Call us directly:** +251 91 234 5852
📧 Email: hello@ethioalibaba.com

We're here to help!"""],
    "group_buy": ["""👥 **ቡድን ግዢ (Group Buying):**

Order together with others:
• Share shipping costs
• Meet MOQ requirements
• Get better prices

💡 **For businesses (B2B):**
• Bulk orders = better rates
• Raw materials, machinery, electronics
• Custom orders accepted

📞 For group buying: +251 91 234 5852"""],
    "default": ["""🤔 ይቅርታ፣ ጥያቄዎትን በትክክል አልገባኝም።

እባክዎን ከእነዚህ ውስጥ አንዱን ይሞክሩ:
• 'እንዴት እንደምናዘዝ'
• 'ዋጋ'
• 'መላኪያ'
• 'ትራክ'
• 'ስልክ'
• 'መለያ'

Or in English:
• 'how to order'
• 'price'
• 'delivery'
• 'track order'
• 'contact'

📞 Direct help: +251 91 234 5852"""]
}

def detect_intent(message):
    msg_lower = message.lower().strip()
    scores = {}
    for intent, keywords in CHATBOT_KNOWLEDGE.items():
        score = 0
        for keyword in keywords:
            if keyword in msg_lower:
                score += len(keyword)
        if score > 0:
            scores[intent] = score
    return max(scores, key=scores.get) if scores else "default"

def get_ai_response(message):
    intent = detect_intent(message)
    responses = CHATBOT_RESPONSES.get(intent, CHATBOT_RESPONSES["default"])
    return random.choice(responses)

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('message', '').strip()
        if not user_message:
            return jsonify({"success": False, "error": "Empty message"}), 400
        return jsonify({
            "success": True,
            "response": get_ai_response(user_message),
            "intent": detect_intent(user_message),
            "timestamp": datetime.now().strftime('%H:%M')
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ========== TELEGRAM BOT WEBHOOK ==========
@app.route('/api/telegram-webhook', methods=['POST'])
def telegram_webhook():
    data = request.json
    if not data or 'message' not in data:
        return jsonify({"ok": True})
    msg = data['message']
    chat_id = msg['chat']['id']
    text = msg.get('text', '').strip()
    if str(chat_id) != str(CHAT_ID):
        send_telegram_reply(chat_id, "⛔ This bot is private.")
        return jsonify({"ok": True})
    if text == '/start':
        send_telegram_reply(chat_id, "👋 EthioAlibaba Admin Bot\n\nCommands:\n/track ORDER_ID\n/orders\n/status ORDER_ID TEXT\n/help")
    elif text.startswith('/track'):
        parts = text.split()
        if len(parts) < 2:
            send_telegram_reply(chat_id, "❌ Usage: /track ETHA1B2C3")
            return jsonify({"ok": True})
        oid = parts[1].upper()
        conn = get_db()
        order = conn.execute("SELECT * FROM orders WHERE id = ?", (oid,)).fetchone()
        history = conn.execute("SELECT status, time, note FROM status_history WHERE order_id = ? ORDER BY id", (oid,)).fetchall()
        conn.close()
        if not order:
            send_telegram_reply(chat_id, f"❌ Order #{oid} not found.")
            return jsonify({"ok": True})
        o = row_to_dict(order)
        hist_lines = "\n".join([f"• {h['status']} — {h['time']}" for h in history]) or "No history"
        reply = f"📦 Order #{o['id']}\n━━━━━━━━━━━━\n📋 Status: {o['status']}\n📦 {o['category']} x {o['quantity']}\n👤 {o['full_name']} | 📱 {o['phone']}\n📍 {o['city']} | 💴 {o['total_etb']:,.0f} ETB\n\n📜 History:\n{hist_lines}"
        send_telegram_reply(chat_id, reply)
    elif text == '/orders':
        conn = get_db()
        rows = conn.execute("SELECT id, category, status, total_etb, created_at FROM orders ORDER BY created_at DESC LIMIT 10").fetchall()
        conn.close()
        if not rows:
            send_telegram_reply(chat_id, "📭 No orders yet.")
            return jsonify({"ok": True})
        lines = [f"#{r['id']} | {r['category']} | {r['status']} | {r['total_etb']:,.0f} ETB" for r in rows]
        reply = "📋 Last 10 Orders\n━━━━━━━━━━━━\n" + "\n".join(lines)
        send_telegram_reply(chat_id, reply)
    elif text.startswith('/status'):
        parts = text.split(maxsplit=2)
        if len(parts) < 3:
            send_telegram_reply(chat_id, "❌ Usage: /status ORDER_ID New Status")
            return jsonify({"ok": True})
        oid = parts[1].upper()
        new_status = parts[2]
        conn = get_db()
        order = conn.execute("SELECT * FROM orders WHERE id = ?", (oid,)).fetchone()
        if not order:
            conn.close()
            send_telegram_reply(chat_id, f"❌ Order #{oid} not found.")
            return jsonify({"ok": True})
        conn.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, oid))
        conn.execute("INSERT INTO status_history (order_id, status, time, note) VALUES (?, ?, ?, ?)",
            (oid, new_status, datetime.now().strftime('%H:%M'), 'Updated via Telegram'))
        conn.commit()
        conn.close()
        send_telegram_reply(chat_id, f"✅ Order #{oid} → {new_status}")
        telegram(f"📊 UPDATE #{oid}\nNew Status: {new_status}")
    elif text == '/help':
        send_telegram_reply(chat_id, "ℹ️ Commands\n/track ORDER_ID\n/orders\n/status ORDER_ID TEXT\n/help")
    else:
        send_telegram_reply(chat_id, "🤖 Unknown command. Send /help")
    return jsonify({"ok": True})

@app.route('/api')
def api_home():
    return """<h1>✅ EthioAlibaba API Running</h1>
    <ul>
        <li>POST /api/register</li>
        <li>POST /api/login</li>
        <li>GET  /api/me</li>
        <li>POST /api/calculate</li>
        <li>POST /api/send-order</li>
        <li>GET  /api/track/&lt;id&gt;</li>
        <li>GET  /api/my-orders</li>
        <li>POST /api/update-status</li>
        <li>POST /api/chat</li>
        <li>POST /api/telegram-webhook</li>
    </ul>"""

def set_webhook(public_url):
    url = public_url.rstrip('/') + '/api/telegram-webhook'
    r = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
        json={"url": url}, timeout=15
    )
    print(r.json())
    print(f"Webhook set to: {url}")

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'set-webhook':
        if len(sys.argv) < 3:
            print("Usage: python app.py set-webhook https://your-domain.com")
            sys.exit(1)
        set_webhook(sys.argv[2])
    else:
        port = int(os.environ.get("PORT", 5000))
        print("=" * 60)
        print("🚀 EthioAlibaba Server Running")
        print(f"🌐 Port: {port}")
        print("=" * 60)
        app.run(debug=False, host='0.0.0.0', port=port)
