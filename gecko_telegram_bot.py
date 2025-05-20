import requests
import time

# تنظیمات API
base_url = 'https://api.geckoterminal.com/api/v2'
networks = ['base', 'solana']

# تنظیمات فیلترها
min_liquidity = 110000
min_market_cap = 500000
min_age_minutes = 360
min_volume_24h = 1000000
min_price_change_5m = 5

# تنظیمات تلگرام
TELEGRAM_TOKEN = '7672274033:AAET9Jpt34MQwnCnzruGeqV6_AkBQcJ7biI'
CHAT_ID = 174861276

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
    else:
        print(f"❌ خطا در دریافت استخرهای {network}: {response.status_code}")
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

def filter_pools(network, pools):
    found = False
    for pool in pools:
        attributes = pool['attributes']
        liquidity = float(attributes.get('reserve_in_usd', 0))
        market_cap = float(attributes.get('market_cap_usd', 0) or 0)
        age_minutes = int(attributes.get('age_minutes', 0))
        volume_24h = float(attributes.get('volume_usd_24h', 0))
        price_change_5m = float(attributes.get('price_change_percentage_5m', 0))

        if (liquidity >= min_liquidity and
            market_cap >= min_market_cap and
            age_minutes >= min_age_minutes and
            volume_24h >= min_volume_24h and
            price_change_5m >= min_price_change_5m):

            base_token = attributes.get('base_token', {})
            token_address = base_token.get('address')
            token_info = get_token_info(network, token_address)
            socials = token_info.get('socials', {})
            creator_token_count = token_info.get('creator_token_count', 0)

            holders = get_top_holders(network, token_address)
            top_10_percent = sum(float(h['attributes']['percentage']) for h in holders[:10]) if holders else 0
            top_holder_percent = float(holders[0]['attributes']['percentage']) if holders else 0
            top_holder_label = holders[0]['attributes'].get('label', '') if holders else ''

            risk_notes = []
            if top_10_percent > 25:
                risk_notes.append("🚨 <b>ریسک: Top 10 > 25%</b>")
            if creator_token_count > 0:
                risk_notes.append("🚨 <b>ریسک: Creator سابقه دارد</b>")
            if top_holder_percent > 10:
                risk_notes.append("🚨 <b>ریسک: یک نفر بیش از 10%</b>")
            if top_holder_label.lower() != 'liquidity pool':
                risk_notes.append("🚨 <b>ریسک: بزرگترین هولدر شخصی است</b>")

            msg = f"""
🧠 <b>شبکه:</b> {network.upper()}
🪙 <b>{base_token.get('name')} ({base_token.get('symbol')})</b>
💰 <b>Liquidity:</b> ${liquidity:,.0f}
📈 <b>Market Cap:</b> ${market_cap:,.0f}
⏱ <b>Age:</b> {age_minutes} mins
📊 <b>24h Volume:</b> ${volume_24h:,.0f}
📉 <b>5m Change:</b> {price_change_5m}%
🔗 <b>Token:</b> <code>{token_address}</code>
🌐 <b>Socials:</b> {'✅' if any(socials.values()) else '❌'}
""" + '\n'.join(risk_notes)

            send_telegram_message(msg)
            found = True
            time.sleep(1)

    if not found:
        send_telegram_message(f"📡 <b>{network.upper()}</b> ➤ فعلاً موردی یافت نشد.")

if __name__ == '__main__':
    for network in networks:
        pools = get_top_pools(network)
        filter_pools(network, pools)
