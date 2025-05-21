from flask import Flask, render_template, request, redirect, url_for, jsonify
import requests
from datetime import datetime
import pytz
import os
import json

app = Flask(__name__)

# متغیرهای محیطی برای تلگرام
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

WATCHLIST_FILE = "watchlist.json"

# بارگذاری واچ‌لیست از فایل
def load_watchlist():
    try:
        with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except:
        return set()

# ذخیره واچ‌لیست در فایل
def save_watchlist(watchlist):
    with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(list(watchlist), f, ensure_ascii=False, indent=2)

watchlist = load_watchlist()

# تابع نمونه برای گرفتن توکن‌ها از API DexScreener
def get_tokens():
    url = "https://api.dexscreener.com/latest/dex/tokens"
    try:
        response = requests.get(url)
        data = response.json()
        tokens = []
        # یک مثال ساده برای نمونه (بسته به ساختار واقعی API ممکنه نیاز به اصلاح داشته باشه)
        for item in data.get("pairs", []):
            tokens.append({
                "name": item.get("token0", {}).get("name", "نامشخص"),
                "symbol": item.get("token0", {}).get("symbol", "???"),
                "price_usd": float(item.get("priceUsd", 0)),
                "liquidity_usd": float(item.get("liquidityUsd", 0)),
                "market_cap": float(item.get("marketCap", 0)),
                "price_change_5m": float(item.get("priceChange", 0)),
                "address": item.get("token0", {}).get("address"),
            })
        # اضافه کردن توکن تستی برای اطمینان
        tokens.insert(0, {
            "name": "TestToken",
            "symbol": "TTK",
            "price_usd": 1.23,
            "liquidity_usd": 100000,
            "market_cap": 500000,
            "price_change_5m": 25.5,
            "address": "0xTestAddress"
        })
        return tokens
    except Exception as e:
        print(f"Error fetching tokens: {e}")
        # بازگشت لیست خالی یا توکن تستی در صورت خطا
        return [{
            "name": "TestToken",
            "symbol": "TTK",
            "price_usd": 1.23,
            "liquidity_usd": 100000,
            "market_cap": 500000,
            "price_change_5m": 25.5,
            "address": "0xTestAddress"
        }]

# تبدیل زمان به ساعت محلی تهران
def get_local_time():
    local_tz = pytz.timezone("Asia/Tehran")
    now_utc = datetime.utcnow()
    now_local = now_utc.replace(tzinfo=pytz.utc).astimezone(local_tz)
    return now_local.strftime("%Y-%m-%d %H:%M:%S")

# تابع ارسال پیام به تلگرام با لاگ‌گذاری
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
        if response.ok:
            print("Telegram message sent successfully.")
            return True
        else:
            print(f"Telegram API error: {response.status_code} {response.text}")
            return False
    except Exception as e:
        print(f"Error sending telegram message: {e}")
        return False

@app.route("/", methods=["GET"])
def index():
    tokens = get_tokens()
    last_updated = get_local_time()
    return render_template("index.html", tokens=tokens, last_updated=last_updated)

@app.route("/watchlist", methods=["GET"])
def show_watchlist():
    tokens = get_tokens()
    # فیلتر کردن توکن‌ها بر اساس واچ‌لیست
    watched_tokens = [t for t in tokens if t.get("address") in watchlist]
    last_updated = get_local_time()
    return render_template("watchlist.html", tokens=watched_tokens, last_updated=last_updated)

@app.route("/watchlist/add", methods=["POST"])
def add_to_watchlist():
    data = request.get_json()
    address = data.get("address")
    if not address:
        return jsonify({"status": "error", "message": "Address not provided"}), 400
    if address not in watchlist:
        watchlist.add(address)
        save_watchlist(watchlist)
        message = f"توکن <b>{address}</b> به واچ‌لیست اضافه شد."
        send_telegram_message(message)
    return jsonify({"status": "ok"})

@app.route("/watchlist/remove", methods=["POST"])
def remove_from_watchlist():
    data = request.get_json()
    address = data.get("address")
    if not address:
        return jsonify({"status": "error", "message": "Address not provided"}), 400
    if address in watchlist:
        watchlist.remove(address)
        save_watchlist(watchlist)
        message = f"توکن <b>{address}</b> از واچ‌لیست حذف شد."
        send_telegram_message(message)
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
