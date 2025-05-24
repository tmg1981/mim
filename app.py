from flask import Flask, render_template, request, redirect
import json
from datetime import datetime
import os
import requests
import pytz

app = Flask(__name__)

FILTERS_FILE = 'filters.json'
TOKENS_FILE = 'tokens.json'
WATCHLIST_FILE = 'watchlist.json'

TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def load_tokens():
    if not os.path.exists(TOKENS_FILE):
        return []
    with open(TOKENS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_filters():
    if not os.path.exists(FILTERS_FILE):
        return {}
    with open(FILTERS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_watchlist():
    if not os.path.exists(WATCHLIST_FILE):
        return []
    with open(WATCHLIST_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_watchlist(watchlist):
    with open(WATCHLIST_FILE, 'w', encoding='utf-8') as f:
        json.dump(watchlist, f, ensure_ascii=False, indent=2)

def send_telegram_message(message):
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
        try:
            requests.post(url, data=data)
        except Exception as e:
            print("Telegram error:", e)

@app.route('/')
def index():
    filters = load_filters()
    tokens = load_tokens()
    watchlist = load_watchlist()

    # در این نسخه ساده، فیلترها بررسی نمی‌شوند
    filtered_tokens = tokens

    if not filtered_tokens:
        filtered_tokens = [{
            "token_name": "توکن تستی",
            "token_symbol": "TST",
            "price_usd": 0.01,
            "address": "0xTestAddress"
        }]

    # ساعت به‌وقت تهران
    iran_time = datetime.now(pytz.timezone('Asia/Tehran')).strftime('%Y-%m-%d %H:%M:%S')

    return render_template(
        'index.html',
        tokens=filtered_tokens,
        watchlist=watchlist,
        last_updated=iran_time
    )

@app.route('/watch', methods=['POST'])
def add_to_watchlist():
    address = request.form['token_address']
    watchlist = load_watchlist()
    if address not in watchlist:
        watchlist.append(address)
        save_watchlist(watchlist)

        # پیام تلگرام
        tokens = load_tokens()
        token = next((t for t in tokens if t['address'] == address), None)
        if token:
            msg = f"✅ توکن {token.get('token_name')} ({token.get('token_symbol')}) به واچ‌لیست افزوده شد.\n\n💲 قیمت: {token.get('price_usd')} دلار\n📬 آدرس: {address}"
            send_telegram_message(msg)

    return redirect('/')

@app.route('/unwatch', methods=['POST'])
def remove_from_watchlist():
    address = request.form['token_address']
    watchlist = load_watchlist()
    if address in watchlist:
        watchlist.remove(address)
        save_watchlist(watchlist)

        # پیام تلگرام
        tokens = load_tokens()
        token = next((t for t in tokens if t['address'] == address), None)
        if token:
            msg = f"⚠️ توکن {token.get('token_name')} از واچ‌لیست حذف شد.\n📬 آدرس: {address}"
            send_telegram_message(msg)

    return redirect('/')

@app.route('/watchlist')
def view_watchlist():
    watchlist = load_watchlist()
    tokens = load_tokens()
    watchlist_tokens = [t for t in tokens if t.get('address') in watchlist]
    return render_template('watchlist.html', tokens=watchlist_tokens)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
