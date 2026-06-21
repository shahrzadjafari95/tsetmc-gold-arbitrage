import requests
from datetime import date
from app.db import SessionLocal
from app.models import FundLiveData
from app.gold_funds import GOLD_FUNDS

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


def fetch_all_funds() -> list[dict]:
    r = requests.get(URL, params={"key": API_KEY}, headers=HEADERS, timeout=10)
    r.raise_for_status()
    payload = r.json()
    if not payload.get("successful"):
        raise ValueError(f"API error: {payload.get('message_error')}")
    return payload["data"]


def find_fund_by_id(funds: list[dict], ins_code: str) -> dict | None:
    for f in funds:
        if str(f.get("id")) == str(ins_code):
            return f
    return None


def parse_record(rec: dict, ins_code: str) -> dict:
    buy_vol_i   = rec.get("Buy_I_Volume") or 0
    sell_vol_i  = rec.get("Sell_I_Volume") or 0
    buy_count_i = rec.get("Buy_CountI") or 1
    sell_count_i= rec.get("Sell_CountI") or 1

    return {
        "ins_code":             ins_code,
        "record_date":          date.today(),
        "record_time":          rec.get("time"),
        # قیمت‌ها
        "p_closing":            rec.get("pc"),
        "p_last":               rec.get("pl"),
        "p_first":              rec.get("pf"),
        "p_min":                rec.get("pmin"),
        "p_max":                rec.get("pmax"),
        "p_yesterday":          rec.get("py"),
        "p_change":             rec.get("pcc"),
        "p_change_pct":         rec.get("pcp"),
        # حجم و ارزش
        "trade_count":          rec.get("tno"),
        "trade_volume":         rec.get("tvol"),
        "trade_value":          rec.get("tval"),
        # خریدار / فروشنده
        "buy_count_i":          rec.get("Buy_CountI"),
        "buy_count_n":          rec.get("Buy_CountN"),
        "sell_count_i":         rec.get("Sell_CountI"),
        "sell_count_n":         rec.get("Sell_CountN"),
        "buy_vol_i":            buy_vol_i,
        "buy_vol_n":            rec.get("Buy_N_Volume"),
        "sell_vol_i":           sell_vol_i,
        "sell_vol_n":           rec.get("Sell_N_Volume"),
        # computed
        "buy_per_capita_i":     buy_vol_i  / buy_count_i  if buy_count_i  else None,
        "sell_per_capita_i":    sell_vol_i / sell_count_i if sell_count_i else None,
        "net_individual_flow":  buy_vol_i - sell_vol_i,
    }


def run_fund_live_scraper():
    db = SessionLocal()
    try:
        print("📡 دریافت داده از BrsApi...")
        try:
            all_funds = fetch_all_funds()
            print(f"  ✅ تعداد صندوق دریافتی: {len(all_funds)}")
        except Exception as e:
            print(f"  ❌ Fetch error: {e}")
            return

        inserted = skipped = errors = 0

        for name, ins_code in GOLD_FUNDS.items():
            print(f"\n📦 {name} | insCode: {ins_code}")

            fund = find_fund_by_id(all_funds, ins_code)
            if fund is None:
                print(f"  ⚠️  در پاسخ API پیدا نشد.")
                errors += 1
                continue

            try:
                parsed = parse_record(fund, ins_code)

                exists = db.query(FundLiveData).filter_by(
                    ins_code=parsed["ins_code"],
                    record_date=parsed["record_date"],
                ).first()

                if exists:
                    skipped += 1
                    print(f"  ⏭️  skipped (already exists for {parsed['record_date']})")
                    continue

                db.add(FundLiveData(**parsed))
                inserted += 1
                print(
                    f"  ✅ inserted | "
                    f"tno: {parsed['trade_count']:,} | "
                    f"tvol: {parsed['trade_volume']:,} | "
                    f"buy_i: {parsed['buy_vol_i']:,} | "
                    f"sell_i: {parsed['sell_vol_i']:,}"
                )

            except Exception as e:
                errors += 1
                print(f"  ❌ Error: {e}")

        db.commit()
        print(f"\n{'─' * 40}")
        print(f"✅ inserted: {inserted} | ⏭️  skipped: {skipped} | ❌ errors: {errors}")

    finally:
        db.close()


if __name__ == "__main__":
    run_fund_live_scraper()