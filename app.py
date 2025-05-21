from flask import Flask, render_template, request, jsonify
import requests
from datetime import datetime
import pytz
import os
import json

app = Flask(__name__)

# متغیرهای محیطی تلگرام
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

FILTERS_FILE = "filters.json"
WATCHLIST_FILE = "watchlist.json"

def load_filters():
    try:
        with open(FILTERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("Error loading filters:", e)
        return {}

def load_watchlist():
    try:
        with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except:
        return set()

def save_watchlist(watchlist):
    with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(list(watchlist), f, ensure_ascii=False)

watchlist = load_watchlist()

def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram bot token or chat ID not set!")
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        r = requests.post(url, data=payload)
        if not r.ok:
            print("Telegram API error:", r.text)
        return r.ok
    except Exception as e:
        print("Exception sending telegram message:", e)
        return False

def get_local_time():
    local_tz = pytz.timezone("Asia/Tehran")
    now_utc = datetime.utcnow()
    now_local = now_utc.replace(tzinfo=pytz.utc).astimezone(local_tz)
    return now_local.strftime("%Y-%m-%d %H:%M:%S")

def get_tokens_from_dexscreener():
    url = "https://api.dexscreener.io/latest/dex/tokens"
    try:
        response = requests.get(url)
        data = response.json()
        tokens_raw = data.get("tokens", [])
    except Exception as e:
        print("Error fetching from DexScreener:", e)
        tokens_raw = []

    tokens = []

    for t in tokens_raw:
        try:
            token = {
                "token_name": t.get("name") or "نامشخص",
                "token_symbol": t.get("symbol") or "نامشخص",
                "price_usd": float(t.get("priceUsd") or 0),
                "liquidity": float(t.get("liquidityUsd") or 0),
                "market_cap": float(t.get("marketCapUsd") or 0),
                "price_change_5m": float(t.get("priceChange") or 0),
                "address": t.get("address") or None,
                "mint_count": t.get("mintCount") or 0,
                "social_score": t.get("socialScore") or 0,
                "watchlist_count": t.get("watchlistCount") or 0,
                "liquidity_to_marketcap_ratio": (float(t.get("liquidityUsd") or 0) / float(t.get("marketCapUsd") or 1)) if t.get("marketCapUsd") else 0,
                "volume_24h": float(t.get("volumeUsd") or 0),
                "liquidity_locked": t.get("liquidityLocked", False),
                "creator_token_count": t.get("creatorTokenCount") or 0
            }
            tokens.append(token)
        except Exception as e:
            print("Error parsing token:", e)
            continue

    # اضافه کردن توکن تستی
    test_token = {
        "token_name": "TestToken",
        "token_symbol": "TTK",
        "price_usd": 1.23,
        "liquidity": 100000,
        "market_cap": 500000,
        "price_change_5m": 25.5,
        "address": "0xTestAddress",
        "mint_count": 1,
        "social_score": 80,
        "watchlist_count": 15,
        "liquidity_to_marketcap_ratio": 0.2,
        "volume_24h": 60000,
        "liquidity_locked": True,
        "creator_token_count": 3
    }
    tokens.insert(0, test_token)

    return tokens

def filter_tokens(tokens, filters):
    filtered = []
    for token in tokens:
        if token["liquidity"] < filters.get("min_liquidity_usd", 0):
            continue
        if token["mint_count"] > filters.get("max_mint_count", 9999):
            continue
        if token["social_score"] < filters.get("min_social_score", 0):
            continue
        if token["watchlist_count"] < filters.get("min_watchlist_count", 0):
            continue
        if token["liquidity_to_marketcap_ratio"] > filters.get("max_liquidity_to_marketcap_ratio", 9999):
            continue
        if token["price_change_5m"] < filters.get("price_change_5m_threshold", -9999):
            continue
        if token["volume_24h"] < filters.get("min_volume_24h", 0):
            continue
        if filters.get("lock_liquidity_required", False) and not token["liquidity_locked"]:
            continue
        if token["creator_token_count"] < filters.get("creator_min_tokens", 0):
            continue

        filtered.append(token)
    return filtered

@app.route("/", methods=["GET"])
def index():
    filters = load_filters()
    tokens = get_tokens_from_dexscreener()
    tokens = filter_tokens(tokens, filters)
    last_updated = get_local_time()
    return render_template("index.html", tokens=tokens, last_updated=last_updated)

@app.route("/watchlist", methods=["POST"])
def add_to_watchlist():
    data = request.get_json()
    address = data.get("address")
    if not address:
        return jsonify({"status": "error", "message": "آدرس توکن ارسال نشده"}), 400

    if address not in watchlist:
        watchlist.add(address)
        save_watchlist(watchlist)
        message = f"توکن با آدرس <b>{address}</b> به واچ‌لیست اضافه شد."
        send_telegram_message(message)
        return jsonify({"status": "ok"})
    else:
        return jsonify({"status": "exists"})

@app.route("/watchlist", methods=["GET"])
def show_watchlist():
    filters = load_filters()
    tokens = get_tokens_from_dexscreener()
    tokens = filter_tokens(tokens, filters)
    tokens_in_watchlist = [t for t in tokens if t["address"] in watchlist]
    last_updated = get_local_time()
    return render_template("watchlist.html", tokens=tokens_in_watchlist, last_updated=last_updated)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
