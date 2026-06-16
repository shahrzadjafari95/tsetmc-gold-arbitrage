import yfinance as yf
from datetime import date, timedelta
from app.db import SessionLocal
from app.models import GoldPrice


def fetch_xau_usd_history(days: int = 365) -> list[dict]:
    """Fetch XAU/USD daily prices using Yahoo Finance (free, no API key)."""
    end = date.today()
    start = end - timedelta(days=days)

    ticker = yf.Ticker("GC=F")  # Gold Futures (closest to spot XAU/USD)
    df = ticker.history(start=str(start), end=str(end), interval="1d")

    if df.empty:
        print("[XAU/USD] ⚠️ No data returned from Yahoo Finance")
        return []

    results = []
    for idx, row in df.iterrows():
        results.append({
            "date": idx.date(),
            "xau_usd": round(float(row["Close"]), 2),
        })

    return results


def save_xau_usd(days: int = 365):
    records = fetch_xau_usd_history(days)
    print(f"[XAU/USD] Fetched {len(records)} records")

    db = SessionLocal()
    try:
        saved = skipped = 0
        for rec in records:
            exists = db.query(GoldPrice).filter_by(record_date=rec["date"]).first()
            if exists:
                skipped += 1
                continue
            db.add(GoldPrice(
                record_date=rec["date"],
                xau_usd=rec["xau_usd"],
            ))
            saved += 1
        db.commit()
        print(f"[XAU/USD] Saved: {saved} | Skipped: {skipped}")
    except Exception as e:
        db.rollback()
        print(f"[XAU/USD] ❌ Error: {e}")
    finally:
        db.close()


def get_xau_usd_now() -> float | None:
    """Fetch live current XAU/USD price."""

    ticker = yf.Ticker("GC=F")
    price = ticker.fast_info.last_price
    return round(float(price), 2) if price else None


def get_xau_usd_latest_from_db() -> dict | None:
    """Get the most recent XAU/USD price saved in DB."""
    db = SessionLocal()
    try:
        row = db.query(GoldPrice).order_by(GoldPrice.record_date.desc()).first()
        if row:
            return {"date": row.record_date, "xau_usd": row.xau_usd}
        return None
    finally:
        db.close()