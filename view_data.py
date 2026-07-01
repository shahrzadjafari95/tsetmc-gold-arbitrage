import argparse
from datetime import date

from app.db import SessionLocal
from app.gold_funds import GOLD_FUNDS
from app.models import (
    ClosingPriceDaily,
    EmamiCoinPrice,
    Fund,
    FundBubble,
    FundLiveData,
    FundSnapshot,
    GoldPrice18K,
)


def _parse_args() -> date:
    parser = argparse.ArgumentParser(description="Inspect saved market data for a specific date.")
    parser.add_argument(
        "--date",
        dest="target_date",
        help="Target date in YYYY-MM-DD format. Defaults to today.",
    )
    args = parser.parse_args()
    if not args.target_date:
        return date.today()
    return date.fromisoformat(args.target_date)

target_date = _parse_args()
db = SessionLocal()
code_to_name = {f.ins_code: f.name for f in db.query(Fund).all()}

try:
    # ─────────────────────────────────────────
    # 1. قیمت‌های پایه برای تاریخ انتخابی
    # ─────────────────────────────────────────
    print("\n" + "═" * 60)
    print(f"💰 قیمت‌های پایه — {target_date}")
    print("═" * 60)

    gold = db.query(GoldPrice18K).filter_by(record_date=target_date).first()
    emami = db.query(EmamiCoinPrice).filter_by(record_date=target_date).first()

    if gold:
        print(f"  طلای جهانی   : ${gold.xau_usd:,.2f} / oz  | تاریخ: {gold.record_date}")
        print(f"  نرخ دلار     : {gold.usd_irr:,.0f} IRR")
        print(f"  طلای ۱۸ عیار : {gold.gold_18k_irr:,.0f} IRR/gram")
    else:
        print("  ⚠️  No gold price data")

    if emami:
        print(f"  سکه امامی    : {emami.price:,.0f} IRR  | تاریخ: {emami.record_date}")
    else:
        print("  ⚠️  No Emami price data")

    # ─────────────────────────────────────────
    # 2. حباب برای تاریخ انتخابی
    # ─────────────────────────────────────────
    print("\n" + "═" * 60)
    print(f"📊 حباب صندوق‌های طلا — {target_date}")
    print("═" * 60)

    bubbles = (
        db.query(FundBubble)
        .filter_by(record_date=target_date)
        .order_by(FundBubble.nominal_bubble_pct.desc())
        .all()
    )

    if not bubbles:
        print("  ⚠️  No bubble data for this date — run bubble_calc.py after saving today's prices and today's fund data")
    else:
        print(f"  {'صندوق':<15} {'قیمت بازار':>12} {'NAV ابطال':>12} {'اسمی':>8} {'واقعی':>8} {'ذاتی':>8}")
        print("  " + "─" * 68)
        for r in bubbles:
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
    # 3. Live data برای تاریخ انتخابی
    # ─────────────────────────────────────────
    print("\n" + "═" * 60)
    print(f"💸 Live Data — حقیقی/حقوقی | {target_date}")
    print("═" * 60)

    live_rows = (
        db.query(FundLiveData)
        .filter_by(record_date=target_date)
        .order_by(FundLiveData.net_individual_flow.desc())
        .all()
    )

    if not live_rows:
        print("  ⚠️  No live data for this date")
    else:
        print(f"  {'صندوق':<12} {'پایانی':>10} {'خ.حقیقی':>12} {'ف.حقیقی':>12} {'خ.حقوقی':>10} {'ف.حقوقی':>10} {'جریان(B)':>10}")
        print("  " + "─" * 80)
        for r in live_rows:
            name = code_to_name.get(r.ins_code, r.ins_code)
            flow_b = (r.net_individual_flow or 0) / 1e9
            print(
                f"  {name:<12} "
                f"{(r.p_closing or 0):>10,.0f} "
                f"{(r.buy_vol_i or 0):>12,.0f} "
                f"{(r.sell_vol_i or 0):>12,.0f} "
                f"{(r.buy_vol_n or 0):>10,.0f} "
                f"{(r.sell_vol_n or 0):>10,.0f} "
                f"{flow_b:>+10.2f}"
            )

    # ─────────────────────────────────────────
    # 4. تاریخچه حقیقی/حقوقی — آخرین رکورد تا تاریخ انتخابی
    # ─────────────────────────────────────────
    print("\n" + "═" * 60)
    print(f"📅 آخرین رکورد FundLiveData تا {target_date}")
    print("═" * 60)

    for name, ins_code in GOLD_FUNDS.items():
        r = (
            db.query(FundLiveData)
            .filter(FundLiveData.ins_code == ins_code)
            .filter(FundLiveData.record_date <= target_date)
            .order_by(FundLiveData.record_date.desc())
            .first()
        )
        if not r:
            continue
        flow_b = (r.net_individual_flow or 0) / 1e9
        print(
            f"  {name:<12} {r.record_date} | "
            f"پایانی={r.p_closing or 0:,.0f} | "
            f"خرید حقیقی={r.buy_vol_i or 0:,.0f} | "
            f"فروش حقیقی={r.sell_vol_i or 0:,.0f} | "
            f"خرید حقوقی={r.buy_vol_n or 0:,.0f} | "
            f"فروش حقوقی={r.sell_vol_n or 0:,.0f} | "
            f"جریان={flow_b:+.2f}B"
        )

    # ─────────────────────────────────────────
    # 5. NAV + closing price برای تاریخ انتخابی
    # ─────────────────────────────────────────
    print("\n" + "═" * 60)
    print(f"📈 NAV + قیمت پایانی — تا {target_date}")
    print("═" * 60)

    funds = db.query(Fund).all()
    for f in funds:
        snap = (
            db.query(FundSnapshot)
            .filter(FundSnapshot.fund_ins_code == f.ins_code, FundSnapshot.record_date == target_date)
            .first()
        )
        closing = (
            db.query(ClosingPriceDaily)
            .filter(ClosingPriceDaily.ins_code == f.ins_code, ClosingPriceDaily.record_date == target_date)
            .first()
        )
        if snap and closing:
            bubble = ((closing.p_closing - snap.nav_red) / snap.nav_red * 100) if snap.nav_red else 0
            print(
                f"  {f.name:<12} "
                f"NAV={snap.nav_red:>10,.0f} | "
                f"اخرین قیمت بازار={closing.p_closing:>10,.0f} | "
                f"حباب={bubble:>+6.2f}% | "
                f"تاریخ={closing.record_date}"
            )
        else:
            print(f"  {f.name:<12} ⚠️  No exact NAV/closing data for {target_date}")
finally:
    db.close()
