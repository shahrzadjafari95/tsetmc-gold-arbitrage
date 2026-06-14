import requests
from datetime import datetime, date
from app.db import SessionLocal
from app.models import CoinPrice

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.tgju.org",
    "Accept": "application/json",
}

def to_float(value: str) -> float | None:
    """Convert Persian-formatted number string like '1,740,100,000' to float."""
    if not value:
        return None
    try:
        return float(str(value).replace(",", ""))
    except (ValueError, TypeError):
        return None


def fetch_coin_price_today() -> dict | None:
    """Fetch today's سکه بهار آزادی price from tgju.org."""
    r = requests.get("https://call4.tgju.org/ajax.json", headers=HEADERS, timeout=10)
    r.raise_for_status()
    data = r.json().get("current", {})

    sekee = data.get("sekee")
    if not sekee:
        return None

    ts = sekee.get("ts", "")
    try:
        rec_date = datetime.strptime(ts[:10], "%Y-%m-%d").date()
    except ValueError:
        rec_date = date.today()

    return {
        "date": rec_date,
        "price": to_float(sekee.get("p")),
        "price_high": to_float(sekee.get("h")),
        "price_low": to_float(sekee.get("l")),
    }


def save_coin_price():
    rec = fetch_coin_price_today()
    if not rec:
        print("[سکه] ⚠️ No data returned")
        return

    print(f"[سکه] price={rec['price']:,.0f} | high={rec['price_high']:,.0f} | low={rec['price_low']:,.0f} | date={rec['date']}")

    db = SessionLocal()
    try:
        exists = db.query(CoinPrice).filter_by(record_date=rec["date"]).first()
        if exists:
            # Update with latest price
            exists.price = rec["price"]
            exists.price_high = rec["price_high"]
            exists.price_low = rec["price_low"]
            print("[سکه] Updated existing record")
        else:
            db.add(CoinPrice(
                record_date=rec["date"],
                price=rec["price"],
                price_high=rec["price_high"],
                price_low=rec["price_low"],
            ))
            print("[سکه] Saved new record")
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[سکه] ❌ Error: {e}")
    finally:
        db.close()