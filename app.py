import os
import json
import telegram
from flask import Flask, render_template, request, redirect
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot = telegram.Bot(token=TELEGRAM_TOKEN)

app = Flask(__name__)
TOKENS_FILE = 'tokens.json'
WATCHLIST_FILE = 'watchlist.json'


def load_tokens():
    if os.path.exists(TOKENS_FILE):
        with open(TOKENS_FILE) as f:
            return json.load(f)
    return []

def load_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE) as f:
            return json.load(f)
    return []

def save_watchlist(data):
    with open(WATCHLIST_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def format_token_summary(tokens):
    summary = "📌 واچ‌لیست روزانه:\n"
    for token in tokens:
        name = token.get("token_name", "Unknown")
        symbol = token.get("token_symbol", "")
        price = token.get("price_usd", 0)
        change = token.get("price_change_5m", 0)
        pnl = f"{change:+.2f}%"
        emoji = "🟢" if change >= 0 else "🔴"
        summary += f"{emoji} {name} ({symbol}) | قیمت: ${price} | سود/زیان ۵دقیقه‌ای: {pnl}\n"
    return summary

def send_watchlist_to_telegram(tokens):
    try:
        summary = format_token_summary(tokens)
        messages = bot.get_chat(TELEGRAM_CHAT_ID).get_pinned_message()
        if messages:
            bot.unpin_chat_message(TELEGRAM_CHAT_ID, messages.message_id)
        msg = bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=summary)
        bot.pin_chat_message(chat_id=TELEGRAM_CHAT_ID, message_id=msg.message_id)
    except Exception as e:
        print(f"خطا در ارسال پیام تلگرام: {e}")

@app.route('/')
def index():
    tokens = load_tokens()
    watchlist = load_watchlist()
    for token in tokens:
        token['in_watchlist'] = any(w['address'] == token['address'] for w in watchlist)
    return render_template('index.html', tokens=tokens, last_updated=datetime.now())

@app.route('/add_to_watchlist', methods=['POST'])
def add_to_watchlist():
    address = request.form['address']
    tokens = load_tokens()
    token = next((t for t in tokens if t['address'] == address), None)
    if token:
        watchlist = load_watchlist()
        if all(w['address'] != address for w in watchlist):
            watchlist.append(token)
            save_watchlist(watchlist)
            send_watchlist_to_telegram(watchlist)
    return redirect('/')

@app.route('/remove_from_watchlist', methods=['POST'])
def remove_from_watchlist():
    address = request.form['address']
    watchlist = load_watchlist()
    new_watchlist = [w for w in watchlist if w['address'] != address]
    save_watchlist(new_watchlist)
    send_watchlist_to_telegram(new_watchlist)
    return redirect('/')

@app.route('/watchlist')
def watchlist():
    tokens = load_watchlist()
    return render_template('watchlist.html', tokens=tokens)

@app.route('/change_filters')
def change_filters():
    return "<h3>صفحه ویرایش فیلترها در حال توسعه است.</h3>"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(debug=True, host='0.0.0.0', port=port)
