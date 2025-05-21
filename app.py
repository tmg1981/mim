from flask import Flask, render_template, request
import requests
import os
from datetime import datetime
import threading
import time

app = Flask(__name__)

WATCHLIST = []
TOKEN_CACHE = []
LAST_UPDATED = None
PREVIOUS_PRICES = {}  # برای مانیتور نوسان قیمت
PRICE_ALERT_THRESHOLD = 20  # درصد تغییر برای هشدار

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

    try:
        response = requests.get("https://api.dexscreener.com/latest/dex/pairs")
        data = response.json()

        tokens = []
        for pool in data.get("pairs", []):
            token_name = pool.get("baseToken", {}).get("name")
            token_symbol = pool.get("baseToken", {}).get("symbol")
            token_address = pool.get("baseToken", {}).get("address")
            network = pool.get("chainId")
            attributes = pool.get("priceUsd", {})

            if not token_name or not token_symbol or not token_address:
                continue

            current_price = float(pool.get("priceUsd", 0))
            prev_price = PREVIOUS_PRICES.get(token_address)

            # هشدار نوسان قیمت
            if prev_price:
                percent_change = ((current_price - prev_price) / prev_price) * 100
                if abs(percent_change) >= PRICE_ALERT_THRESHOLD:
                    msg = f"""
🚨 <b>Price Alert!</b>
📉 <b>{token_name} ({token_symbol})</b>
🌐 <b>Network:</b> {network}
💲 <b>Old Price:</b> ${prev_price:.6f}
💲 <b>New Price:</b> ${current_price:.6f}
📊 <b>Change:</b> {percent_change:.2f}%
🔗 <b>Token:</b> <code>{token_address}</code>
"""
                    send_telegram_message(msg)

            PREVIOUS_PRICES[token_address] = current_price

            tokens.append({
                "name": token_name,
                "symbol": token_symbol,
                "address": token_address,
                "network": network,
                "price": current_price
            })

        # افزودن توکن تستی برای بررسی عملکرد
        tokens.append({
            "name": "Test Token",
            "symbol": "TEST",
            "address": "0xTestTokenAddress",
            "network": "TestNet",
            "price": 0.1234
        })

        TOKEN_CACHE = tokens
        LAST_UPDATED = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    except Exception as e:
        print(f"Error fetching data: {e}")


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
        time.sleep(300)  # هر ۵ دقیقه یک بار


if __name__ == '__main__':
    threading.Thread(target=background_updater, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
