import requests
from datetime import date
from app.db import SessionLocal
from app.models import EmamiCoinPrice

HEADERS = {"User-Agent": "Mozilla/5.0"}


def fetch_emami_price() -> float | None:
    url = "https://call4.tgju.org/ajax.json"
    r = requests.get(url, headers=HEADERS, timeout=10)
    data = r.json().get("current", {})
    raw = data.get("sekee", {}).get("p")  # ✅ correct key
    if raw:
        return float(str(raw).replace(",", ""))
    return None


def save_emami_price():
    price = fetch_emami_price()
    if not price:
        print("❌ Could not fetch Emami price")
        return

    today = date.today()
    db = SessionLocal()
    try:
        exists = db.query(EmamiCoinPrice).filter_by(record_date=today).first()
        if exists:
            exists.price = price
        else:
            db.add(EmamiCoinPrice(record_date=today, price=price))
        db.commit()
        print(f"✅ Emami coin price: {price:,.0f} IRR")
    finally:
        db.close()


if __name__ == "__main__":
    save_emami_price()