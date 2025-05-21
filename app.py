from flask import Flask, render_template, request, redirect
import datetime
import pytz
import requests
import os

app = Flask(__name__)

# محیط زمان محلی (تهران)
tehran = pytz.timezone('Asia/Tehran')

# متغیر محیطی برای توکن ربات تلگرام
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# توکن تستی
TOKENS = [
    {
        "name": "Test Token",
        "symbol": "TST",
        "price_usd": 0.01,
        "liquidity_usd": 100000,
        "market_cap": 200000,
        "price_change_5m": 25,  # درصد تغییر بالا برای تست
        "pair_address": "0x1234567890abcdef"
    }
]

WATCHLIST = set()

def send_telegram_message(text):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML"
        }
        try:
            requests.post(url, data=payload)
        except Exception as e:
            print("Telegram error:", e)

@app.route("/")
def index():
    now_tehran = datetime.datetime.now(tehran)
    last_updated = now_tehran.strftime('%Y-%m-%d %H:%M:%S')

    # هشدار قیمت بالا
    for token in TOKENS:
        if token["price_change_5m"] > 20 and token["symbol"] not in WATCHLIST:
            msg = f"🚨 تغییر قیمت شدید برای <b>{token['name']} ({token['symbol']})</b>\n📈 تغییر: {token['price_change_5m']}%\n💧 لیکوئیدیتی: ${token['liquidity_usd']:,}"
            send_telegram_message(msg)

    return render_template("index.html", tokens=TOKENS, last_updated=last_updated)

@app.route("/add_to_watchlist/<symbol>", methods=["POST"])
def add_to_watchlist(symbol):
    WATCHLIST.add(symbol)
    token = next((t for t in TOKENS if t["symbol"] == symbol), None)
    if token:
        msg = f"👁 توکن <b>{token['name']} ({symbol})</b> به واچ‌لیست افزوده شد."
        send_telegram_message(msg)
    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
