from flask import Flask, render_template, request, redirect, url_for
import json
import os
import datetime
import telegram

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN', '')
CHAT_ID = os.environ.get('CHAT_ID', '')

bot = telegram.Bot(token=TELEGRAM_TOKEN)

TOKENS_FILE = 'tokens.json'
WATCHLIST_FILE = 'watchlist.json'
FILTERS_FILE = 'filters.json'


def load_json(file_path):
    if not os.path.exists(file_path):
        return [] if file_path.endswith('.json') else {}
    with open(file_path, 'r') as f:
        return json.load(f)

def save_json(file_path, data):
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)


def try_parse_number(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def send_telegram_message(message):
    if TELEGRAM_TOKEN and CHAT_ID:
        try:
            bot.send_message(chat_id=CHAT_ID, text=message, parse_mode=telegram.constants.ParseMode.HTML)
        except Exception as e:
            print(f"Telegram Error: {e}")


def send_watchlist_to_telegram(watchlist):
    message = "📋 واچ‌لیست امروز:\n"
    for i, token in enumerate(watchlist, 1):
        message += f"{i}. {token['token_name']} ({token['token_symbol']})\n"
    if TELEGRAM_TOKEN and CHAT_ID:
        try:
            for msg in bot.get_chat(CHAT_ID).get_pinned_messages():
                bot.unpin_chat_message(CHAT_ID, msg.message_id)
            sent = bot.send_message(chat_id=CHAT_ID, text=message)
            bot.pin_chat_message(chat_id=CHAT_ID, message_id=sent.message_id)
        except Exception as e:
            print(f"Pin Telegram Error: {e}")


@app.route('/')
def index():
    tokens = load_json(TOKENS_FILE)
    watchlist_addresses = [t['address'] for t in load_json(WATCHLIST_FILE)]
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return render_template('index.html', tokens=tokens, watchlist=watchlist_addresses, now=now)


@app.route('/add_to_watchlist/<address>')
def add_to_watchlist(address):
    tokens = load_json(TOKENS_FILE)
    watchlist = load_json(WATCHLIST_FILE)
    token = next((t for t in tokens if t['address'] == address), None)
    if token and address not in [t['address'] for t in watchlist]:
        watchlist.append(token)
        save_json(WATCHLIST_FILE, watchlist)
        send_telegram_message(f"➕ توکن {token['token_name']} به واچ‌لیست افزوده شد.")
        send_watchlist_to_telegram(watchlist)
    return redirect(url_for('index'))


@app.route('/remove_from_watchlist/<address>')
def remove_from_watchlist(address):
    watchlist = load_json(WATCHLIST_FILE)
    new_watchlist = [t for t in watchlist if t['address'] != address]
    save_json(WATCHLIST_FILE, new_watchlist)
    send_telegram_message(f"❌ توکن با آدرس {address} از واچ‌لیست حذف شد.")
    send_watchlist_to_telegram(new_watchlist)
    return redirect(url_for('index'))


@app.route('/watchlist')
def watchlist():
    tokens = load_json(WATCHLIST_FILE)
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return render_template('watchlist.html', tokens=tokens, watchlist=[t['address'] for t in tokens], now=now)


@app.route('/filters', methods=['GET', 'POST'])
def filters():
    if request.method == 'POST':
        new_filters = request.form.to_dict()
        save_json(FILTERS_FILE, new_filters)
        return redirect(url_for('index'))
    filters_data = load_json(FILTERS_FILE)
    return render_template('filters.html', filters=filters_data)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(debug=True, host='0.0.0.0', port=port)
