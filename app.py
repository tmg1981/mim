import os
import json
from flask import Flask, render_template, request, redirect
from datetime import datetime
import pytz
import telegram

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = telegram.Bot(token=TELEGRAM_TOKEN)

TOKENS_FILE = 'tokens.json'
WATCHLIST_FILE = 'watchlist.json'

def load_tokens():
    if not os.path.exists(TOKENS_FILE):
        return []
    with open(TOKENS_FILE, 'r') as f:
        return json.load(f)

def save_watchlist(watchlist):
    with open(WATCHLIST_FILE, 'w') as f:
        json.dump(watchlist, f)

def load_watchlist():
    if not os.path.exists(WATCHLIST_FILE):
        return []
    with open(WATCHLIST_FILE, 'r') as f:
        return json.load(f)

def update_pinned_watchlist():
    tokens = load_tokens()
    watchlist = load_watchlist()
    matched = [t for t in tokens if t['address'] in watchlist]
    if not matched:
        message = "📌 واچ‌لیست امروز:\nهیچ توکنی در واچ‌لیست نیست."
    else:
        message = "📌 واچ‌لیست امروز:\n"
        for t in matched:
            name = t.get('token_name', 'N/A')
            symbol = t.get('token_symbol', '')
            price = t.get('price_usd', 0)
            buy_price = t.get('buy_price_usd', None)
            percent = ''
            if buy_price:
                diff = round((price - buy_price) / buy_price * 100, 2)
                emoji = "🟢" if diff > 0 else "🔴"
                percent = f"{emoji} {diff}%"
            message += f"- {name} ({symbol}) | ${price} | {percent}\n"

    # حذف پیام پین‌شده قدیمی و ارسال جدید
    try:
        updates = bot.get_updates()
        for update in updates:
            if update.message and update.message.pinned_message:
                bot.unpin_chat_message(chat_id=TELEGRAM_CHAT_ID, message_id=update.message.pinned_message.message_id)
    except:
        pass

    sent = bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    bot.pin_chat_message(chat_id=TELEGRAM_CHAT_ID, message_id=sent.message_id)

@app.route('/')
def index():
    tokens = load_tokens()
    return render_template('index.html', tokens=tokens)

@app.route('/add_to_watchlist', methods=['POST'])
def add_to_watchlist():
    address = request.form['address']
    tokens = load_tokens()
    watchlist = load_watchlist()

    token = next((t for t in tokens if t['address'] == address), None)
    if token:
        if address not in watchlist:
            token['buy_price_usd'] = token.get('price_usd')
            watchlist.append(address)
            save_watchlist(watchlist)
            update_pinned_watchlist()
            bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"➕ {token['token_name']} به واچ‌لیست افزوده شد.")
    return redirect('/')

@app.route('/remove_from_watchlist', methods=['POST'])
def remove_from_watchlist():
    address = request.form['address']
    watchlist = load_watchlist()
    if address in watchlist:
        watchlist.remove(address)
        save_watchlist(watchlist)
        update_pinned_watchlist()
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"➖ توکن با آدرس {address} از واچ‌لیست حذف شد.")
    return redirect('/')

@app.route('/watchlist')
def watchlist():
    tokens = load_tokens()
    watchlist = load_watchlist()
    selected = [t for t in tokens if t['address'] in watchlist]
    return render_template('watchlist.html', tokens=selected)

@app.route('/edit_filters')
def edit_filters():
    return "<h3>🛠 صفحه ویرایش فیلترها در حال توسعه است.</h3>"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)