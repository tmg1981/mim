from flask import Flask, render_template, request
import requests
import os
from datetime import datetime
import threading
import time
import random

app = Flask(__name__)

WATCHLIST = []
TOKEN_CACHE = []
LAST_UPDATED = None
PREVIOUS_PRICES = {}
PRICE_ALERT_THRESHOLD = 20  # درصد

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


def send_telegram_message(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("TELEGRAM TOKEN OR CHAT_ID NOT SET")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Error sending Telegram message: {e}")


def fetch_data():
    global TOKEN_CACHE, LAST_UPDATED, PREVIOUS_PRICES

    tokens = []

    # توکن تستی
    test_token_address = "0xTestTokenAddress"
    base_price = PREVIOUS_PRICES.get(test_token_address, 0.1)
    # نوسان ±30٪ در قیمت
    new_price = round(base_price * (1 + random.uniform(-0.3, 0.3)), 6)

    if base_price and abs((new_price - base_price) / base_price * 100) >= PRICE_ALERT_THRESHOLD:
        percent_change = ((new_price - base_price) / base_price) * 100
        send_telegram_message(f"""
🚨 <b>Test Token Price Alert!</b>
🧪 <b>Test Token (TEST)</b>
💲 <b>Old Price:</b> ${base_price:.6f}
💲 <b>New Price:</b> ${new_price:.6f}
📊 <b>Change:</b> {percent_change:.2f}%
🔗 <b>Token:</b> <code>{test_token_address}</code>
""")

    PREVIOUS_PRICES[test_token_address] = new_price
    tokens.append({
        "name": "Test Token",
        "symbol": "TEST",
        "address": test_token_address,
        "network": "TestNet",
        "price": new_price
    })

    # دریافت توکن‌های واقعی از DexScreener (اختیاری)
    try:
        response = requests.get("https://api.dexscreener.com/latest/dex/pairs")
        data = response.json()
        for pool in data.get("pairs", []):
            base = pool.get("baseToken", {})
            if not base.get("address"):
                continue
            token_address = base["address"]
            price = float(pool.get("priceUsd", 0))

            prev_price = PREVIOUS_PRICES.get(token_address)
            if prev_price and abs((price - prev_price) / prev_price * 100) >= PRICE_ALERT_THRESHOLD:
                percent_change = ((price - prev_price) / prev_price) * 100
                send_telegram_message(f"""
🚨 <b>Price Alert!</b>
📉 <b>{base.get("name")} ({base.get("symbol")})</b>
🌐 <b>Network:</b> {pool.get("chainId")}
💲 <b>Old Price:</b> ${prev_price:.6f}
💲 <b>New Price:</b> ${price:.6f}
📊 <b>Change:</b> {percent_change:.2f}%
🔗 <b>Token:</b> <code>{token_address}</code>
""")

            PREVIOUS_PRICES[token_address] = price
            tokens.append({
                "name": base.get("name"),
                "symbol": base.get("symbol"),
                "address": token_address,
                "network": pool.get("chainId"),
                "price": price
            })
    except Exception as e:
        print(f"Error fetching real tokens: {e}")

    TOKEN_CACHE = tokens
    LAST_UPDATED = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')


@app.route('/')
def index():
    return render_template("index.html", tokens=TOKEN_CACHE, last_updated=LAST_UPDATED)


@app.route('/watchlist', methods=['POST'])
def add_to_watchlist():
    token_address = request.form.get("token_address")
    if token_address:
        WATCHLIST.append(token_address)
        send_telegram_message(f"🔔 توکن به واچ‌لیست افزوده شد: <code>{token_address}</code>")
    return ('', 204)


def background_updater():
    while True:
        fetch_data()
        time.sleep(300)


if __name__ == '__main__':
    threading.Thread(target=background_updater, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
