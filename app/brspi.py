# app/brsapi.py
import gzip
import json
import time
import requests
from datetime import date, timedelta
from app.db import SessionLocal
from app.models import FundLiveData
from app.gold_funds import GOLD_FUNDS

API_KEY = "BE9KJxgJZkd2peD14HxrkWdfR9s8ZP8X"
URL     = "https://Api.BrsApi.ir/IME/Fund.php"
HEADERS = {
    "User-Agent":     "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept":         "application/json, text/plain, */*",
    "Accept-Language":"en-US,en;q=0.9,fa;q=0.8",
    "Referer":        "https://brsapi.ir/",
    "Origin":         "https://brsapi.ir",
    "sec-ch-ua":          '"Chromium";v="124", "Google Chrome";v="124"',
    "sec-ch-ua-mobile":   "?0",
    "sec-ch-ua-platform": '"macOS"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
}

_CODE_TO_NAME = {v: k for k, v in GOLD_FUNDS.items()}
_OUR_CODES    = set(GOLD_FUNDS.values())


# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────

def _fetch(target_date: date | None = None) -> list[dict]:
    """Fetch fund data for a specific date or today if None."""
    params = {"key": API_KEY}
    if target_date:
        params["date"] = target_date.strftime("%Y%m%d")

    r = requests.get(URL, params=params, headers=HEADERS, timeout=15)
    r.raise_for_status()

    if not r.content:
        raise Exception("Empty response from BrsApi")

    content = r.content
    if content[:2] == b'\x1f\x8b':
        content = gzip.decompress(content)

    try:
        data = json.loads(content.decode("utf-8"))
    except Exception as e:
        raise Exception(f"Failed to parse JSON: {e} | Raw: {content[:100]}")

    if not data.get("successful"):
        raise Exception(f"BrsApi error: {data.get('message_error')}")

    return data.get("data", [])


def _find_fund(funds: list[dict], ins_code: str) -> dict | None:
    """Find fund record by ins_code — exact match only."""
    for f in funds:
        if str(f.get("id")) == str(ins_code):
            return f
    return None


def _parse(rec: dict, ins_code: str, record_date: date) -> dict:
    """Parse raw API record into DB-ready dict."""
    buy_vol_i    = rec.get("Buy_I_Volume") or 0
    sell_vol_i   = rec.get("Sell_I_Volume") or 0
    buy_count_i  = rec.get("Buy_CountI") or 1
    sell_count_i = rec.get("Sell_CountI") or 1
    pc           = rec.get("pc") or 0

    return dict(
        ins_code             = ins_code,
        record_date          = record_date,
        record_time          = rec.get("time", ""),
        # قیمت‌ها
        p_closing            = pc,
        p_last               = rec.get("pl"),
        p_first              = rec.get("pf"),
        p_min                = rec.get("pmin"),
        p_max                = rec.get("pmax"),
        p_yesterday          = rec.get("py"),
        p_change             = rec.get("pcc"),
        p_change_pct         = rec.get("pcp"),
        # حجم و ارزش
        trade_count          = rec.get("tno"),
        trade_volume         = rec.get("tvol") or 0,
        trade_value          = rec.get("tval") or 0,
        # حقیقی / حقوقی
        buy_count_i          = rec.get("Buy_CountI"),
        buy_count_n          = rec.get("Buy_CountN"),
        sell_count_i         = rec.get("Sell_CountI"),
        sell_count_n         = rec.get("Sell_CountN"),
        buy_vol_i            = buy_vol_i,
        buy_vol_n            = rec.get("Buy_N_Volume"),
        sell_vol_i           = sell_vol_i,
        sell_vol_n           = rec.get("Sell_N_Volume"),
        # محاسبات
        buy_per_capita_i     = buy_vol_i  / buy_count_i  if buy_count_i  else None,
        sell_per_capita_i    = sell_vol_i / sell_count_i if sell_count_i else None,
        net_individual_flow  = (buy_vol_i - sell_vol_i) * pc,
    )


def _save_day(db, all_funds: list[dict], record_date: date, update_existing: bool = True) -> tuple[int, int, int]:
    """Save one day's data. Returns (inserted, updated, errors)."""
    inserted = updated = errors = 0

    for name, ins_code in GOLD_FUNDS.items():
        fund = _find_fund(all_funds, ins_code)
        if fund is None:
            errors += 1
            continue

        try:
            fields = _parse(fund, ins_code, record_date)
            existing = db.query(FundLiveData).filter_by(
                ins_code=ins_code,
                record_date=record_date,
            ).first()

            if existing:
                if update_existing:
                    for k, v in fields.items():
                        setattr(existing, k, v)
                    updated += 1
                else:
                    updated += 1  # count as skipped
            else:
                db.add(FundLiveData(**fields))
                inserted += 1

        except Exception as e:
            print(f"  ❌ {name}: {e}")
            errors += 1

    return inserted, updated, errors


# ─────────────────────────────────────────
# PUBLIC: TODAY
# ─────────────────────────────────────────

def save_today() -> None:
    """Fetch and save today's live data."""
    today = date.today()
    db    = SessionLocal()
    try:
        print("📡 دریافت داده از BrsApi...")
        all_funds = _fetch()
        matched = sum(1 for _, ins_code in GOLD_FUNDS.items() if _find_fund(all_funds, ins_code))
        print(f"  ✅ {len(all_funds)} funds received from API")
        print(f"  ✅ {matched} tracked funds matched in API")

        inserted, updated, errors = _save_day(db, all_funds, today, update_existing=True)
        db.commit()

        # Print summary per fund
        for name, ins_code in GOLD_FUNDS.items():
            fund = _find_fund(all_funds, ins_code)
            if not fund:
                continue
            parsed = _parse(fund, ins_code, today)
            print(f"\n  🏷️  {name}")
            rows = [
                ("ins_code", "شناسه داخلی نماد", parsed["ins_code"]),
                ("record_date", "تاریخ", parsed["record_date"]),
                ("record_time", "زمان آخرین اطلاعات قیمت", parsed["record_time"]),
                ("p_last", "آخرین قیمت", parsed["p_last"] or 0),
                ("p_first", "اولین قیمت", parsed["p_first"] or 0),
                ("p_min", "کمترین قیمت", parsed["p_min"] or 0),
                ("p_max", "بیشترین قیمت", parsed["p_max"] or 0),
                ("trade_count", "تعداد معاملات", parsed["trade_count"] or 0),
                ("trade_volume", "حجم معاملات", parsed["trade_volume"] or 0),
                ("trade_value", "ارزش معاملات", parsed["trade_value"] or 0),
                ("buy_count_i", "تعداد خریدار حقیقی", parsed["buy_count_i"] or 0),
                ("buy_count_n", "تعداد خریدار حقوقی", parsed["buy_count_n"] or 0),
                ("sell_count_i", "تعداد فروشنده حقیقی", parsed["sell_count_i"] or 0),
                ("sell_count_n", "تعداد فروشنده حقوقی", parsed["sell_count_n"] or 0),
                ("buy_vol_i", "حجم خرید حقیقی", parsed["buy_vol_i"] or 0),
                ("buy_vol_n", "حجم خرید حقوقی", parsed["buy_vol_n"] or 0),
                ("sell_vol_i", "حجم فروش حقیقی", parsed["sell_vol_i"] or 0),
                ("sell_vol_n", "حجم فروش حقوقی", parsed["sell_vol_n"] or 0),
            ]

            for key, fa_label, value in rows:
                if isinstance(value, (int, float)):
                    value_text = f"{value:,}"
                else:
                    value_text = str(value)
                print(f"     {key:<13} | {fa_label:<28} | {value_text}")

        print(f"\n  💾 Saved: {inserted} | Updated: {updated} | Errors: {errors}")
        if matched < len(GOLD_FUNDS):
            missing = [name for name, ins_code in GOLD_FUNDS.items() if not _find_fund(all_funds, ins_code)]
            print(f"  ⚠️  Missing tracked funds: {', '.join(missing)}")

    except Exception as e:
        db.rollback()
        print(f"  ❌ BrsApi error: {e}")
        raise
    finally:
        db.close()


# ─────────────────────────────────────────
# PUBLIC: HISTORY
# ─────────────────────────────────────────

def _get_trading_days(start: date, end: date) -> list[date]:
    """Iranian market: Sat–Wed open, Thu–Fri closed."""
    days = []
    current = start
    while current <= end:
        if current.weekday() not in (3, 4):  # skip Thursday=3, Friday=4
            days.append(current)
        current += timedelta(days=1)
    return days


def save_history(days_back: int = 365) -> None:
    """Fetch and save historical data for past N days."""
    end_date     = date.today() - timedelta(days=1)
    start_date   = end_date - timedelta(days=days_back)
    trading_days = _get_trading_days(start_date, end_date)

    print(f"📅 Fetching {len(trading_days)} trading days: {start_date} → {end_date}")

    db = SessionLocal()
    total_inserted = total_skipped = total_errors = 0

    try:
        for i, target_date in enumerate(trading_days):
            print(f"\n[{i+1}/{len(trading_days)}] 📆 {target_date}", end="  ")

            # Skip if already fully saved
            existing_count = db.query(FundLiveData).filter_by(
                record_date=target_date
            ).count()
            if existing_count >= len(GOLD_FUNDS):
                print(f"⏭️  already complete ({existing_count} records)")
                total_skipped += existing_count
                continue

            try:
                all_funds = _fetch(target_date)
                if not all_funds:
                    print("⚠️  no data returned")
                    continue

                print(f"✅ {len(all_funds)} funds")
                inserted, skipped, errors = _save_day(
                    db, all_funds, target_date, update_existing=False
                )
                db.commit()

                total_inserted += inserted
                total_skipped  += skipped
                total_errors   += errors
                print(f"   💾 +{inserted} inserted | {skipped} skipped | {errors} errors")

                time.sleep(0.5)  # be polite to API

            except Exception as e:
                print(f"   ❌ {e}")
                total_errors += 1
                db.rollback()
                time.sleep(2)

    finally:
        db.close()

    print(f"\n{'═' * 50}")
    print(f"✅ Total inserted : {total_inserted:,}")
    print(f"⏭️  Total skipped  : {total_skipped:,}")
    print(f"❌ Total errors   : {total_errors:,}")


# ─────────────────────────────────────────
# ENTRY POINTS
# ─────────────────────────────────────────

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "history":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 365
        save_history(days_back=days)
    else:
        save_today()
