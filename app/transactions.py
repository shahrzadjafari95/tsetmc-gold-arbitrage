import requests
import jdatetime
from datetime import date, timedelta
from app.db import SessionLocal
from app.models import FundTransaction
from app.gold_funds import GOLD_FUNDS

BRSAPI_KEY = "BE9KJxgJZkd2peD14HxrkWdfR9s8ZP8X"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://brsapi.ir",
}


def gregorian_to_jalali(d: date) -> str:
    return jdatetime.date.fromgregorian(date=d).strftime("%Y-%m-%d")


def fetch_transactions(fund_name: str, target_date: date) -> tuple[list[dict], str]:
    """
    Fetch transactions for a fund on a given date.
    Returns (records, status) where status is one of:
      'ok', 'plan_limit', 'quota_exhausted', 'empty', 'error'
    """
    jalali_date = gregorian_to_jalali(target_date)
    url = f"https://Api.BrsApi.ir/Tsetmc/Transaction.php?key={BRSAPI_KEY}&l18={fund_name}&date={jalali_date}"

    try:
        r = requests.get(url, headers=HEADERS, timeout=15)

        if r.status_code == 402:
            data = r.json()
            msg = data.get("message_error", "")
            # distinguish between plan limit and daily quota exhausted
            if "امروز" in msg or "پایان رسیده" in msg:
                return [], "quota_exhausted"
            return [], "plan_limit"

        r.raise_for_status()
        data = r.json()

        if not isinstance(data, list):
            return [], "error"

        return data, "ok"

    except Exception as e:
        print(f"  ❌ [{fund_name}] Request error: {e}")
        return [], "error"


def save_transactions(fund_name: str, target_date: date) -> dict:
    records, status = fetch_transactions(fund_name, target_date)

    result = {"status": status, "saved": 0, "skipped": 0, "total": len(records)}

    if status != "ok" or not records:
        return result

    db = SessionLocal()
    try:
        saved = skipped = 0
        for rec in records:
            if rec.get("canceled", 0) == 1:
                continue

            exists = db.query(FundTransaction).filter_by(
                fund_name=fund_name,
                record_date=target_date,
                row=rec["row"],
            ).first()

            if exists:
                skipped += 1
                continue

            db.add(FundTransaction(
                fund_name=fund_name,
                record_date=target_date,
                row=rec["row"],
                time=rec.get("time"),
                volume=rec.get("volume"),
                price=rec.get("price"),
                canceled=rec.get("canceled", 0),
            ))
            saved += 1

        db.commit()
        result["saved"] = saved
        result["skipped"] = skipped
        return result

    except Exception as e:
        db.rollback()
        print(f"  ❌ [{fund_name}] DB error: {e}")
        result["status"] = "error"
        return result
    finally:
        db.close()


def run_transactions_scraper(days: int = 1):
    """Fetch transactions for all 31 funds for the last `days` trading days."""
    print(f"\n=== Fetching transactions for {len(GOLD_FUNDS)} funds ===")

    dates = [date.today() - timedelta(days=i) for i in range(days)]

    quota_exhausted = False  # stop all requests if daily quota is hit

    for fund_name in GOLD_FUNDS:
        if quota_exhausted:
            print(f"  ⏸️  [{fund_name}] Skipped — daily quota exhausted")
            continue

        total_saved = total_skipped = 0
        for target_date in dates:
            result = save_transactions(fund_name, target_date)

            if result["status"] == "quota_exhausted":
                print(f"  🚫 Daily quota exhausted — stopping all requests for today")
                quota_exhausted = True
                break

            elif result["status"] == "plan_limit":
                print(f"  💳 [{fund_name}] Requires paid plan — skipping")
                break  # no point trying other dates for this fund

            elif result["status"] == "ok":
                total_saved += result["saved"]
                total_skipped += result["skipped"]

        if not quota_exhausted and result["status"] == "ok":
            print(f"  ✅ [{fund_name}] Saved: {total_saved} | Skipped: {total_skipped} | Total: {result['total']}")

    if quota_exhausted:
        print("\n⚠️  Free daily quota reached. Resets tomorrow.")
        print("   Upgrade at https://brsapi.ir to remove this limit and access all 31 funds.")

        