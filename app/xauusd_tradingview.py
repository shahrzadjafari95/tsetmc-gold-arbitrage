import json
import re
from datetime import datetime, timezone

import requests

from app.db import SessionLocal
from app.db import Base, engine
from app.models import XAUUSDTradingView

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.tradingview.com/",
}

TRADINGVIEW_SYMBOL_URL = "https://www.tradingview.com/symbols/XAUUSD/"


def fetch_xauusd_tradingview() -> dict | None:
    try:
        r = requests.get(TRADINGVIEW_SYMBOL_URL, headers=HEADERS, timeout=20)
        r.raise_for_status()
        html = r.text

        patterns = [
            r"the price of gold is\s+([0-9][0-9,]*\.?[0-9]*)\s+USD",
            r"price of gold is\s+([0-9][0-9,]*\.?[0-9]*)\s+USD",
            r"XAUUSD[^0-9]{0,40}([0-9][0-9,]*\.?[0-9]*)\s*USD",
        ]

        price = None
        for pattern in patterns:
            match = re.search(pattern, html, flags=re.IGNORECASE | re.DOTALL)
            if match:
                try:
                    price = float(match.group(1).replace(",", ""))
                    break
                except ValueError:
                    continue

        if price is None:
            raise ValueError("no XAU/USD price found on TradingView symbol page")

        return {
            "symbol": "XAUUSD",
            "price": price,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        print(f"⚠️ TradingView XAU/USD lookup failed: {exc}")

    return None


def save_xauusd_tradingview() -> dict | None:
    payload = fetch_xauusd_tradingview()
    if not payload:
        print("❌ Could not fetch XAU/USD from TradingView")
        return None

    db = SessionLocal()
    try:
        Base.metadata.create_all(bind=engine)
        db.add(
            XAUUSDTradingView(
                symbol=payload["symbol"],
                price=payload["price"],
                fetched_at=datetime.fromisoformat(payload["fetched_at"]),
            )
        )
        db.commit()
        print(json.dumps(payload, ensure_ascii=False))
        return payload
    finally:
        db.close()


if __name__ == "__main__":
    save_xauusd_tradingview()
