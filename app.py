from flask import Flask, render_template, request, jsonify
import requests
from datetime import datetime
import pytz
import os

app = Flask(__name__)

# متغیرهای محیطی برای تلگرام
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# لیست توکن‌هایی که به واچ‌لیست اضافه شده‌اند
watchlist = set()

# تابع نمونه برای گرفتن لیست توکن‌ها
def get_tokens():
    tokens = []

    # نمونه توکن تستی
    test_token = {
        "token_name": "TestToken",
        "token_symbol": "TTK",
        "price_usd": 1.23,
        "liquidity": 100000,
        "market_cap": 500000,
        "price_change_5m": 25.5,
        "address": "0xTestAddress"
    }

    tokens.append(test_token)

    return tokens

# تابع تبدیل زمان به تهران
def get_local_time():
    local_tz = pytz.timezone("Asia/Tehran")
    now_utc = datetime.utcnow()
    now_local = now_utc.replace(tzinfo=pytz.utc).astimezone(local_tz)
    return now_local.strftime("%Y-%m-%d %H:%M:%S")

# ارسال پیام تلگرام
def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⛔ متغیرهای تلگرام تنظیم نشده‌اند.")
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, data=payload)
        return response.ok
    except Exception as e:
        print(f"خطا در ارسال پیام تلگرام: {e}")
        return False

# روت اصلی
@app.route("/", methods=["GET"])
def index():
    tokens = get_tokens()
    last_updated = get_local_time()
    return render_template("index.html", tokens=tokens, last_updated=last_updated)

# روت API برای افزودن توکن به واچ‌لیست
@app.route("/watchlist", methods=["POST"])
def add_to_watchlist():
    data = request.get_json()
    address = data.get("address")

    if not address:
        return jsonify({"status": "error", "message": "آدرس توکن ارسال نشده است"}), 400

    if address in watchlist:
        return jsonify({"status": "ok", "message": "قبلاً اضافه شده"})

    watchlist.add(address)
    message = f"✅ توکن جدید به واچ‌لیست اضافه شد:\n<code>{address}</code>"
    send_telegram_message(message)

    return jsonify({"status": "ok", "message": "به واچ‌لیست اضافه شد"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
