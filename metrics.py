"""
Calculated metrics for gold ETF analysis:
1. Bubble %          — (market_price - nav_red) / nav_red * 100
2. Price Spread      — difference between fund prices (normalized to NAV)
3. Rolling Volatility — 5, 20, 60-day rolling std of daily returns
4. Correlation Matrix — between funds based on closing prices
5. Fund/Coin Ratio   — fund market price vs سکه بهار آزادی
"""

import pandas as pd
from datetime import date, timedelta
from sqlalchemy import text
from app.db import SessionLocal, engine
from app.models import ClosingPriceDaily, FundSnapshot, CoinPrice, Fund


# -------------------------
# HELPERS
# -------------------------

def _get_closing_prices(days: int = 90) -> pd.DataFrame:
    """Return a wide DataFrame: index=date, columns=fund_name, values=p_closing."""
    cutoff = date.today() - timedelta(days=days)
    db = SessionLocal()
    try:
        funds = {f.ins_code: f.name for f in db.query(Fund).all()}
        rows = (
            db.query(ClosingPriceDaily)
            .filter(ClosingPriceDaily.record_date >= cutoff)
            .order_by(ClosingPriceDaily.record_date)
            .all()
        )
    finally:
        db.close()

    records = [
        {"date": r.record_date, "fund": funds.get(r.ins_code, r.ins_code), "price": r.p_closing}
        for r in rows if r.p_closing
    ]
    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records).pivot(index="date", columns="fund", values="price")
    df.index = pd.to_datetime(df.index)
    return df


def _get_latest_nav() -> dict:
    """Return {ins_code: nav_red} for the latest snapshot per fund."""
    db = SessionLocal()
    try:
        funds = db.query(Fund).all()
        result = {}
        for f in funds:
            snap = (
                db.query(FundSnapshot)
                .filter_by(fund_ins_code=f.ins_code)
                .order_by(FundSnapshot.record_date.desc())
                .first()
            )
            if snap and snap.nav_red:
                result[f.name] = snap.nav_red
        return result
    finally:
        db.close()


def _get_latest_closing() -> dict:
    """Return {fund_name: price_last} for the latest closing price per fund."""
    db = SessionLocal()
    try:
        funds = {f.ins_code: f.name for f in db.query(Fund).all()}
        result = {}
        for ins_code, name in funds.items():
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


def _get_latest_coin_price() -> float | None:
    """Return the latest سکه بهار آزادی price."""
    db = SessionLocal()
    try:
        row = db.query(CoinPrice).order_by(CoinPrice.record_date.desc()).first()
        return row.price if row else None
    finally:
        db.close()


# -------------------------
# 1. BUBBLE %
# -------------------------

def calc_bubble() -> pd.DataFrame:
    """
    Bubble % = (market_price - nav_red) / nav_red * 100
    Uses latest closing price vs latest NAV snapshot.
    """
    nav = _get_latest_nav()
    prices = _get_latest_closing()

    rows = []
    for name, market_price in prices.items():
        nav_red = nav.get(name)
        if nav_red:
            bubble = (market_price - nav_red) / nav_red * 100
            rows.append({
                "fund": name,
                "market_price": market_price,
                "nav_red": nav_red,
                "bubble_pct": round(bubble, 4),
            })

    df = pd.DataFrame(rows).sort_values("bubble_pct")
    return df


# -------------------------
# 2. PRICE SPREAD
# -------------------------

def calc_spread() -> pd.DataFrame:
    """
    Spread between funds = difference in bubble % between any two funds.
    Higher spread = more arbitrage opportunity.
    """
    bubble_df = calc_bubble()
    if bubble_df.empty:
        return pd.DataFrame()

    rows = []
    funds = bubble_df.set_index("fund")["bubble_pct"].to_dict()
    fund_names = list(funds.keys())

    for i in range(len(fund_names)):
        for j in range(i + 1, len(fund_names)):
            a, b = fund_names[i], fund_names[j]
            spread = abs(funds[a] - funds[b])
            rows.append({
                "fund_a": a,
                "fund_b": b,
                "bubble_a": round(funds[a], 4),
                "bubble_b": round(funds[b], 4),
                "spread_pct": round(spread, 4),
            })

    df = pd.DataFrame(rows).sort_values("spread_pct", ascending=False)
    return df


# -------------------------
# 3. ROLLING VOLATILITY
# -------------------------

def calc_rolling_volatility(days: int = 90) -> pd.DataFrame:
    """
    Rolling volatility = annualized std of daily log returns.
    Windows: 5, 20, 60 days.
    Returns the latest row (most recent values).
    """
    prices = _get_closing_prices(days=max(days, 90))
    if prices.empty:
        return pd.DataFrame()

    # Daily log returns
    returns = prices.pct_change().dropna()

    results = {}
    for window in [5, 20, 60]:
        vol = returns.rolling(window).std() * (252 ** 0.5) * 100  # annualized %
        results[f"vol_{window}d"] = vol.iloc[-1]

    df = pd.DataFrame(results).round(4)
    df.index.name = "fund"
    return df


# -------------------------
# 4. CORRELATION MATRIX
# -------------------------

def calc_correlation(days: int = 90) -> pd.DataFrame:
    """
    Pearson correlation matrix of daily returns between all funds.
    Range: -1 (inverse) to +1 (perfect correlation).
    """
    prices = _get_closing_prices(days=days)
    if prices.empty:
        return pd.DataFrame()

    returns = prices.pct_change().dropna()
    corr = returns.corr().round(4)
    return corr


# -------------------------
# 5. FUND / COIN RATIO
# -------------------------

def calc_fund_coin_ratio() -> pd.DataFrame:
    """
    Ratio of fund market price to سکه بهار آزادی price.
    Useful for comparing fund valuation relative to physical coin.
    """
    coin_price = _get_latest_coin_price()
    if not coin_price:
        return pd.DataFrame()

    prices = _get_latest_closing()

    rows = []
    for name, market_price in prices.items():
        ratio = market_price / coin_price
        rows.append({
            "fund": name,
            "market_price": market_price,
            "coin_price": coin_price,
            "fund_coin_ratio": round(ratio, 6),
        })

    df = pd.DataFrame(rows).sort_values("fund_coin_ratio", ascending=False)
    return df


# -------------------------
# PRINT ALL METRICS
# -------------------------

def print_all_metrics():
    print("\n" + "=" * 60)
    print("📊 1. BUBBLE % — (market - NAV) / NAV * 100")
    print("=" * 60)
    df = calc_bubble()
    print(df.to_string(index=False))

    print("\n" + "=" * 60)
    print("📐 2. PRICE SPREAD between funds")
    print("=" * 60)
    df = calc_spread()
    print(df.to_string(index=False))

    print("\n" + "=" * 60)
    print("📈 3. ROLLING VOLATILITY (annualized %) — 5/20/60 day")
    print("=" * 60)
    df = calc_rolling_volatility()
    print(df.to_string())

    print("\n" + "=" * 60)
    print("🔗 4. CORRELATION MATRIX (daily returns)")
    print("=" * 60)
    df = calc_correlation()
    print(df.to_string())

    print("\n" + "=" * 60)
    print("🪙 5. FUND / سکه RATIO")
    print("=" * 60)
    df = calc_fund_coin_ratio()
    print(df.to_string(index=False))


if __name__ == "__main__":
    print_all_metrics()