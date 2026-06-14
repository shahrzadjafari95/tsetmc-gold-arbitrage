import requests
import jdatetime
from datetime import datetime, timedelta

from app.db import SessionLocal, Base, engine
from app.models import ClosingPriceDaily, Fund

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://tsetmc.com",
    "Accept": "application/json, text/plain, */*",
}

FUNDS = {
    "گوهر": "12390706505809150",
    "زر": "33254899395816171",
    "عیار": "34144395039913458",
    "کهربا": "25559236668122210",
    "صباح": "41013876011050911",
    "طلا": "46700660505281786",
}


def _upsert_fund(db, name: str, ins_code: str) -> bool:
    existing = db.query(Fund).filter_by(ins_code=str(ins_code)).first()
    if existing:
        if existing.name != name:
            existing.name = name
        return False

    db.add(Fund(
        name=name,
        ins_code=str(ins_code),
    ))
    return True


def to_float(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def jalali_str_to_gregorian(date_str: str):
    y, m, d = int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8])
    return jdatetime.date(y, m, d).togregorian()


def save_closing_price_daily(ins_code: str, name: str, days: int = 365):
    url = f"https://cdn.tsetmc.com/api/ClosingPrice/GetClosingPriceDailyList/{ins_code}/0"
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    data = r.json()

    records = data.get("closingPriceDaily", [])
    print(f"[{name}] Total records from API: {len(records)}")

    cutoff = datetime.now().date() - timedelta(days=days)
    db = SessionLocal()
    try:
        saved = 0
        skipped = 0
        invalid = 0
        for rec in records:
            date_str = str(rec.get("dEven", ""))
            if len(date_str) != 8:
                continue

            try:
                rec_date = jalali_str_to_gregorian(date_str)
            except ValueError:
                invalid += 1
                continue

            if rec_date < cutoff:
                continue

            exists = db.query(ClosingPriceDaily).filter_by(
                ins_code=str(ins_code),
                record_date=rec_date,
            ).first()
            if exists:
                skipped += 1
                continue

            db.add(ClosingPriceDaily(
                ins_code=str(ins_code),
                record_date=rec_date,
                price_first=to_float(rec.get("priceFirst")),
                price_min=to_float(rec.get("priceMin")),
                price_max=to_float(rec.get("priceMax")),
                price_last=to_float(rec.get("priceLast")),
                p_closing=to_float(rec.get("pClosing")),
                q_tot_tran5j=to_float(rec.get("qTotTran5J")),
                raw_data=rec,
            ))
            saved += 1

        db.commit()
        print(f"[{name}] Saved: {saved} | Skipped (already existed): {skipped} | Invalid dates: {invalid}")
    except Exception as e:
        db.rollback()
        print(f"[{name}] ❌ Error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)

    for name, ins_code in FUNDS.items():
        db = SessionLocal()
        try:
            inserted = _upsert_fund(db, name=name, ins_code=ins_code)
            db.commit()
            print(f"[{name}] Fund {'inserted' if inserted else 'already existed'}")
        except Exception as e:
            db.rollback()
            print(f"[{name}] ❌ Fund save error: {e}")
        finally:
            db.close()

        save_closing_price_daily(ins_code, name, days=365)
