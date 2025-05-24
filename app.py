from flask import Flask, render_template, request, redirect, url_for, flash
import json
import os
import requests

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # برای flash پیام‌ها

WATCHLIST_FILE = 'watchlist.json'
TOKENS_FILE = 'tokens.json'

# توکن تلگرام و چت آی‌دی (جایگزین کن با مقادیر خودت)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = telegram.Bot(token=TELEGRAM_TOKEN)

def load_tokens():
    if os.path.exists(TOKENS_FILE):
        with open(TOKENS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def load_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_watchlist(watchlist):
    with open(WATCHLIST_FILE, 'w', encoding='utf-8') as f:
        json.dump(watchlist, f, ensure_ascii=False, indent=2)

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': text,
        'parse_mode': 'HTML'
    }
    try:
        r = requests.post(url, data=payload)
        r.raise_for_status()
    except Exception as e:
        print("Telegram send error:", e)

# فرض می‌کنیم این توابع برای خرید و فروش خودکار پیاده‌سازی شده
def buy_token(token):
    # اینجا منطق خرید خودکار را پیاده‌سازی کن
    print(f"Buying token: {token['token_symbol']} at {token['price_usd']}")
    # در واقعیت، درخواست به شبکه بلاک‌چین یا API صرافی ارسال شود

def sell_token(token):
    # اینجا منطق فروش خودکار را پیاده‌سازی کن
    print(f"Selling token: {token['token_symbol']} at {token['price_usd']}")

def calculate_risk_class(risk_level):
    # برای استایل کلاس ریسک در HTML
    level = risk_level.lower()
    if level == 'low':
        return 'risk-low'
    elif level == 'medium':
        return 'risk-medium'
    elif level == 'high':
        return 'risk-high'
    else:
        return ''

@app.route('/')
def index():
    tokens = load_tokens()
    watchlist = load_watchlist()
    # افزودن فیلدهای اضافی برای نمایش در قالب (مثل buy_price_usd)
    # در اینجا فرض می‌کنیم buy_price_usd داخل واچ‌لیست ذخیره شده
    for token in tokens:
        # پیدا کردن اگر توکن در واچ‌لیست است
        wtoken = next((w for w in watchlist if w['address'] == token['address']), None)
        if wtoken:
            token['buy_price_usd'] = wtoken.get('buy_price_usd', None)
        else:
            token['buy_price_usd'] = None
        token['risk_class'] = calculate_risk_class(token.get('risk_level', ''))
    return render_template('index.html', tokens=tokens)

@app.route('/watchlist')
def watchlist_page():
    watchlist = load_watchlist()
    for token in watchlist:
        token['risk_class'] = calculate_risk_class(token.get('risk_level', ''))
    return render_template('watchlist.html', tokens=watchlist)

@app.route('/add_to_watchlist', methods=['POST'])
def add_to_watchlist():
    address = request.form.get('address')
    tokens = load_tokens()
    watchlist = load_watchlist()
    token = next((t for t in tokens if t['address'] == address), None)
    if not token:
        flash('توکن یافت نشد!', 'danger')
        return redirect(url_for('index'))
    # چک کن اگر قبلاً در واچ‌لیست هست
    if any(w['address'] == address for w in watchlist):
        flash('توکن قبلاً در واچ‌لیست است.', 'warning')
        return redirect(url_for('index'))
    # اضافه کن و قیمت خرید فرضی را روی قیمت فعلی قرار بده
    token_to_add = token.copy()
    token_to_add['buy_price_usd'] = token['price_usd']
    watchlist.append(token_to_add)
    save_watchlist(watchlist)
    buy_token(token_to_add)  # خرید خودکار
    send_telegram_message(f"✅ توکن <b>{token['token_name']} ({token['token_symbol']})</b> به واچ‌لیست اضافه شد و خرید خودکار انجام شد.")
    flash('توکن به واچ‌لیست اضافه شد.', 'success')
    return redirect(url_for('index'))

@app.route('/remove_from_watchlist', methods=['POST'])
def remove_from_watchlist():
    address = request.form.get('address')
    watchlist = load_watchlist()
    token = next((w for w in watchlist if w['address'] == address), None)
    if not token:
        flash('توکن در واچ‌لیست یافت نشد.', 'danger')
        return redirect(url_for('watchlist_page'))
    watchlist = [w for w in watchlist if w['address'] != address]
    save_watchlist(watchlist)
    sell_token(token)  # فروش خودکار
    send_telegram_message(f"❌ توکن <b>{token['token_name']} ({token['token_symbol']})</b> از واچ‌لیست حذف شد و فروش خودکار انجام شد.")
    flash('توکن از واچ‌لیست حذف شد.', 'success')
    return redirect(url_for('watchlist_page'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
