from flask import Flask, render_template, request, redirect, url_for, jsonify
import json
import os
from datetime import datetime
import pytz
import telegram

# تابع کمکی برای تبدیل رشته به عدد، بولین یا نگه داشتن به‌صورت رشته
def try_parse_number(value):
    try:
        if '.' in value:
            return float(value)
        return int(value)
    except ValueError:
        if value.lower() == 'true':
            return True
        if value.lower() == 'false':
            return False
        return value

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
PORT = int(os.environ.get("PORT", 5000))

bot = telegram.Bot(token=TELEGRAM_TOKEN)

def load_tokens():
    try:
        with open("tokens.json", "r") as f:
            return json.load(f)
    except:
        return []

def save_tokens(tokens):
    with open("tokens.json", "w") as f:
        json.dump(tokens, f, indent=4)

def load_watchlist():
    try:
        with open("watchlist.json", "r") as f:
            return json.load(f)
    except:
        return []

def save_watchlist(watchlist):
    with open("watchlist.json", "w") as f:
        json.dump(watchlist, f, indent=4)

def send_watchlist_to_telegram():
    watchlist = load_watchlist()
    if not watchlist:
        message = """📋 واچ‌لیست امروز:
(خالی است)"
    else:
        message = """📋 واچ‌لیست امروز:
"
        for token in watchlist:
            change = token.get("price_change_5m", 0)
            sign = "🔺" if change > 0 else ("🔻" if change < 0 else "➖")
            message += f"{sign} {token['token_name']} ({token['token_symbol']}): {change}%\n"

    msg = bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode=telegram.constants.ParseMode.HTML)
    try:
        bot.pin_chat_message(chat_id=TELEGRAM_CHAT_ID, message_id=msg.message_id, disable_notification=True)
    except:
        pass

@app.route("/")
def index():
    tokens = load_tokens()
    tehran_time = datetime.now(pytz.timezone('Asia/Tehran')).strftime("%Y-%m-%d %H:%M:%S")
    return render_template("index.html", tokens=tokens, updated=tehran_time)

@app.route("/watchlist")
def watchlist():
    watchlist = load_watchlist()
    return render_template("watchlist.html", watchlist=watchlist)

@app.route("/add_to_watchlist", methods=["POST"])
def add_to_watchlist():
    address = request.form.get("address")
    tokens = load_tokens()
    token = next((t for t in tokens if t["address"] == address), None)
    if token:
        watchlist = load_watchlist()
        if address not in [t["address"] for t in watchlist]:
            watchlist.append(token)
            save_watchlist(watchlist)
            send_watchlist_to_telegram()
    return redirect(url_for("index"))

@app.route("/remove_from_watchlist", methods=["POST"])
def remove_from_watchlist():
    address = request.form.get("address")
    watchlist = load_watchlist()
    watchlist = [t for t in watchlist if t["address"] != address]
    save_watchlist(watchlist)
    send_watchlist_to_telegram()
    return redirect(url_for("watchlist"))

@app.route('/filters', methods=['GET'])
def filters():
    with open('filters.json', 'r') as f:
        filters_data = json.load(f)
    return render_template('filters.html', filters=filters_data)

@app.route('/update_filters', methods=['POST'])
def update_filters():
    new_filters = {key: try_parse_number(value) for key, value in request.form.items()}
    with open('filters.json', 'w') as f:
        json.dump(new_filters, f, indent=4)
    return redirect('/')


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
