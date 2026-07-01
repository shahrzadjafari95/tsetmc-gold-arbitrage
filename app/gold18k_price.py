# app/gold18k_price.py
import requests
from datetime import date, timedelta, datetime, timezone
import json
from app.db import SessionLocal
from app.models import GoldPrice18K

HEADERS = {
    "User-Agent":      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept":          "application/json, text/plain, */*",
    "Accept-Language": "fa-IR,fa;q=0.9,en-US;q=0.8",
    "Referer":         "https://www.tradingview.com/",
}

TRADINGVIEW_SCAN_URL = "https://scanner.tradingview.com/forex/scan"
BASE_URL  = "https://api.tgju.org/v1/market/indicator/summary-table-data"
LIVE_URL  = "https://call4.tgju.org/ajax.json"

# slug → DB field
SLUGS = {
    "ons":             "xau_usd",
    "price_dollar_rl": "usd_irr",
    "geram18":         "gold_18k_irr",
}


# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────

def _clean(val) -> float | None:
    """Convert '161,600,000' or 4141.47 to float."""
    if val is None:
        return None
    try:
        return float(str(val).replace(",", ""))
    except (ValueError, TypeError):
        return None


def _parse_date(date_str: str) -> date | None:
    """Parse 'YYYY/MM/DD' gregorian date string."""
    try:
        parts = date_str.strip().split("/")
        y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
        if y > 1800:  # gregorian
            return date(y, m, d)
        # jalali — skip, we use gregorian column (index 6)
        return None
    except Exception:
        return None


def _fetch_all_pages(slug: str) -> dict[date, float]:
    """
    Fetch all pages from tgju historical API for a slug.
    Returns {date: close_price}
    """
    result: dict[date, float] = {}
    start  = 0
    length = 500  # max per page

    while True:
        r = requests.get(
            f"{BASE_URL}/{slug}",
            params={"start": start, "length": length},
            headers=HEADERS,
            timeout=15,
        )
        r.raise_for_status()
        data  = r.json()
        rows  = data.get("data", [])
        total = data.get("recordsTotal", 0)

        for row in rows:
            # row: [close, low, high, open, change_html, pct_html, gregorian, jalali]
            try:
                close     = _clean(row[0])
                greg_date = _parse_date(row[6])
                if close and greg_date:
                    result[greg_date] = close
            except (IndexError, Exception):
                continue

        start += length
        if start >= total:
            break

    return result


def _fetch_live() -> dict:
    """Fetch today's prices from live endpoint."""
    r = requests.get(LIVE_URL, headers=HEADERS, timeout=10)
    r.raise_for_status()
    current = r.json().get("current", {})

    def get(key):
        return _clean(current.get(key, {}).get("p"))

    return {
        "xau_usd":      get("ons"),
        "usd_irr":      get("price_dollar_rl"),
        "gold_18k_irr": get("tgju_gold_irg18"),
    }


def _fetch_xau_usd_from_tradingview() -> dict | None:
    """
    Fetch XAU/USD from TradingView scanner.
    Uses a small fallback list because the exact symbol can vary by provider.
    """
    candidates = [
        "OANDA:XAUUSD",
        "FX_IDC:XAUUSD",
        "TVC:GOLD",
    ]

    payload_template = {
        "columns": ["close"],
        "symbols": {"tickers": [], "query": {"types": []}},
    }

    for symbol in candidates:
        payload = {
            **payload_template,
            "symbols": {
                "tickers": [symbol],
                "query": {"types": []},
            },
        }

        try:
            r = requests.post(TRADINGVIEW_SCAN_URL, json=payload, headers=HEADERS, timeout=15)
            r.raise_for_status()
            data = r.json().get("data", [])
            if not data:
                continue

            row = data[0]
            values = row.get("d", [])
            if not values:
                continue

            price = _clean(values[0])
            if price:
                return {
                    "symbol": symbol.split(":", 1)[-1],
                    "price": price,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                }
        except Exception:
            continue

    return None


# ─────────────────────────────────────────
# DB UPSERT
# ─────────────────────────────────────────

def _upsert(db, record_date: date, prices: dict) -> str:
    exists = db.query(GoldPrice18K).filter_by(record_date=record_date).first()
    if exists:
        exists.xau_usd      = prices.get("xau_usd")
        exists.usd_irr      = prices.get("usd_irr")
        exists.gold_18k_irr = prices.get("gold_18k_irr")
        return "updated"
    db.add(GoldPrice18K(
        record_date  = record_date,
        xau_usd      = prices.get("xau_usd"),
        usd_irr      = prices.get("usd_irr"),
        gold_18k_irr = prices.get("gold_18k_irr"),
    ))
    return "inserted"


# ─────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────

def save_today_price() -> dict | None:
    """Fetch and save today's gold prices, then return the TradingView payload."""
    prices = _fetch_live()
    xau_tv = _fetch_xau_usd_from_tradingview()
    if xau_tv:
        prices["xau_usd"] = xau_tv["price"]
    if not prices["gold_18k_irr"]:
        print("❌ Could not fetch 18K gold price")
        return None

    db = SessionLocal()
    try:
        action = _upsert(db, date.today(), prices)
        db.commit()
        print(
            f"✅ [{action}] "
            f"XAU/USD (TradingView): {prices['xau_usd']:,.2f} | "
            f"USD/IRR: {prices['usd_irr']:,.0f} | "
            f"18K/gram: {prices['gold_18k_irr']:,.0f}"
        )
        if xau_tv:
            print(json.dumps(xau_tv, ensure_ascii=False))
        return xau_tv
    finally:
        db.close()


def save_price_for_date(target_date: date) -> None:
    """Fetch and save gold prices for a specific date."""
    print(f"📅 Fetching prices for {target_date}...")

    # Fetch all history for each slug, then pick the target date
    prices = {"xau_usd": None, "usd_irr": None, "gold_18k_irr": None}

    for slug, field in SLUGS.items():
        try:
            all_data = _fetch_all_pages(slug)
            prices[field] = all_data.get(target_date)
        except Exception as e:
            print(f"  ⚠️ {slug}: {e}")

    if not any(prices.values()):
        print(f"❌ No data found for {target_date}")
        return

    db = SessionLocal()
    try:
        action = _upsert(db, target_date, prices)
        db.commit()
        print(
            f"✅ [{action}] {target_date} | "
            f"XAU/USD (TradingView): {prices['xau_usd']} | "
            f"USD/IRR: {prices['usd_irr']} | "
            f"18K/gram: {prices['gold_18k_irr']}"
        )
    finally:
        db.close()


def save_history(days_back: int = 365) -> None:
    """Fetch and save full history for all slugs."""
    end_date   = date.today()
    start_date = end_date - timedelta(days=days_back)
    print(f"📅 Fetching gold price history: {start_date} → {end_date}")

    # Fetch all pages for each slug once
    all_data: dict[str, dict[date, float]] = {}
    for slug, field in SLUGS.items():
        try:
            print(f"  📡 Fetching {slug}...", end=" ", flush=True)
            all_data[field] = _fetch_all_pages(slug)
            print(f"✅ {len(all_data[field])} records")
        except Exception as e:
            print(f"❌ {e}")
            all_data[field] = {}

    # Collect all dates in range
    all_dates = set()
    for field_data in all_data.values():
        all_dates.update(d for d in field_data if start_date <= d <= end_date)

    if not all_dates:
        print("❌ No data in range")
        return

    db = SessionLocal()
    inserted = updated = 0
    try:
        for rec_date in sorted(all_dates):
            prices = {
                "xau_usd":      all_data["xau_usd"].get(rec_date),
                "usd_irr":      all_data["usd_irr"].get(rec_date),
                "gold_18k_irr": all_data["gold_18k_irr"].get(rec_date),
            }
            action = _upsert(db, rec_date, prices)
            if action == "inserted":
                inserted += 1
            else:
                updated += 1

        db.commit()
        print(f"\n✅ inserted: {inserted} | updated: {updated}")
    finally:
        db.close()


# ─────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) == 1:
        payload = save_today_price()
        if payload:
            print(json.dumps(payload, ensure_ascii=False))

    elif sys.argv[1] == "history":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 365
        save_history(days_back=days)

    else:
        try:
            target = date.fromisoformat(sys.argv[1])
            save_price_for_date(target)
        except ValueError:
            print(f"❌ Invalid date: {sys.argv[1]} — use YYYY-MM-DD")
