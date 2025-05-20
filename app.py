from flask import Flask, render_template, request, jsonify
import requests
import time
import threading
import json
import os
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = int(os.getenv('CHAT_ID'))


app = Flask(__name__)

# تنظیمات API
base_url = 'https://api.geckoterminal.com/api/v2'
networks = ['solana', 'base', 'arbitrum']

# فیلترها
min_market_cap = 500000
min_volume_24h = 1000000
min_price_change_5m = 5
max_age_minutes = 120  # توکن تازه‌لانچ‌شده
min_liquidity = 90000
min_liq_to_cap_ratio = 0.3
max_total_supply = 1_000_000_000


# کش دیتا
DATA_CACHE = []
last_updated = None
WATCHLIST_FILE = 'watchlist.json'
if not os.path.exists(WATCHLIST_FILE):
    with open(WATCHLIST_FILE, 'w') as f:
        json.dump([], f)

def send_telegram_message(message):
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    data = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'HTML'
    }
    requests.post(url, data=data)

def get_top_pools(network):
    url = f'{base_url}/networks/{network}/pools'
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get('data', [])
    return []

def get_token_info(network, token_address):
    url = f'{base_url}/networks/{network}/tokens/{token_address}/info'
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get('data', {}).get('attributes', {})
    return {}

def get_top_holders(network, token_address):
    url = f'{base_url}/networks/{network}/tokens/{token_address}/top_holders'
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get('data', [])
    return []

def fetch_data():
    global DATA_CACHE, last_updated
    DATA_CACHE = []
    for network in networks:
        try:
            pools = get_top_pools(network)
            for pool in pools:
                attributes = pool['attributes']
                liquidity = float(attributes.get('reserve_in_usd', 0))
                market_cap = float(attributes.get('market_cap_usd', 0) or 0)
                age_minutes = int(attributes.get('age_minutes', 0))
                volume_24h = float(attributes.get('volume_usd_24h', 0))
                price_change_5m = float(attributes.get('price_change_percentage_5m', 0))

                base_token = attributes.get('base_token', {})
                token_address = base_token.get('address')
                token_name = base_token.get('name')
                token_symbol = base_token.get('symbol')

                # فیلترهای اولیه
                if (not token_name or not token_symbol or
                    market_cap < min_market_cap or
                    liquidity < min_liquidity or
                    market_cap == 0 or
                    liquidity / market_cap < min_liq_to_cap_ratio or
                    age_minutes > max_age_minutes or
                    volume_24h < min_volume_24h or
                    price_change_5m < min_price_change_5m):
                    continue

                token_info = get_token_info(network, token_address)
                socials = token_info.get('socials', {})
                creator_token_count = token_info.get('creator_token_count', 0)
                total_supply = float(token_info.get('total_supply', 0) or 0)

                if total_supply > max_total_supply:
                    continue

                holders = get_top_holders(network, token_address)
                top_10_percent = sum(float(h['attributes']['percentage']) for h in holders[:10]) if holders else 0
                top_holder_percent = float(holders[0]['attributes']['percentage']) if holders else 0
                top_holder_label = holders[0]['attributes'].get('label', '') if holders else ''

                # بررسی ریسک‌ها
                risk_notes = []
                if top_10_percent > 25:
                    risk_notes.append("Top 10 > 25%")
                if creator_token_count > 0:
                    risk_notes.append("Creator سابقه دارد")
                if top_holder_percent > 10:
                    risk_notes.append("1 نفر > 10%")
                if top_holder_label.lower() != 'liquidity pool':
                    risk_notes.append("هولدر اول شخصی است")
                if not socials.get('twitter') and not socials.get('telegram'):
                    risk_notes.append("بدون سوشال‌مدیا")

                token_data = {
                    'network': network,
                    'token_name': token_name,
                    'token_symbol': token_symbol,
                    'liquidity': liquidity,
                    'market_cap': market_cap,
                    'age': age_minutes,
                    'volume_24h': volume_24h,
                    'price_change_5m': price_change_5m,
                    'address': token_address,
                    'socials': socials,
                    'risks': risk_notes
                }

                DATA_CACHE.append(token_data)
        except Exception as e:
            print(f"خطا در پردازش شبکه {network}: {e}")
    last_updated = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())

def auto_fetch():
    while True:
        fetch_data()
        time.sleep(60)

def send_watchlist_to_telegram():
    with open(WATCHLIST_FILE, 'r') as f:
        watchlist = json.load(f)

    for item in DATA_CACHE:
        if item['address'] in watchlist:
            msg = f"""
📢 <b>{item['token_name']} ({item['token_symbol']})</b>
🌐 <b>Network:</b> {item['network']}
💰 <b>Liquidity:</b> ${item['liquidity']:,.0f}
📈 <b>Market Cap:</b> ${item['market_cap']:,.0f}
⏱ <b>Age:</b> {item['age']} mins
📊 <b>24h Volume:</b> ${item['volume_24h']:,.0f}
📉 <b>5m Change:</b> {item['price_change_5m']}%
🔗 <b>Token:</b> <code>{item['address']}</code>
🚨 <b>Risks:</b> {' | '.join(item['risks']) if item['risks'] else 'None'}
"""
            send_telegram_message(msg)

def auto_telegram():
    while True:
        send_watchlist_to_telegram()
        time.sleep(60)

@app.route('/')
def index():
    return render_template('index.html', tokens=DATA_CACHE, last_updated=last_updated)

@app.route('/watchlist', methods=['POST'])
def add_to_watchlist():
    token_address = request.json.get('address')
    with open(WATCHLIST_FILE, 'r+') as f:
        watchlist = json.load(f)
        if token_address not in watchlist:
            watchlist.append(token_address)
            f.seek(0)
            json.dump(watchlist, f)
            f.truncate()
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    threading.Thread(target=auto_fetch, daemon=True).start()
    threading.Thread(target=auto_telegram, daemon=True).start()
    app.run(debug=True)
