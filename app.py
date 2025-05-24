from flask import Flask, render_template, request, redirect
import json
from datetime import datetime
import os

app = Flask(__name__)

FILTERS_FILE = 'filters.json'
TOKENS_FILE = 'tokens.json'
WATCHLIST_FILE = 'watchlist.json'

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

@app.route('/')
def index():
    filters = load_filters()
    tokens = load_tokens()
    watchlist = load_watchlist()

    filtered_tokens = []
    for token in tokens:
        try:
            if (
                token.get('liquidity_usd', 0) >= filters.get('min_liquidity_usd', 0) and
                token.get('mint_count', 0) <= filters.get('max_mint_count', 10) and
                token.get('social_score', 0) >= filters.get('min_social_score', 0) and
                token.get('watchlist_count', 0) >= filters.get('min_watchlist_count', 0) and
                token.get('liquidity_to_mc', 1) <= filters.get('max_liquidity_to_marketcap_ratio', 1) and
                abs(token.get('price_change_5m', 0)) >= filters.get('price_change_5m_threshold', 0) and
                token.get('volume_24h', 0) >= filters.get('min_volume_24h', 0) and
                (not filters.get('lock_liquidity_required') or token.get('liquidity_locked') == 'قفل') and
                token.get('creator_token_count', 0) < filters.get('creator_min_tokens', 100)
            ):
                filtered_tokens.append(token)
        except Exception as e:
            print(f"Error filtering token: {token.get('name')} - {e}")
            continue

    # اگر توکنی برای نمایش نبود، یک توکن تستی اضافه شود
    if not filtered_tokens:
        test_token = {
            "name": "توکن تستی",
            "symbol": "TST",
            "address": "0xTestTokenAddress",
            "chart_url": "https://dexscreener.com/",
            "liquidity_usd": 100000,
            "mint_count": 1,
            "social_score": 50,
            "price_change_5m": 0.5,
            "liquidity_locked": "قفل",
            "creator_token_count": 1,
            "volume_24h": 10000,
            "watchlist_count": 0,
            "liquidity_to_mc": 0.5,
            "risk_level": "low"
        }
        filtered_tokens = [test_token]

    return render_template(
        'index.html',
        tokens=filtered_tokens,
        watchlist=watchlist,
        last_updated=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )

@app.route('/watch', methods=['POST'])
def add_to_watchlist():
    address = request.form['token_address']
    watchlist = load_watchlist()
    if address not in watchlist:
        watchlist.append(address)
        # اینجا می‌تونی کد خرید خودکار رو اضافه کنی
    save_watchlist(watchlist)
    return redirect('/')

@app.route('/unwatch', methods=['POST'])
def remove_from_watchlist():
    address = request.form['token_address']
    watchlist = load_watchlist()
    if address in watchlist:
        watchlist.remove(address)
        # اینجا می‌تونی کد فروش خودکار رو اضافه کنی
    save_watchlist(watchlist)
    return redirect('/')

@app.route('/watchlist')
def view_watchlist():
    watchlist = load_watchlist()
    tokens = load_tokens()
    watchlist_tokens = [t for t in tokens if t.get('address') in watchlist]
    return render_template('watchlist.html', tokens=watchlist_tokens)


@app.route('/edit_filters', methods=['GET', 'POST'])
def edit_filters():
    if request.method == 'POST':
        new_filters = {
            "min_liquidity_usd": int(request.form.get("min_liquidity_usd", 0)),
            "max_mint_count": int(request.form.get("max_mint_count", 10)),
            "min_social_score": int(request.form.get("min_social_score", 0)),
            "min_watchlist_count": int(request.form.get("min_watchlist_count", 0)),
            "max_liquidity_to_marketcap_ratio": float(request.form.get("max_liquidity_to_marketcap_ratio", 1)),
            "price_change_5m_threshold": float(request.form.get("price_change_5m_threshold", 0)),
            "min_volume_24h": int(request.form.get("min_volume_24h", 0)),
            "lock_liquidity_required": request.form.get("lock_liquidity_required") == 'on',
            "creator_min_tokens": int(request.form.get("creator_min_tokens", 100))
        }
        with open(FILTERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(new_filters, f, ensure_ascii=False, indent=2)
        return redirect('/')
    else:
        filters = load_filters()
        return render_template('filters.html', filters=filters)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
