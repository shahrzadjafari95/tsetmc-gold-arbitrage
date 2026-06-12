from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import ClosingPriceDaily, Fund, FundSnapshot
from app.tsetmc import get_closing_price_history, get_fund_nav_history, get_funds

GOLD_FUND_KEYWORDS = [
    "طلا", "زر", "درنا", "گلد", "مثقال",
    "عیار", "گنج", "زمرد", "نفیس", "رزگلد", "مفید",
]


def is_gold_fund(name: str) -> bool:
    return bool(name) and any(k in name for k in GOLD_FUND_KEYWORDS)


# -------------------------
# UPSERT HELPERS
# -------------------------

def _upsert_fund(db: Session, name: str, ins_code: str, reg_no) -> None:
    """Insert fund metadata if it doesn't already exist."""
    existing = db.query(Fund).filter_by(ins_code=ins_code).first()
    if not existing:
        db.add(Fund(
            name=name,
            ins_code=ins_code,
            reg_no=int(reg_no) if reg_no else None,
        ))


def _save_nav_snapshot(db: Session, ins_code: str, reg_no, item: dict) -> bool:
    """
    Insert a FundSnapshot row for one NAV record.
    Returns True if inserted, False if it already existed.
    """
    exists = db.query(FundSnapshot).filter_by(
        fund_ins_code=ins_code,
        record_date=item["date"],
    ).first()
    if exists:
        return False

    db.add(FundSnapshot(
        fund_ins_code=ins_code,
        reg_no=int(reg_no) if reg_no else None,
        record_date=item["date"],
        nav_sub=item["nav_sub"],
        nav_red=item["nav_red"],
        nav_stat=item["nav_stat"],
        net_asset=item["net_asset"],
        units=item["units"],
    ))
    return True


def _save_closing_price(db: Session, ins_code: str, item: dict) -> bool:
    """
    Insert a ClosingPriceDaily row for one record.
    Returns True if inserted, False if it already existed.
    """
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


# -------------------------
# MAIN SCRAPER
# -------------------------

def _process_fund(db: Session, fund: dict, days: int) -> None:
    """Process a single fund: upsert metadata, save NAV + closing price history."""
    name = fund.get("mfName", "")
    ins_code = fund.get("insCode")
    reg_no = fund.get("regNo")

    if not ins_code:
        print(f"  ⚠️  No insCode for '{name}', skipping")
        return

    ins_code = str(ins_code)
    print(f"\n📦 Processing: {name} | insCode: {ins_code}")

    # --- Fund metadata ---
    _upsert_fund(db, name=name, ins_code=ins_code, reg_no=reg_no)

    # --- NAV history ---
    try:
        nav_records = get_fund_nav_history(ins_code, days=days)
        print(f"  📅 NAV records: {len(nav_records)}")
        inserted = sum(_save_nav_snapshot(db, ins_code, reg_no, r) for r in nav_records)
        print(f"  ✅ NAV inserted: {inserted} | skipped: {len(nav_records) - inserted}")
    except Exception as e:
        print(f"  ❌ NAV fetch error: {e}")
        raise  # bubble up so the outer try/except can rollback

    # --- Closing price history ---
    try:
        cp_records = get_closing_price_history(ins_code, days=days)
        print(f"  📅 Closing price records: {len(cp_records)}")
        inserted = sum(_save_closing_price(db, ins_code, r) for r in cp_records)
        print(f"  ✅ Closing price inserted: {inserted} | skipped: {len(cp_records) - inserted}")
    except Exception as e:
        print(f"  ❌ Closing price fetch error: {e}")
        raise  # bubble up so the outer try/except can rollback


def run_scraper(days: int = 7) -> None:
    data = get_funds()
    funds = data.get("funds", [])
    gold_funds = [f for f in funds if is_gold_fund(f.get("mfName", ""))]

    print(f"Total funds: {len(funds)}")
    print(f"Gold funds found: {len(gold_funds)}")

    for fund in gold_funds:
        db = SessionLocal()
        try:
            _process_fund(db, fund, days)
            db.commit()
        except Exception as e:
            db.rollback()
            name = fund.get("mfName", "unknown")
            print(f"  ❌ Rolled back changes for '{name}': {e}")
        finally:
            db.close()