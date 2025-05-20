from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import httpx
import datetime

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# پارامترهای فیلتر (تعدیل‌شده)
MIN_LIQUIDITY = 90000
MIN_MARKET_CAP = 500000
MIN_AGE_HOURS = 6
MIN_VOLUME_24H = 1000000
MIN_PRICE_CHANGE_5M = 5

# توابع کمکی
def filter_token(token):
    try:
        liquidity = float(token.get("liquidity_usd", 0))
        market_cap = float(token.get("market_cap_usd", 0))
        age_hours = float(token.get("age_hours", 0))
        volume_24h = float(token.get("volume_usd_24h", 0))
        price_change_5m = float(token.get("price_change_percentage_5m", 0))

        if liquidity < MIN_LIQUIDITY:
            return False
        if market_cap < MIN_MARKET_CAP:
            return False
        if age_hours < MIN_AGE_HOURS:
            return False
        if volume_24h < MIN_VOLUME_24H:
            return False
        if price_change_5m < MIN_PRICE_CHANGE_5M:
            return False

        return True
    except:
        return False

async def get_filtered_tokens():
    url = "https://api.dexscreener.com/latest/dex/tokens"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()

        tokens = []
        for token in data.get("tokens", []):
            if filter_token(token):
                tokens.append({
                    "name": token.get("name"),
                    "symbol": token.get("symbol"),
                    "liquidity": token.get("liquidity_usd"),
                    "market_cap": token.get("market_cap_usd"),
                    "age_hours": token.get("age_hours"),
                    "volume_24h": token.get("volume_usd_24h"),
                    "price_change_5m": token.get("price_change_percentage_5m"),
                    "url": token.get("url"),
                    "dex": token.get("dex_name")
                })

        return tokens

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    tokens = await get_filtered_tokens()
    last_updated = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not tokens:
        tokens = [{"name": "فعلا موردی یافت نشد", "symbol": "", "liquidity": "", "market_cap": "",
                   "age_hours": "", "volume_24h": "", "price_change_5m": "", "url": "", "dex": ""}]
    return templates.TemplateResponse("dashboard.html", {"request": request, "tokens": tokens, "last_updated": last_updated})
