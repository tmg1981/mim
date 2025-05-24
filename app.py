import os
import json
from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime
import telegram

app = Flask(__name__)

# بارگذاری توکن تلگرام و شناسه چت از متغیرهای محیطی
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# مقداردهی اولیه به ربات تلگرام در صورت معتبر بودن توکن
bot = None
if TELEGRAM_TOKEN and TELEGRAM_TOKEN.startswith("bot"):
    try:
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
    except Exception as e:
        print(f"خطا در ساخت ربات: {e}")

TOKENS_FILE = "tokens.json"
WATCHLIST_FILE = "watchlist.json"

def load_json_file(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r") as f:
        return json.load(f)

def save_json_file(filepath, data):
    with open(filepath, "w") as f:
        json.dump(data, f, indent=4)

@app.route("/")
def index():
    tokens = load_json_file(TOKENS_FILE)
    watchlist = load_json_file(WATCHLIST_FILE)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return render_template("index.html", tokens=tokens, watchlist=watchlist, last_updated=now)

@app.route("/add_to_watchlist", methods=["POST"])
def add_to_watchlist():
    try:
        address = request.form.get("address")
        tokens = load_json_file(TOKENS_FILE)
        token = next((t for t in tokens if t["address"] == address), None)
        if not token:
            return "توکن پیدا نشد.", 400

        watchlist = load_json_file(WATCHLIST_FILE)
        if not any(t["address"] == address for t in watchlist):
            watchlist.append(token)
            save_json_file(WATCHLIST_FILE, watchlist)

            if bot:
                message = f"✅ توکن به واچ‌لیست افزوده شد:\n{token['token_name']} ({token['token_symbol']})\nقیمت: ${token.get('price_usd', '?')}\n📈 نمودار: https://dexscreener.com/ethereum/{token['address']}"
                bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        return redirect(url_for("index"))
    except Exception as e:
        print(f"Add Error: {e}")
        return "خطایی رخ داد", 500

@app.route("/remove_from_watchlist", methods=["POST"])
def remove_from_watchlist():
    try:
        address = request.form.get("address")
        watchlist = load_json_file(WATCHLIST_FILE)
        updated = [t for t in watchlist if t["address"] != address]
        save_json_file(WATCHLIST_FILE, updated)

        if bot:
            bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"❌ توکن از واچ‌لیست حذف شد:\nآدرس: {address}")
        return redirect(url_for("index"))
    except Exception as e:
        print(f"Remove Error: {e}")
        return "خطایی رخ داد", 500

@app.route("/filters")
def filters():
    return "صفحه ویرایش فیلترها در حال توسعه است"

@app.route("/watchlist")
def show_watchlist():
    tokens = load_json_file(WATCHLIST_FILE)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return render_template("watchlist.html", tokens=tokens, last_updated=now)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
