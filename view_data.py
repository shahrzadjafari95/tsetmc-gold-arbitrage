# view_data.py
from datetime import date
from app.db import SessionLocal
from app.models import ClosingPriceDaily, Fund, FundSnapshot, FundBubble, EmamiCoinPrice, GoldPrice18K

db = SessionLocal()

# ─────────────────────────────────────────
# 1. FUNDS
# ─────────────────────────────────────────
print("\n=== Funds ===")
funds = db.query(Fund).all()
code_to_name = {f.ins_code: f.name for f in funds}
for f in funds:
    print(f"  {f.name} | {f.ins_code}")

# ─────────────────────────────────────────
# 2. CLOSING PRICES (latest 3 per fund)
# ─────────────────────────────────────────
print("\n=== Closing Price (latest 3 per fund) ===")
for f in funds:
    rows = (
        db.query(ClosingPriceDaily)
        .filter_by(ins_code=f.ins_code)
        .order_by(ClosingPriceDaily.record_date.desc())
        .limit(3)
        .all()
    )
    for r in rows:
        raw = r.raw_data or {}
        print(
            f"  [{f.name}] {r.record_date} | "
            f"پایانی={r.p_closing:,.0f} | "
            f"اولیه={raw.get('priceFirst', '-')} | "
            f"بالا={raw.get('priceMax', '-')} | "
            f"پایین={raw.get('priceMin', '-')} | "
            f"دیروز={raw.get('priceYesterday', '-')} | "
            f"آخرین={r.price_last:,.0f}"
        )

# ─────────────────────────────────────────
# 3. NAV SNAPSHOTS (latest per fund)
# ─────────────────────────────────────────
print("\n=== NAV Snapshots (latest per fund) ===")
for f in funds:
    r = (
        db.query(FundSnapshot)
        .filter_by(fund_ins_code=f.ins_code)
        .order_by(FundSnapshot.record_date.desc())
        .first()
    )
    if r:
        print(f"  [{f.name}] {r.record_date} | nav_red={r.nav_red:,.0f} | nav_sub={r.nav_sub:,.0f}")

# ─────────────────────────────────────────
# 4. طلای ۱۸ عیار (latest 5)
# ─────────────────────────────────────────
print("\n=== طلای ۱۸ عیار (latest 5) ===")
for r in db.query(GoldPrice18K).order_by(GoldPrice18K.record_date.desc()).limit(5).all():
    print(
        f"  {r.record_date} | "
        f"XAU/USD={r.xau_usd:,.2f} | "
        f"دلار={r.usd_irr:,.0f} | "
        f"۱۸عیار/گرم={r.gold_18k_irr:,.0f}"
    )

# ─────────────────────────────────────────
# 5. BUBBLES (today)
# ─────────────────────────────────────────
print(f"\n=== Bubbles — {date.today()} ===")
rows = (
    db.query(FundBubble)
    .filter_by(record_date=date.today())
    .order_by(FundBubble.nominal_bubble_pct.desc())
    .all()
)
if not rows:
    print("  No bubble data for today — run run_all.py first")
else:
    print(f"  {'صندوق':<15} {'قیمت بازار':>12} {'NAV ابطال':>12} {'اسمی':>8} {'واقعی':>8} {'ذاتی':>8}")
    print("  " + "-" * 68)
    for r in rows:
        name = code_to_name.get(r.fund_ins_code, r.fund_ins_code)
        print(
            f"  {name:<15} "
            f"{r.market_price:>12,.0f} "
            f"{r.nav_red:>12,.0f} "
            f"{r.nominal_bubble_pct:>+7.2f}% "
            f"{r.real_bubble_pct:>+7.2f}% "
            f"{r.intrinsic_bubble_pct:>+7.2f}%"
        )

# ─────────────────────────────────────────
# 6. سکه امامی (latest 5)
# ─────────────────────────────────────────
print("\n=== سکه امامی (latest 5) ===")
for r in db.query(EmamiCoinPrice).order_by(EmamiCoinPrice.record_date.desc()).limit(5).all():
    print(f"  {r.record_date} | قیمت={r.price:,.0f} IRR")

db.close()