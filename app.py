from flask import Flask, render_template, request, redirect, url_for
import requests
from datetime import datetime
import pytz
import os

app = Flask(__name__)

# متغیرهای محیطی برای تلگرام (تو باید تنظیم کنی)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# لیست واچ‌لیست به صورت set برای جلوگیری از تکراری بودن
watchlist = set()

# تابع نمونه برای گرفتن توکن‌ها (مثال با توکن تستی)
def get_tokens():
    # اینجا به جای نمونه می‌تونی API اصلی خودت رو صدا بزنی و داده واقعی بگیری
    tokens = [
        # اینجا می‌تونی توکن‌های واقعی رو بارگذاری کنی
    ]

    # توکن تستی همیشه اضافه می‌کنیم
    test_token = {
        "name": "TestToken",
        "symbol": "TTK",
        "price_usd": 1.23,
        "liquidity_usd": 100000,
        "market_cap": 500000,
        "price_change_5m": 25.5,
        "contract_address": "0xTestAddress",
    }
    tokens.insert(0, test_token)

    return tokens

# تبدیل زمان به ساعت محلی تهران
def get_local_time():
    local_tz = pytz.timezone("Asia/Tehran")
    now_utc = datetime.utcnow()
    now_local = now_utc.replace(tzinfo=pytz.utc).astimezone(local_tz)
    return now_local.strftime("%Y-%m-%d %H:%M:%S")

# تابع ارسال پیام به تلگرام
def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram bot token or chat ID not set!")
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
        print(f"Error sending telegram message: {e}")
        return False

@app.route("/", methods=["GET"])
def index():
    tokens = get_tokens()
    last_updated = get_local_time()
    return render_template("index.html", tokens=tokens, last_updated=last_updated)

@app.route("/add_to_watchlist/<symbol>", methods=["POST"])
def add_to_watchlist(symbol):
    if symbol not in watchlist:
        watchlist.add(symbol)
        message = f"توکن <b>{symbol}</b> به واچ‌لیست اضافه شد."
        send_telegram_message(message)
    return redirect(url_for("index"))

if __name__ == "__main__":
    # روی همه IPها و پورت 10000 اجرا شود (مطابق رندر)
    app.run(host="0.0.0.0", port=10000)
