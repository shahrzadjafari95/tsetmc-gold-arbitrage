from app.db import SessionLocal
from app.models import ClosingPriceDaily, Fund, FundSnapshot, GoldPrice, FundBubble
from app.models import ClosingPriceDaily
from app.models import CoinPrice

db = SessionLocal()

r = db.query(ClosingPriceDaily).first()
if r:
    print("\nRaw data fields:", list(r.raw_data.keys()))

print("\n=== Funds ===")
for f in db.query(Fund).all():
    print(f"  {f.name} | {f.ins_code}")

print("\n=== Closing Price (latest 3 per fund) ===")
from sqlalchemy import func
funds = db.query(Fund).all()
for f in funds:
    rows = db.query(ClosingPriceDaily).filter_by(ins_code=f.ins_code)\
             .order_by(ClosingPriceDaily.record_date.desc()).limit(3).all()
    for r in rows:
        print(f"  [{f.name}] {r.record_date} | price_last={r.price_last} | p_closing={r.p_closing}")

print("\n=== NAV Snapshots (latest per fund) ===")
for f in funds:
    r = db.query(FundSnapshot).filter_by(fund_ins_code=f.ins_code)\
          .order_by(FundSnapshot.record_date.desc()).first()
    if r:
        print(f"  [{f.name}] {r.record_date} | nav_red={r.nav_red} | nav_sub={r.nav_sub}")

print("\n=== XAU/USD (latest 5) ===")
for r in db.query(GoldPrice).order_by(GoldPrice.record_date.desc()).limit(5).all():
    print(f"  {r.record_date} | {r.xau_usd}")

print("\n=== Bubbles ===")
for r in db.query(FundBubble).order_by(FundBubble.record_date.desc()).all():
    print(f"  [{r.fund_name}] {r.record_date} | bubble={r.bubble_pct:.2f}%")


print("\n=== سکه بهار آزادی (latest 5) ===")
for r in db.query(CoinPrice).order_by(CoinPrice.record_date.desc()).limit(5).all():
    print(f"  {r.record_date} | price={r.price:,.0f} | high={r.price_high:,.0f} | low={r.price_low:,.0f}")

db.close()