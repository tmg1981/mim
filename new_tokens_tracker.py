import requests
from datetime import datetime, timezone

def fetch_new_tokens():
    url = "https://api.dexscreener.com/latest/dex/pairs"
    try:
        response = requests.get(url)

        if response.status_code != 200:
            print(f"❌ HTTP Error {response.status_code}: {response.text}")
            return

        data = response.json()

        print("\n🔍 Checking NEW tokens on BASE & SOLANA...\n")

        for token in data.get("pairs", []):
            chain = token.get("chainId", "").lower()
            if chain not in ["base", "solana"]:
                continue

            pair_created_at = token.get("pairCreatedAt")
            if not pair_created_at:
                continue

            created_datetime = datetime.fromtimestamp(pair_created_at / 1000, tz=timezone.utc)
            now = datetime.now(timezone.utc)
            age_minutes = (now - created_datetime).total_seconds() / 60

            if age_minutes <= 5:
                print(f"🆕 Token: {token['baseToken']['symbol']} / {token['baseToken']['address']}")
                print(f"🌐 Chain: {chain}")
                print(f"📈 DEX: {token['dexId']}")
                print(f"💰 Liquidity (USD): {token.get('liquidity', {}).get('usd', 'N/A')}")
                print(f"🔗 Pair URL: {token['url']}")
                print(f"⏱ Age: {round(age_minutes, 2)} min")
                print("-" * 50)

    except Exception as e:
        print("❌ Error fetching data:", e)

if __name__ == "__main__":
    fetch_new_tokens()
