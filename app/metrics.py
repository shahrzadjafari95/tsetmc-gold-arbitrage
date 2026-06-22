"""
Calculated metrics for gold ETF analysis:
1. Bubble %          — nominal / real / intrinsic (from FundBubble)
2. Price Spread      — bubble % spread between fund pairs
3. Rolling Volatility — 5, 20, 60-day annualized std of daily returns
4. Correlation Matrix — between funds based on closing prices
5. Fund/Coin Ratio   — fund market price vs سکه امامی
6. Money Flow        — ورود/خروج پول حقیقی از FundLiveData
"""

import pandas as pd
from datetime import date, timedelta
from app.db import SessionLocal
from app.models import (
    ClosingPriceDaily,
    FundSnapshot,
    FundBubble,
    Fund,
    EmamiCoinPrice,
    FundLiveData,
    GoldPrice18K,
)


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def _code_to_name() -> dict[str, str]:
    db = SessionLocal()
    try:
        return {f.ins_code: f.name for f in db.query(Fund).all()}
    finally:
        db.close()


def _get_closing_prices(days: int = 90) -> pd.DataFrame:
    """Wide DataFrame: index=date, columns=fund_name, values=p_closing."""
    cutoff = date.today() - timedelta(days=days)
    db = SessionLocal()
    try:
        names = _code_to_name()
        rows = (
            db.query(ClosingPriceDaily)
            .filter(ClosingPriceDaily.record_date >= cutoff)
            .order_by(ClosingPriceDaily.record_date)
            .all()
        )
    finally:
        db.close()

    records = [
        {"date": r.record_date, "fund": names.get(r.ins_code, r.ins_code), "price": r.p_closing}
        for r in rows if r.p_closing
    ]
    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records).pivot(index="date", columns="fund", values="price")
    df.index = pd.to_datetime(df.index)
    return df


def _get_latest_emami_price() -> float | None:
    db = SessionLocal()
    try:
        row = db.query(EmamiCoinPrice).order_by(EmamiCoinPrice.record_date.desc()).first()
        return row.price if row else None
    finally:
        db.close()


def _get_latest_gold18k() -> dict | None:
    """Return latest GoldPrice18K record as dict."""
    db = SessionLocal()
    try:
        row = db.query(GoldPrice18K).order_by(GoldPrice18K.record_date.desc()).first()
        if not row:
            return None
        return {
            "date":         row.record_date,
            "xau_usd":      row.xau_usd,
            "usd_irr":      row.usd_irr,
            "gold_18k_irr": row.gold_18k_irr,
        }
    finally:
        db.close()


def _get_latest_closing() -> dict[str, float]:
    """Return {fund_name: p_closing} for the latest date per fund."""
    db = SessionLocal()
    try:
        names = _code_to_name()
        result = {}
        for ins_code, name in names.items():
            row = (
                db.query(ClosingPriceDaily)
                .filter_by(ins_code=ins_code)
                .order_by(ClosingPriceDaily.record_date.desc())
                .first()
            )
            if row and row.p_closing:
                result[name] = row.p_closing
        return result
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────
# 1. BUBBLE (خواندن از FundBubble که bubble_calc.py محاسبه کرده)
# ─────────────────────────────────────────────────────────────

def view_bubbles(target_date: date | None = None) -> pd.DataFrame:
    """
    خواندن حباب‌های محاسبه‌شده از DB.
    هر سه نوع حباب: اسمی / واقعی / ذاتی
    """
    target_date = target_date or date.today()
    db = SessionLocal()
    try:
        names = _code_to_name()
        rows = (
            db.query(FundBubble)
            .filter_by(record_date=target_date)
            .order_by(FundBubble.nominal_bubble_pct.desc())
            .all()
        )
        if not rows:
            print(f"⚠️  No bubble data for {target_date}")
            return pd.DataFrame()

        return pd.DataFrame([
            {
                "صندوق":        names.get(r.fund_ins_code, r.fund_ins_code),
                "قیمت بازار":   r.market_price,
                "NAV ابطال":    r.nav_red,
                "حباب اسمی %":  r.nominal_bubble_pct,   # (market - nav) / nav
                "حباب واقعی %": r.real_bubble_pct,       # (market - fair_emami) / fair_emami
                "حباب ذاتی %":  r.intrinsic_bubble_pct,  # (nav - gold_intrinsic) / gold_intrinsic
            }
            for r in rows
        ])
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────
# 2. PRICE SPREAD
# ─────────────────────────────────────────────────────────────

def calc_spread(target_date: date | None = None) -> pd.DataFrame:
    """
    Spread between funds = |bubble_a% - bubble_b%|
    بالاتر = فرصت آربیتراژ بیشتر
    """
    bubble_df = view_bubbles(target_date)
    if bubble_df.empty:
        return pd.DataFrame()

    funds = bubble_df.set_index("صندوق")["حباب اسمی %"].to_dict()
    fund_names = list(funds.keys())

    rows = []
    for i in range(len(fund_names)):
        for j in range(i + 1, len(fund_names)):
            a, b = fund_names[i], fund_names[j]
            rows.append({
                "صندوق الف":   a,
                "صندوق ب":     b,
                "حباب الف %":  round(funds[a], 4),
                "حباب ب %":    round(funds[b], 4),
                "اختلاف %":    round(abs(funds[a] - funds[b]), 4),
            })

    return pd.DataFrame(rows).sort_values("اختلاف %", ascending=False)


# ─────────────────────────────────────────────────────────────
# 3. ROLLING VOLATILITY
# ─────────────────────────────────────────────────────────────

def calc_rolling_volatility(days: int = 90) -> pd.DataFrame:
    """
    نوسان‌پذیری سالانه‌شده (annualized) — پنجره‌های ۵، ۲۰، ۶۰ روزه
    """
    prices = _get_closing_prices(days=max(days, 90))
    if prices.empty:
        return pd.DataFrame()

    returns = prices.pct_change().dropna()
    results = {}
    for window in [5, 20, 60]:
        vol = returns.rolling(window).std() * (252 ** 0.5) * 100
        results[f"vol_{window}d_%"] = vol.iloc[-1]

    df = pd.DataFrame(results).round(4)
    df.index.name = "صندوق"
    return df


# ─────────────────────────────────────────────────────────────
# 4. CORRELATION MATRIX
# ─────────────────────────────────────────────────────────────

def calc_correlation(days: int = 90) -> pd.DataFrame:
    """ماتریس همبستگی پیرسون بازده روزانه بین صندوق‌ها"""
    prices = _get_closing_prices(days=days)
    if prices.empty:
        return pd.DataFrame()

    return prices.pct_change().dropna().corr().round(4)


# ─────────────────────────────────────────────────────────────
# 5. FUND / EMAMI COIN RATIO
# ─────────────────────────────────────────────────────────────

def calc_fund_coin_ratio() -> pd.DataFrame:
    """نسبت قیمت صندوق به سکه امامی"""
    coin_price = _get_latest_emami_price()
    if not coin_price:
        print("⚠️  No Emami coin price in DB")
        return pd.DataFrame()

    prices = _get_latest_closing()
    rows = [
        {
            "صندوق":        name,
            "قیمت صندوق":  market_price,
            "قیمت سکه":    coin_price,
            "نسبت":         round(market_price / coin_price, 6),
        }
        for name, market_price in prices.items()
    ]
    return pd.DataFrame(rows).sort_values("نسبت", ascending=False)


# ─────────────────────────────────────────────────────────────
# 6. MONEY FLOW — ورود/خروج پول حقیقی
# ─────────────────────────────────────────────────────────────

def calc_money_flow(days: int = 30) -> pd.DataFrame:
    cutoff = date.today() - timedelta(days=days)
    db = SessionLocal()
    try:
        names = _code_to_name()
        rows = (
            db.query(FundLiveData)
            .filter(FundLiveData.record_date >= cutoff)
            .order_by(FundLiveData.record_date)
            .all()
        )
    finally:
        db.close()

    if not rows:
        print("⚠️  No FundLiveData in DB")
        return pd.DataFrame()

    return pd.DataFrame([
        {
            "تاریخ":           r.record_date,
            "صندوق":           names.get(r.ins_code, r.ins_code),
            "حجم خرید حقیقی":  r.buy_vol_i,
            "حجم فروش حقیقی":  r.sell_vol_i,
            "خرید حقوقی":      r.buy_vol_n,
            "فروش حقوقی":      r.sell_vol_n,
            "جریان پول حقیقی": r.net_individual_flow,
            "سرانه خرید":      r.buy_per_capita_i,
            "سرانه فروش":      r.sell_per_capita_i,
        }
        for r in rows
    ])


def calc_money_flow_summary(days: int = 30) -> pd.DataFrame:
    df = calc_money_flow(days=days)
    if df.empty:
        return pd.DataFrame()

    return (
        df.groupby("صندوق")
        .agg(
            جریان_کل=("جریان پول حقیقی", "sum"),
            خرید_کل=("حجم خرید حقیقی", "sum"),
            فروش_کل=("حجم فروش حقیقی", "sum"),
        )
        .sort_values("جریان_کل", ascending=False)
        .round(0)
    )
# ─────────────────────────────────────────────────────────────
# PRINT ALL METRICS
# ─────────────────────────────────────────────────────────────

def print_all_metrics():
    gold = _get_latest_gold18k()
    emami = _get_latest_emami_price()

    print("\n" + "═" * 70)
    print("💰 قیمت‌های پایه")
    print("═" * 70)
    if gold:
        print(f"  طلای جهانی  : ${gold['xau_usd']:,.2f} / oz")
        print(f"  نرخ دلار    : {gold['usd_irr']:,.0f} IRR")
        print(f"  طلای ۱۸ عیار: {gold['gold_18k_irr']:,.0f} IRR/gram | تاریخ: {gold['date']}")
    if emami:
        print(f"  سکه امامی   : {emami:,.0f} IRR")

    print("\n" + "═" * 70)
    print(f"📊 1. حباب صندوق‌های طلا — {date.today()}")
    print("═" * 70)
    df = view_bubbles()
    if not df.empty:
        df_print = df.copy()
        for col in ["قیمت بازار", "NAV ابطال"]:
            df_print[col] = df_print[col].apply(lambda x: f"{x:,.0f}")
        for col in ["حباب اسمی %", "حباب واقعی %", "حباب ذاتی %"]:
            df_print[col] = df_print[col].apply(lambda x: f"{x:+.2f}%")
        print(df_print.to_string(index=False))

    print("\n" + "═" * 70)
    print("📐 2. اختلاف حباب بین صندوق‌ها (فرصت آربیتراژ)")
    print("═" * 70)
    df = calc_spread()
    if not df.empty:
        print(df.head(10).to_string(index=False))

    print("\n" + "═" * 70)
    print("📈 3. نوسان‌پذیری سالانه — ۵/۲۰/۶۰ روزه")
    print("═" * 70)
    df = calc_rolling_volatility()
    if not df.empty:
        print(df.to_string())

    print("\n" + "═" * 70)
    print("🔗 4. ماتریس همبستگی بازده روزانه")
    print("═" * 70)
    df = calc_correlation()
    if not df.empty:
        print(df.to_string())

    print("\n" + "═" * 70)
    print("🪙 5. نسبت قیمت صندوق به سکه امامی")
    print("═" * 70)
    df = calc_fund_coin_ratio()
    if not df.empty:
        print(df.to_string(index=False))

    print("\n" + "═" * 70)
    print("💸 6. جریان پول حقیقی — ۳۰ روز اخیر (خلاصه)")
    print("═" * 70)
    df = calc_money_flow_summary(days=30)
    if not df.empty:
        df_print = df.copy()
        for col in df_print.columns:
            df_print[col] = df_print[col].apply(lambda x: f"{x:,.0f}")
        print(df_print.to_string())


if __name__ == "__main__":
    print_all_metrics()
