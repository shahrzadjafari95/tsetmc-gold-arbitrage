import requests
from datetime import date
from app.db import SessionLocal
from app.models import GoldPrice18K

HEADERS = {"User-Agent": "Mozilla/5.0"}


def fetch_prices() -> tuple[float | None, float | None, float | None]:
    url = "https://call4.tgju.org/ajax.json"
    r = requests.get(url, headers=HEADERS, timeout=10)
    data = r.json().get("current", {})

    def clean(key):
        val = data.get(key, {}).get("p")
        return float(str(val).replace(",", "")) if val else None

    xau_usd = clean("ons")               # طلای جهانی (اونس دلار)
    usd_irr = clean("price_dollar_rl")   # نرخ دلار (ریال)
    gold_18k_irr = clean("tgju_gold_irg18")  # ✅ طلای ۱۸ عیار گرمی (ریال) — direct!

    return xau_usd, usd_irr, gold_18k_irr


def save_gold_18k_price():
    xau_usd, usd_irr, gold_18k_irr = fetch_prices()

    if not gold_18k_irr:
        print("❌ Could not fetch 18K gold price")
        return

    today = date.today()
    db = SessionLocal()
    try:
        exists = db.query(GoldPrice18K).filter_by(record_date=today).first()
        if exists:
            exists.xau_usd = xau_usd
            exists.usd_irr = usd_irr
            exists.gold_18k_irr = gold_18k_irr
        else:
            db.add(GoldPrice18K(
                record_date=today,
                xau_usd=xau_usd,
                usd_irr=usd_irr,
                gold_18k_irr=gold_18k_irr,
            ))
        db.commit()
        print(f"✅ XAU/USD: {xau_usd:,.2f} | USD/IRR: {usd_irr:,.0f} | 18K/gram IRR: {gold_18k_irr:,.0f}")
    finally:
        db.close()


if __name__ == "__main__":
    save_gold_18k_price()