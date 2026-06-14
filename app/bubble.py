from datetime import date
from app.db import SessionLocal
from app.models import FundSnapshot, ClosingPriceDaily, FundBubble, Fund
from sqlalchemy import func


def calculate_and_save_bubbles():
    db = SessionLocal()
    try:
        funds = db.query(Fund).all()
        saved = skipped = missed = 0

        for fund in funds:
            # Get latest NAV snapshot for this fund
            snapshot = db.query(FundSnapshot).filter_by(
                fund_ins_code=fund.ins_code,
            ).order_by(FundSnapshot.record_date.desc()).first()

            # Get latest closing price for this fund
            closing = db.query(ClosingPriceDaily).filter_by(
                ins_code=fund.ins_code,
            ).order_by(ClosingPriceDaily.record_date.desc()).first()

            if not snapshot or not closing:
                print(f"  ⚠️ [{fund.name}] Missing data: snapshot={snapshot is not None} closing={closing is not None}")
                missed += 1
                continue

            if not snapshot.nav_red or not closing.price_last:
                print(f"  ⚠️ [{fund.name}] Missing values: nav_red={snapshot.nav_red} price_last={closing.price_last}")
                missed += 1
                continue

            bubble_pct = (closing.price_last / snapshot.nav_red - 1) * 100
            target_date = closing.record_date

            exists = db.query(FundBubble).filter_by(
                fund_ins_code=fund.ins_code,
                record_date=target_date,
            ).first()

            if exists:
                exists.bubble_pct = bubble_pct
                skipped += 1
            else:
                db.add(FundBubble(
                    fund_ins_code=fund.ins_code,
                    fund_name=fund.name,
                    record_date=target_date,
                    nav_red=snapshot.nav_red,
                    price_last=closing.price_last,
                    bubble_pct=bubble_pct,
                ))
                saved += 1

            print(f"  📊 [{fund.name}] bubble={bubble_pct:.2f}% | nav_red={snapshot.nav_red} | price={closing.price_last} | date={target_date}")

        db.commit()
        print(f"\n[Bubble] Saved: {saved} | Updated: {skipped} | Missing data: {missed}")
    except Exception as e:
        db.rollback()
        print(f"[Bubble] ❌ Error: {e}")
    finally:
        db.close()