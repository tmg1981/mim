import os
import json
from flask import Flask, render_template, request, redirect, url_for, jsonify
from datetime import datetime
import telegram

app = Flask(__name__)

# دریافت توکن بات و چت آی‌دی از متغیرهای محیطی
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

WATCHLIST_FILE = 'watchlist.json'
TOKENS_FILE = 'tokens.json'
FILTERS_FILE = 'filters.json'

def load_tokens():
    try:
        with open(TOKENS_FILE, 'r', encoding='utf-8') as f:
            tokens = json.load(f)
        return tokens
    except Exception:
        return []

def load_watchlist():
    try:
        with open(WATCHLIST_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []

def save_watchlist(watchlist):
    with open(WATCHLIST_FILE, 'w', encoding='utf-8') as f:
        json.dump(watchlist, f, ensure_ascii=False, indent=2)

def load_filters():
    try:
        with open(FILTERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def save_filters(filters):
    with open(FILTERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(filters, f, ensure_ascii=False, indent=2)

# محاسبه سود/زیان ساده برای هر توکن واچ‌لیست (قیمت خرید و فعلی)
def calculate_profit(token, buy_price):
    current_price = token.get('price_usd', 0)
    if buy_price == 0:
        return 0
    profit = ((current_price - buy_price) / buy_price) * 100
    return profit

# ارسال پیام پین شده روزانه در تلگرام
def send_daily_watchlist_summary():
    watchlist = load_watchlist()
    tokens = load_tokens()
    
    # نگاشت آدرس توکن به داده توکن
    tokens_map = {t['address']: t for t in tokens}

    message_lines = ["📌 *واچ‌لیست روزانه* 📌\n"]
    total_profit_percent = 0
    total_invested = 0

    if not watchlist:
        message_lines.append("_واچ‌لیست خالی است._")
    else:
        for item in watchlist:
            address = item['address']
            buy_price = item.get('buy_price', 0)
            amount = item.get('amount', 0)
            token = tokens_map.get(address, {})
            name = token.get('token_name', 'ناشناخته')
            symbol = token.get('token_symbol', '')
            current_price = token.get('price_usd', 0)
            profit_percent = calculate_profit(token, buy_price)
            total_invested += buy_price * amount
            total_profit_percent += profit_percent

            color = "🟢" if profit_percent >= 0 else "🔴"
            line = (
                f"{color} {name} ({symbol}): "
                f"خرید: {buy_price:.5f}$، قیمت فعلی: {current_price:.5f}$، "
                f"مقدار: {amount}, "
                f"سود/زیان: {profit_percent:.2f}%"
            )
            message_lines.append(line)
        
        avg_profit = total_profit_percent / len(watchlist)
        message_lines.append(f"\n*میانگین سود/زیان:* {avg_profit:.2f}%")

    message_text = "\n".join(message_lines)

    # ارسال پیام و پین کردن (حذف پین قبلی)
    try:
        bot.unpin_all_chat_messages(chat_id=TELEGRAM_CHAT_ID)
    except Exception:
        pass

    sent_message = bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message_text, parse_mode=telegram.ParseMode.MARKDOWN)
    bot.pin_chat_message(chat_id=TELEGRAM_CHAT_ID, message_id=sent_message.message_id)

@app.route('/')
def index():
    tokens = load_tokens()
    watchlist = load_watchlist()
    watchlist_addresses = {item['address'] for item in watchlist}
    filters = load_filters()

    # زمان آخرین بروزرسانی (به فرمت زمان محلی UTC+3:30 مثلا تهران)
    now = datetime.utcnow()
    # تبدیل UTC به تهران +3:30 ساعت
    local_time = now.replace(hour=(now.hour + 3) % 24, minute=(now.minute + 30) % 60)
    last_update = local_time.strftime('%Y-%m-%d %H:%M:%S')

    return render_template('index.html',
                           tokens=tokens,
                           watchlist_addresses=watchlist_addresses,
                           filters=filters,
                           last_update=last_update)

@app.route('/watch', methods=['POST'])
def watch():
    address = request.form.get('token_address')
    buy_price = float(request.form.get('buy_price', 0))
    amount = float(request.form.get('amount', 0))
    if not address:
        return redirect(url_for('index'))

    watchlist = load_watchlist()
    # اگر توکن قبلا اضافه نشده، اضافه کن
    if not any(item['address'] == address for item in watchlist):
        watchlist.append({
            'address': address,
            'buy_price': buy_price,
            'amount': amount
        })
        save_watchlist(watchlist)
        send_daily_watchlist_summary()

    return redirect(url_for('index'))

@app.route('/unwatch', methods=['POST'])
def unwatch():
    address = request.form.get('token_address')
    if not address:
        return redirect(url_for('index'))

    watchlist = load_watchlist()
    watchlist = [item for item in watchlist if item['address'] != address]
    save_watchlist(watchlist)
    send_daily_watchlist_summary()

    return redirect(url_for('index'))

@app.route('/watchlist')
def watchlist_view():
    watchlist = load_watchlist()
    tokens = load_tokens()
    tokens_map = {t['address']: t for t in tokens}

    detailed_list = []
    for item in watchlist:
        token = tokens_map.get(item['address'], {})
        if token:
            detailed = {
                'token_name': token.get('token_name', ''),
                'token_symbol': token.get('token_symbol', ''),
                'address': item['address'],
                'buy_price': item.get('buy_price', 0),
                'amount': item.get('amount', 0),
                'current_price': token.get('price_usd', 0),
                'profit_percent': calculate_profit(token, item.get('buy_price', 0))
            }
            detailed_list.append(detailed)

    return render_template('watchlist.html', watchlist=detailed_list)

@app.route('/edit_filters', methods=['GET', 'POST'])
def edit_filters():
    if request.method == 'POST':
        filters_json = request.form.get('filters_json')
        try:
            filters = json.loads(filters_json)
            save_filters(filters)
            return redirect(url_for('index'))
        except Exception:
            return "JSON نامعتبر است", 400
    else:
        filters = load_filters()
        filters_json = json.dumps(filters, ensure_ascii=False, indent=2)
        return render_template('edit_filters.html', filters_json=filters_json)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
