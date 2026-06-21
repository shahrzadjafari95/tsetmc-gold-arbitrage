# app/brsapi_history.py
import requests
import gzip
import json
from datetime import date, timedelta
from app.db import SessionLocal
from app.models import FundLiveData
from app.gold_funds import GOLD_FUNDS
import time

API_KEY = "BE9KJxgJZkd2peD14HxrkWdfR9s8ZP8X"
URL = "https://Api.BrsApi.ir/IME/Fund.php"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9,fa;q=0.8",
    "Referer": "https://brsapi.ir/",
    "Origin": "https://brsapi.ir",
}


def fetch_funds_for_date(target_date: date) -> list[dict]:
    date_str = target_date.strftime("%Y%m%d")
    r = requests.get(
        URL,
        params={"key": API_KEY, "date": date_str},
        headers=HEADERS,
        timeout=15,
    )
    r.raise_for_status()

    content = r.content
    if content[:2] == b'\x1f\x8b':
        content = gzip.decompress(content)

    payload = json.loads(content.decode("utf-8"))
    if not payload.get("successful"):
        raise ValueError(f"API error: {payload.get('message_error')}")
    return payload.get("data", [])


def find_fund(funds: list[dict], ins_code: str) -> dict | None:
    for f in funds:
        if str(f.get("id")) == str(ins_code):
            return f
    return None


def parse_record(rec: dict, ins_code: str, record_date: date) -> dict:
    buy_vol_i    = rec.get("Buy_I_Volume") or 0
    sell_vol_i   = rec.get("Sell_I_Volume") or 0
    buy_count_i  = rec.get("Buy_CountI") or 1
    sell_count_i = rec.get("Sell_CountI") or 1

    return dict(
        ins_code            = ins_code,
        record_date         = record_date,
        record_time         = rec.get("time"),
        p_closing           = rec.get("pc"),
        p_last              = rec.get("pl"),
        p_first             = rec.get("pf"),
        p_min               = rec.get("pmin"),
        p_max               = rec.get("pmax"),
        p_yesterday         = rec.get("py"),
        p_change            = rec.get("pcc"),
        p_change_pct        = rec.get("pcp"),
        trade_count         = rec.get("tno"),
        trade_volume        = rec.get("tvol"),
        trade_value         = rec.get("tval"),
        buy_count_i         = rec.get("Buy_CountI"),
        buy_count_n         = rec.get("Buy_CountN"),
        sell_count_i        = rec.get("Sell_CountI"),
        sell_count_n        = rec.get("Sell_CountN"),
        buy_vol_i           = buy_vol_i,
        buy_vol_n           = rec.get("Buy_N_Volume"),
        sell_vol_i          = sell_vol_i,
        sell_vol_n          = rec.get("Sell_N_Volume"),
        buy_per_capita_i    = buy_vol_i  / buy_count_i  if buy_count_i  else None,
        sell_per_capita_i   = sell_vol_i / sell_count_i if sell_count_i else None,
        net_individual_flow = buy_vol_i - sell_vol_i,
    )


def get_trading_days(start: date, end: date) -> list[date]:
    """Return all weekdays (Sat–Wed for Iran) between start and end."""
    days = []
    current = start
    while current <= end:
        # Iranian market: Saturday=5, Sunday=6, Monday=0, Tuesday=1, Wednesday=2
        # Skip Thursday(3) and Friday(4)
        if current.weekday() not in (3, 4):  # not Thursday or Friday
            days.append(current)
        current += timedelta(days=1)
    return days


def run_history_scraper(days_back: int = 365):
    """Fetch historical fund data for past N days."""
    end_date   = date.today() - timedelta(days=1)  # yesterday
    start_date = end_date - timedelta(days=days_back)
    trading_days = get_trading_days(start_date, end_date)

    print(f"📅 Fetching {len(trading_days)} trading days: {start_date} → {end_date}")

    db = SessionLocal()
    total_inserted = total_skipped = total_errors = 0

    try:
        for i, target_date in enumerate(trading_days):
            date_str = target_date.strftime("%Y-%m-%d")
            print(f"\n[{i+1}/{len(trading_days)}] 📆 {date_str}", end=" ")

            # Check if we already have data for this date
            existing_count = db.query(FundLiveData).filter_by(
                record_date=target_date
            ).count()
            if existing_count >= len(GOLD_FUNDS):
                print(f"⏭️  already complete ({existing_count} records)")
                total_skipped += existing_count
                continue

            try:
                all_funds = fetch_funds_for_date(target_date)
                if not all_funds:
                    print("⚠️  no data returned")
                    continue

                print(f"✅ {len(all_funds)} funds received")

                day_inserted = day_skipped = 0

                for name, ins_code in GOLD_FUNDS.items():
                    fund = find_fund(all_funds, ins_code)
                    if not fund:
                        continue

                    exists = db.query(FundLiveData).filter_by(
                        ins_code=ins_code,
                        record_date=target_date,
                    ).first()

                    if exists:
                        day_skipped += 1
                        continue

                    parsed = parse_record(fund, ins_code, target_date)
                    db.add(FundLiveData(**parsed))
                    day_inserted += 1

                db.commit()
                total_inserted += day_inserted
                total_skipped  += day_skipped
                print(f"   💾 inserted: {day_inserted} | skipped: {day_skipped}")

                # Be polite to the API — don't hammer it
                time.sleep(0.5)

            except Exception as e:
                print(f"   ❌ Error: {e}")
                total_errors += 1
                db.rollback()
                time.sleep(2)  # wait longer after error

    finally:
        db.close()

    print(f"\n{'═' * 50}")
    print(f"✅ Total inserted : {total_inserted}")
    print(f"⏭️  Total skipped  : {total_skipped}")
    print(f"❌ Total errors   : {total_errors}")


if __name__ == "__main__":
    run_history_scraper(days_back=365)