import os
import json
from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime, timedelta
import pytz
import telegram

app = Flask(__name__)

# مقادیر از متغیر محیطی گرفته می‌شوند
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
bot = telegram.Bot(token=TELEGRAM_TOKEN)

TOKENS_FILE = 'tokens.json'
WATCHLIST_FILE = 'watchlist.json'
FILTERS_FILE = 'filters.json'


def load_tokens():
    if os.path.exists(TOKENS_FILE):
        with open(TOKENS_FILE, 'r') as f:
            return json.load(f)
    return []


def load_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, 'r') as f:
            return json.load(f)
    return []


def save_watchlist(watchlist):
    with open(WATCHLIST_FILE, 'w') as f:
        json.dump(watchlist, f, indent=4)


def try_parse_number(value):
    try:
        return float(value)
    except:
        return None


def get_current_time_tehran():
    tehran = pytz.timezone('Asia/Tehran')
    now = datetime.now(tehran)
    return now.strftime("%Y-%m-%d %H:%M:%S")


def send_watchlist_to_telegram(watchlist):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return

    if not watchlist:
        message = "📋 واچ‌لیست امروز خالی است."
    else:
        message = "📋 واچ‌لیست امروز:\n"
        for token in watchlist:
            name = token.get('token_name', '')
            symbol = token.get('token_symbol', '')
            price = token.get('price_usd', 0)
            buy_price = token.get('buy_price', price)
            percent_change = ((price - buy_price) / buy_price) * 100 if buy_price else 0

            emoji = "🟢" if percent_change > 0 else "🔴" if percent_change < 0 else "⚪️"
            message += f"{emoji} {name} ({symbol}): {price:.4f} USD ({percent_change:+.2f}%)\n"

    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode=telegram.constants.ParseMode.HTML)

    # پین کردن پیام
    updates = bot.get_updates()
    if updates:
        last_message = updates[-1].message
        try:
            bot.pin_chat_message(chat_id=TELEGRAM_CHAT_ID, message_id=last_message.message_id, disable_notification=True)
        except:
            pass


@app.route('/')
def index():
    tokens = load_tokens()
    watchlist = load_watchlist()
    now = get_current_time_tehran()
    return render_template('index.html', tokens=tokens, watchlist=watchlist, now=now)


@app.route('/add_to_watchlist/<address>', methods=['POST'])
def add_to_watchlist(address):
    tokens = load_tokens()
    watchlist = load_watchlist()

    token = next((t for t in tokens if t['address'] == address), None)
    if token and token not in watchlist:
        token['buy_price'] = token['price_usd']
        watchlist.append(token)
        save_watchlist(watchlist)
        send_watchlist_to_telegram(watchlist)

    return redirect(url_for('index'))


@app.route('/remove_from_watchlist/<address>', methods=['POST'])
def remove_from_watchlist(address):
    watchlist = load_watchlist()
    watchlist = [t for t in watchlist if t['address'] != address]
    save_watchlist(watchlist)
    send_watchlist_to_telegram(watchlist)

    return redirect(url_for('index'))


@app.route('/filters', methods=['GET', 'POST'])
def filters():
    if request.method == 'POST':
        new_filters = request.form.to_dict()
        parsed_filters = {k: try_parse_number(v) for k, v in new_filters.items()}
        with open(FILTERS_FILE, 'w') as f:
            json.dump(parsed_filters, f, indent=4)
        return redirect(url_for('index'))

    filters = {}
    if os.path.exists(FILTERS_FILE):
        with open(FILTERS_FILE, 'r') as f:
            filters = json.load(f)

    return render_template('filters.html', filters=filters)


@app.route('/watchlist')
def view_watchlist():
    watchlist = load_watchlist()
    return render_template('watchlist.html', watchlist=watchlist)


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
