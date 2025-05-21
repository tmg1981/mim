from flask import Flask, render_template, request, redirect, url_for
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

# توکن تستی برای نمایش ثابت
TEST_TOKEN = {
    "name": "TestToken",
    "symbol": "TTK",
    "price_usd": 1.23,
    "liquidity_usd": 100000,
    "market_cap": 500000,
    "price_change_5m": 25.5,
    "contract_address": "0xTestAddress",
    "chain": "TestNet",
    "dex": "FakeDEX",
    "chart": "#"
}

# بارگذاری واچ‌لیست
if os.path.exists(WATCHLIST_FILE):
    with open(WATCHLIST_FILE, "r") as f:
        watchlist = set(json.load(f))
else:
    watchlist = set()

# ذخیره واچ‌لیست در فایل
def save_watchlist():
    with open(WATCHLIST_FILE, "w") as f:
        json.dump(list(watchlist), f)

# گرفتن توکن‌ها از DexScreener
def get_tokens():
    try:
        url = "https://api.dexscreener.com/latest/dex/pairs/solana"
        response = requests.get(url, timeout=10)
        data = response.json()
        tokens = []
        for item in data.get("pairs", [])[:20]:
            tokens.append({
                "name": item.get("baseToken", {}).get("name", "Unknown"),
                "symbol": item.get("baseToken", {}).get("symbol", "N/A"),
                "price_usd": float(item.get("priceUsd") or 0),
                "liquidity_usd": float(item.get("liquidity", {}).get("usd", 0)),
                "market_cap": float(item.get("fdv", 0)),
                "price_change_5m": float(item.get("priceChange", {}).get("m5", 0)),
                "contract_address": item.get("pairAddress", ""),
                "chain": item.get("chainId", "solana"),
                "dex": item.get("dexId", "N/A"),
                "chart": item.get("url", "#")
            })
        tokens.insert(0, TEST_TOKEN)
        return tokens
    except Exception as e:
        print(f"Error fetching tokens: {e}")
        return [TEST_TOKEN]

# زمان محلی تهران
def get_local_time():
    local_tz = pytz.timezone("Asia/Tehran")
    now_utc = datetime.utcnow()
    now_local = now_utc.replace(tzinfo=pytz.utc).astimezone(local_tz)
    return now_local.strftime("%Y-%m-%d %H:%M:%S")

# ارسال پیام به تلگرام
def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram credentials not set.")
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        response = requests.post(url, data=payload)
        if response.status_code != 200:
            print(f"❌ Telegram error: {response.text}")
        return response.ok
    except Exception as e:
        print(f"❌ Telegram send error: {e}")
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
        save_watchlist()
        send_telegram_message(f"✅ توکن <b>{symbol}</b> به واچ‌لیست اضافه شد.")
    return redirect(url_for("index"))

@app.route("/watchlist", methods=["GET"])
def view_watchlist():
    symbols = list(watchlist)
    return render_template("watchlist.html", symbols=symbols)

@app.route("/remove_from_watchlist/<symbol>", methods=["POST"])
def remove_from_watchlist(symbol):
    watchlist.discard(symbol)
    return redirect(url_for("view_watchlist"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
