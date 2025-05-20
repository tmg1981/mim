import requests
import time

# تنظیمات اولیه
network = 'base'  # یا 'solana'
base_url = 'https://api.geckoterminal.com/api/v2'

# فیلترهای اولیه
min_liquidity = 110000
min_market_cap = 500000
min_age_minutes = 360  # 6 ساعت
min_volume_24h = 1000000
min_price_change_5m = 5

# دریافت استخرهای برتر در شبکه مورد نظر
def get_top_pools(network):
    url = f'{base_url}/networks/{network}/pools'
    params = {'include': 'base_token,quote_token'}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()['data']
    else:
        print(f"خطا در دریافت استخرها: {response.status_code}")
        return []

# دریافت اطلاعات توکن
def get_token_info(network, token_address):
    url = f'{base_url}/networks/{network}/tokens/{token_address}/info'
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()['data']['attributes']
    else:
        return {}

# دریافت اطلاعات هولدرها
def get_top_holders(network, token_address):
    url = f'{base_url}/networks/{network}/tokens/{token_address}/top_holders'
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()['data']
    else:
        return []

# بررسی فیلترها برای هر استخر
def filter_pools(pools):
    filtered = []
    for pool in pools:
        attributes = pool['attributes']
        liquidity = float(attributes.get('reserve_in_usd', 0))
        market_cap = float(attributes.get('market_cap_usd', 0) or 0)
        age_minutes = int(attributes.get('age_minutes', 0))
        volume_24h = float(attributes.get('volume_usd_24h', 0))
        price_change_5m = float(attributes.get('price_change_percentage_5m', 0))

        # اعمال فیلترهای اولیه
        if (liquidity >= min_liquidity and
            market_cap >= min_market_cap and
            age_minutes >= min_age_minutes and
            volume_24h >= min_volume_24h and
            price_change_5m >= min_price_change_5m):

            # دریافت اطلاعات توکن پایه
            base_token = attributes.get('base_token', {})
            token_address = base_token.get('address')
            token_info = get_token_info(network, token_address)
            social_links = token_info.get('socials', {})
            creator_token_count = token_info.get('creator_token_count', 0)

            # دریافت اطلاعات هولدرها
            holders = get_top_holders(network, token_address)
            top_10_percent = sum(float(holder['attributes']['percentage']) for holder in holders[:10])
            top_holder_percent = float(holders[0]['attributes']['percentage']) if holders else 0
            top_holder_label = holders[0]['attributes'].get('label', '') if holders else ''

            # بررسی فیلترهای اضافی
            risk_notes = []
            if top_10_percent > 25:
                risk_notes.append("🚨 با ریسک بالا (Top 10 Holders > 25%)")
            if creator_token_count > 0:
                risk_notes.append("🚨 با ریسک بالا (Creator Token Count > 0)")
            if top_holder_percent > 10:
                risk_notes.append("🚨 با ریسک بالا (Top Holder > 10%)")
            if top_holder_label.lower() != 'liquidity pool':
                risk_notes.append("🚨 با ریسک بالا (Top Holder is not Liquidity Pool)")

            # بررسی وجود لینک‌های اجتماعی
            has_socials = any(social_links.values())

            # افزودن به لیست نهایی
            filtered.append({
                'name': base_token.get('name'),
                'symbol': base_token.get('symbol'),
                'address': token_address,
                'liquidity': liquidity,
                'market_cap': market_cap,
                'age_minutes': age_minutes,
                'volume_24h': volume_24h,
                'price_change_5m': price_change_5m,
                'social_links': social_links,
                'risk_notes': risk_notes,
                'has_socials': has_socials
            })

            # تاخیر برای جلوگیری از محدودیت نرخ درخواست‌ها
            time.sleep(1)

    return filtered

# اجرای برنامه
if __name__ == "__main__":
    pools = get_top_pools(network)
    filtered_tokens = filter_pools(pools)
    for token in filtered_tokens:
        print(f"\n🪙 نام: {token['name']} ({token['symbol']})")
        print(f"🔗 آدرس: {token['address']}")
        print(f"📊 نقدینگی: ${token['liquidity']}")
        print(f"📈 مارکت کپ: ${token['market_cap']}")
        print(f"⏱ سن (دقیقه): {token['age_minutes']}")
        print(f"💰 حجم معاملات ۲۴ ساعته: ${token['volume_24h']}")
        print(f"📉 تغییر قیمت ۵ دقیقه‌ای: {token['price_change_5m']}%")
        print(f"🔗 لینک‌های اجتماعی: {token['social_links']}")
        for note in token['risk_notes']:
            print(note)
