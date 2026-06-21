# app/brsapi.py
import requests
from datetime import date
from app.db import SessionLocal
from app.models import FundLiveData
from app.gold_funds import GOLD_FUNDS
import json
import gzip


API_KEY  = "BE9KJxgJZkd2peD14HxrkWdfR9s8ZP8X"
API_URL  = "https://Api.BrsApi.ir/IME/Fund.php"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://brsapi.ir/",
    "Origin": "https://brsapi.ir",
    "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
}

# ins_code → fund name
_CODE_TO_NAME = {v: k for k, v in GOLD_FUNDS.items()}
_OUR_CODES    = set(GOLD_FUNDS.values())


# ─────────────────────────────────────────
# FETCH
# ─────────────────────────────────────────

import gzip

def _fetch() -> list[dict]:
    r = requests.get(
        API_URL,
        params={"key": API_KEY},
        headers=HEADERS,
        timeout=15,
    )
    r.raise_for_status()

    if not r.content:
        raise Exception("Empty response from BrsApi")

    # Decompress manually if gzip-encoded
    content = r.content
    if content[:2] == b'\x1f\x8b':  # gzip magic bytes
        content = gzip.decompress(content)

    try:
        data = json.loads(content.decode("utf-8"))
    except Exception as e:
        raise Exception(f"Failed to parse JSON: {e} | Raw: {content[:100]}")

    if not data.get("successful"):
        raise Exception(f"BrsApi error: {data.get('message_error')}")

    return data.get("data", [])
def _match_ins_code(api_id: str) -> str | None:
    """Match API id to our ins_code — exact first, then prefix fallback."""
    if api_id in _OUR_CODES:
        return api_id
    # last digit sometimes differs by 1
    return next((c for c in _OUR_CODES if c[:-1] == api_id[:-1]), None)


# ─────────────────────────────────────────
# COMPUTE
# ─────────────────────────────────────────

def _build_record(rec: dict, ins_code: str, today: date) -> dict:
    buy_vol_i   = rec.get("Buy_I_Volume") or 0
    sell_vol_i  = rec.get("Sell_I_Volume") or 0
    buy_count_i = rec.get("Buy_CountI") or 1
    sell_count_i= rec.get("Sell_CountI") or 1
    pc          = rec.get("pc") or 0

    return dict(
        ins_code        = ins_code,
        record_date     = today,
        record_time     = rec.get("time", ""),

        # قیمت‌ها
        p_closing       = pc,
        p_last          = rec.get("pl"),
        p_first         = rec.get("pf"),
        p_min           = rec.get("pmin"),
        p_max           = rec.get("pmax"),
        p_yesterday     = rec.get("py"),
        p_change        = rec.get("pcc"),
        p_change_pct    = rec.get("pcp"),

        # حجم و ارزش
        trade_count     = rec.get("tno"),
        trade_volume    = rec.get("tvol") or 0,
        trade_value     = rec.get("tval") or 0,

        # حقیقی / حقوقی
        buy_count_i     = rec.get("Buy_CountI"),
        buy_count_n     = rec.get("Buy_CountN"),
        sell_count_i    = rec.get("Sell_CountI"),
        sell_count_n    = rec.get("Sell_CountN"),
        buy_vol_i       = buy_vol_i,
        buy_vol_n       = rec.get("Buy_N_Volume"),
        sell_vol_i      = sell_vol_i,
        sell_vol_n      = rec.get("Sell_N_Volume"),

        # محاسبات
        buy_per_capita_i    = buy_vol_i  / buy_count_i  if buy_count_i  else None,
        sell_per_capita_i   = sell_vol_i / sell_count_i if sell_count_i else None,
        net_individual_flow = (buy_vol_i - sell_vol_i) * pc,
    )


# ─────────────────────────────────────────
# SAVE
# ─────────────────────────────────────────

def save_fund_live_data() -> None:
    today = date.today()
    db    = SessionLocal()

    try:
        raw_records = _fetch()
        print(f"  📡 API returned {len(raw_records)} funds")

        saved = updated = skipped = 0

        for rec in raw_records:
            api_id   = str(rec.get("id", "")).strip()
            ins_code = _match_ins_code(api_id)

            if not ins_code:
                skipped += 1
                continue

            name   = _CODE_TO_NAME.get(ins_code, ins_code)
            fields = _build_record(rec, ins_code, today)

            existing = db.query(FundLiveData).filter_by(
                ins_code=ins_code,
                record_date=today,
            ).first()

            if existing:
                for k, v in fields.items():
                    setattr(existing, k, v)
                updated += 1
                icon = "🔄"
            else:
                db.add(FundLiveData(**fields))
                saved += 1
                icon = "✅"

            net_b = fields["net_individual_flow"] / 1e9
            print(
                f"  {icon} {name}: "
                f"پایانی={fields['p_closing']:,} | "
                f"خرید حقیقی={fields['buy_vol_i']:,} | "
                f"فروش حقیقی={fields['sell_vol_i']:,} | "
                f"جریان={net_b:+.2f}B"
            )

        db.commit()
        print(f"\n  💾 Saved: {saved} | Updated: {updated} | Not matched: {skipped}")

    except Exception as e:
        db.rollback()
        print(f"  ❌ BrsApi error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    save_fund_live_data()