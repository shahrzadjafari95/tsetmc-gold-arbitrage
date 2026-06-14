from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.models import ClosingPriceDaily, Fund, FundSnapshot
from app.tsetmc import get_closing_price_history, get_etf_nav_today

# Hardcoded gold funds — insCode verified from TSETMC
GOLD_FUNDS = {
    "گوهر":  "12390706505809150",
    "زر":    "33254899395816171",
    "عیار":  "34144395039913458",
    "کهربا": "25559236668122210",
    "گلدیس":  "68376789401977331",
    "طلا":   "46700660505281786",
}


def _upsert_fund(db: Session, name: str, ins_code: str) -> None:
    existing = db.query(Fund).filter_by(ins_code=ins_code).first()
    if not existing:
        db.add(Fund(name=name, ins_code=ins_code))


def _save_nav_snapshot(db: Session, ins_code: str, item: dict) -> bool:
    exists = db.query(FundSnapshot).filter_by(
        fund_ins_code=ins_code,
        record_date=item["date"],
    ).first()
    if exists:
        return False
    db.add(FundSnapshot(
        fund_ins_code=ins_code,
        record_date=item["date"],
        nav_sub=item["nav_sub"],
        nav_red=item["nav_red"],
        nav_stat=item["nav_stat"],
        net_asset=item["net_asset"],
        units=item["units"],
    ))
    return True


def _save_closing_price(db: Session, ins_code: str, item: dict) -> bool:
    exists = db.query(ClosingPriceDaily).filter_by(
        ins_code=ins_code,
        record_date=item["date"],
    ).first()
    if exists:
        return False
    db.add(ClosingPriceDaily(
        ins_code=ins_code,
        record_date=item["date"],
        price_first=item.get("price_first"),
        price_min=item.get("price_min"),
        price_max=item.get("price_max"),
        price_last=item.get("price_last"),
        p_closing=item.get("p_closing"),
        q_tot_tran5j=item.get("q_tot_tran5j"),
        raw_data=item.get("raw", {}),
    ))
    return True


def _process_fund(db: Session, name: str, ins_code: str, days: int) -> None:
    print(f"\n📦 Processing: {name} | insCode: {ins_code}")

    _upsert_fund(db, name=name, ins_code=ins_code)

    # Today's NAV — non-fatal, some funds may not support ETF NAV endpoint
    try:
        nav = get_etf_nav_today(ins_code)
        if nav:
            inserted = _save_nav_snapshot(db, ins_code, nav)
            print(f"  ✅ NAV today: nav_red={nav['nav_red']} | nav_sub={nav['nav_sub']} | {'inserted' if inserted else 'already existed'}")
        else:
            print(f"  ⚠️ No NAV data returned")
    except Exception as e:
        print(f"  ⚠️ NAV skipped: {e}")  # non-fatal

    # Closing price history — fatal if fails
    try:
        cp_records = get_closing_price_history(ins_code, days=days)
        print(f"  📅 Closing price records: {len(cp_records)}")
        inserted = sum(_save_closing_price(db, ins_code, r) for r in cp_records)
        print(f"  ✅ Closing price inserted: {inserted} | skipped: {len(cp_records) - inserted}")
    except Exception as e:
        print(f"  ❌ Closing price fetch error: {e}")
        raise


def run_scraper(days: int = 365) -> None:
    print(f"Gold funds: {len(GOLD_FUNDS)}")

    for name, ins_code in GOLD_FUNDS.items():
        db = SessionLocal()
        try:
            _process_fund(db, name, ins_code, days)
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"  ❌ Rolled back changes for '{name}': {e}")
        finally:
            db.close()