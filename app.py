import os
import json
import requests
from flask import Flask, render_template, request, redirect
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

app = Flask(__name__)
#TELEGRAM_TOKEN ="TELEGRAM_BOT_TOKEN"
#TELEGRAM_CHAT_ID = "TELEGRAM_CHAT_ID"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
#bot = Bot(token=TELEGRAM_TOKEN)

def fetch_tokens():
    url = "https://api.dexscreener.com/latest/dex/pairs/solana"
    try:
        response = requests.get(url)
        data = response.json()
        tokens = []
        for item in data["pairs"][:10]:  # نمایش ۱۰ توکن اول به‌عنوان نمونه
            token = {
                "token_name": item["baseToken"]["name"],
                "token_symbol": item["baseToken"]["symbol"],
                "address": item["pairAddress"],
                "price_usd": float(item["priceUsd"]) if item["priceUsd"] else 0,
                "liquidity": int(item["liquidity"]["usd"]) if item["liquidity"] else 0,
                "market_cap": int(item.get("fdv", 0)),
                "price_change_5m": float(item["priceChange"]["m5"]) if item["priceChange"] else 0,
                "chart_url": item.get("url", "#"),
                "risk_level": "کم" if int(item["liquidity"]["usd"]) > 20000 else ("متوسط" if int(item["liquidity"]["usd"]) > 5000 else "زیاد"),
                "risk_class": "risk-low" if int(item["liquidity"]["usd"]) > 20000 else ("risk-medium" if int(item["liquidity"]["usd"]) > 5000 else "risk-high"),
            }
            tokens.append(token)
        return tokens
    except:
        return []

def load_watchlist():
    try:
        with open("watchlist.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_watchlist(data):
    with open("watchlist.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_filters():
    try:
        with open("filters.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_filters(data):
    with open("filters.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@app.route("/")
def index():
    tokens = fetch_tokens()
    watchlist = load_watchlist()

    # اضافه‌کردن اطلاعات قیمت خرید از واچ‌لیست به توکن‌ها
    for token in tokens:
        for w in watchlist:
            if token["address"] == w["address"]:
                token["buy_price_usd"] = w.get("buy_price_usd")

    return render_template("index.html", tokens=tokens)

@app.route("/add_to_watchlist", methods=["POST"])
def add_to_watchlist():
    address = request.form["address"]
    tokens = fetch_tokens()
    token = next((t for t in tokens if t["address"] == address), None)

    if token:
        watchlist = load_watchlist()
        if not any(w["address"] == address for w in watchlist):
            token["buy_price_usd"] = token["price_usd"]
            watchlist.append(token)
            save_watchlist(watchlist)
            send_telegram_message(f"➕ توکن {token['token_name']} به واچ‌لیست افزوده شد.")
            update_pinned_message(watchlist)

    return redirect("/")

@app.route("/remove_from_watchlist", methods=["POST"])
def remove_from_watchlist():
    address = request.form["address"]
    watchlist = load_watchlist()
    watchlist = [w for w in watchlist if w["address"] != address]
    save_watchlist(watchlist)
    send_telegram_message(f"➖ توکن با آدرس {address} از واچ‌لیست حذف شد.")
    update_pinned_message(watchlist)
    return redirect("/")

@app.route("/edit_filters", methods=["GET", "POST"])
def edit_filters():
    if request.method == "POST":
        filters = []
        for key, value in request.form.items():
            filters.append({"name": key, "value": value})
        save_filters(filters)
        return redirect("/")
    else:
        filters = load_filters()
        return render_template("filters.html", filters=filters)

@app.route("/watchlist")
def view_watchlist():
    tokens = load_watchlist()
    return render_template("watchlist.html", tokens=tokens)

def send_telegram_message(text):
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text, parse_mode="HTML")
    except Exception as e:
        print("Telegram Error:", e)

def update_pinned_message(watchlist):
    try:
        message = """📌 <b>واچ‌لیست روزانه</b>\n\n"""
        for token in watchlist:
            name = token.get("token_name", "نامشخص")
            symbol = token.get("token_symbol", "")
            price = token.get("price_usd", 0)
            buy_price = token.get("buy_price_usd", 0)
            profit = 0
            if buy_price:
                profit = round((price - buy_price) / buy_price * 100, 2)
            emoji = "🟢" if profit >= 0 else "🔴"
            message += f"{emoji} <b>{name} ({symbol})</b>\nقیمت فعلی: ${price}\nسود/زیان: {profit}%\n\n"
        messages = bot.get_chat(TELEGRAM_CHAT_ID).get_pinned_message()
        if messages:
            bot.unpin_chat_message(chat_id=TELEGRAM_CHAT_ID, message_id=messages.message_id)
        new_msg = bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode="HTML")
        bot.pin_chat_message(chat_id=TELEGRAM_CHAT_ID, message_id=new_msg.message_id)
    except Exception as e:
        print("Pinned Message Error:", e)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
