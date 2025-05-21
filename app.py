from flask import Flask, render_template, request, redirect, url_for, jsonify
import requests
from datetime import datetime
import pytz
import os
import json

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

WATCHLIST_FILE = "watchlist.json"
if os.path.exists(WATCHLIST_FILE):
    with open(WATCHLIST_FILE, "r") as f:
        watchlist = set(json.load(f))
else:
    watchlist = set()

# دریافت توکن‌ها از API واقعی DexScreener
def get_tokens():
    try:
        url = "https://api.dexscreener.com/latest/dex/pairs/solana"
        response = requests.get(url, timeout=10)
        data = response.json()
        tokens = []

        for item in data["pairs"][:10]:  # فقط 10 توکن اول برای تست
            token = {
                "token_name": item.get("baseToken", {}).get("name", "Unknown"),
                "token_symbol": item.get("baseToken", {}).get("symbol", "UNK"),
                "price_usd": float(item.get("priceUsd", 0)),
                "liquidity": float(item.get("liquidity", {}).get("usd", 0)),
                "market_cap": float(item.get("fdv", 0)),
                "price_change_5m": float(item.get("priceChange", {}).get("m5", 0)),
                "address": item.get("pairAddress", "")
            }
            tokens.append(token)

        # اضافه کردن توکن تستی
        tokens.insert(0, {
            "token_name": "TestToken",
            "token_symbol": "TTK",
            "price_usd": 1.23,
            "liquidity": 100000,
            "market_cap": 500000,
            "price_change_5m": 25.5,
            "address": "0xTestAddress"
        })

        return tokens
    except Exception as e:
        print(f"Error fetching tokens: {e}")
        return []

def get_local_time():
    local_tz = pytz.timezone("Asia/Tehran")
    now_utc = datetime.utcnow()
    now_local = now_utc.replace(tzinfo=pytz.utc).astimezone(local_tz)
    return now_local.strftime("%Y-%m-%d %H:%M:%S")

def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials not set!")
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
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

@app.route("/watchlist", methods=["POST"])
def add_to_watchlist():
    data = request.json
    address = data.get("address")
    if address and address not in watchlist:
        watchlist.add(address)
        with open(WATCHLIST_FILE, "w") as f:
            json.dump(list(watchlist), f)
        send_telegram_message(f"✅ توکن جدیدی به واچ‌لیست اضافه شد:\n<code>{address}</code>")
        return jsonify({"status": "ok"})
    return jsonify({"status": "exists"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
