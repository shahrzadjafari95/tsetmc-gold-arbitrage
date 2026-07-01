# app/nobitex.py
"""
قیمت تتر (USDT/IRT) از API عمومی نوبیتکس
endpoint: https://apiv2.nobitex.ir/v3/orderbook/USDTIRT
"""
import requests
from datetime import datetime, date, timezone
from dataclasses import dataclass, field
from app.db import SessionLocal
from app.models import UsdtPrice

API_URL = "https://apiv2.nobitex.ir/v3/orderbook/USDTIRT"
SYMBOL  = "USDTIRT"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept":     "application/json",
}


@dataclass
class OrderBookSnapshot:
    symbol:          str
    last_price:      float
    best_bid:        float
    best_ask:        float
    bid_volume:      float
    ask_volume:      float
    spread:          float
    spread_pct:      float
    fetched_at:      datetime
    api_last_update: float
    top_bids:        list = field(default_factory=list)
    top_asks:        list = field(default_factory=list)


def fetch(depth: int = 5) -> OrderBookSnapshot:
    r = requests.get(API_URL, headers=HEADERS, timeout=10)
    r.raise_for_status()
    data = r.json()

    if data.get("status") != "ok":
        raise ValueError(f"Nobitex API error: {data}")

    fetched_at = datetime.now(timezone.utc)
    last_price = float(data["lastTradePrice"])

    raw_bids = data.get("bids", [])
    raw_asks = data.get("asks", [])

    if not raw_bids or not raw_asks:
        raise ValueError("Empty orderbook")

    top_bids = [(float(b[0]), float(b[1])) for b in raw_bids[:depth]]
    top_asks = [(float(a[0]), float(a[1])) for a in raw_asks[:depth]]

    best_bid   = top_bids[0][0]
    bid_volume = top_bids[0][1]
    best_ask   = top_asks[0][0]
    ask_volume = top_asks[0][1]
    spread     = best_ask - best_bid
    spread_pct = round((spread / best_ask * 100) if best_ask else 0, 6)

    return OrderBookSnapshot(
        symbol          = SYMBOL,
        last_price      = last_price,
        best_bid        = best_bid,
        best_ask        = best_ask,
        bid_volume      = bid_volume,
        ask_volume      = ask_volume,
        spread          = spread,
        spread_pct      = spread_pct,
        fetched_at      = fetched_at,
        api_last_update = float(data.get("lastUpdate", 0)),
        top_bids        = top_bids,
        top_asks        = top_asks,
    )

def save_usdt_price() -> None:
    print("📡 دریافت قیمت تتر از نوبیتکس...")
    try:
        snap = fetch(depth=5)
    except Exception as e:
        print(f"  ❌ Fetch error: {e}")
        return

    toman = snap.last_price / 10
    best_bid_t = snap.best_bid / 10
    best_ask_t = snap.best_ask / 10
    spread_t   = snap.spread / 10

    print(f"  💵 USDT/IRT")
    print(f"     last price : {snap.last_price:>15,.0f} IRT  ({toman:>12,.0f} تومان)")
    print(f"     best bid   : {snap.best_bid:>15,.0f} IRT  ({best_bid_t:>12,.0f} تومان)  vol: {snap.bid_volume}")
    print(f"     best ask   : {snap.best_ask:>15,.0f} IRT  ({best_ask_t:>12,.0f} تومان)  vol: {snap.ask_volume}")
    print(f"     spread     : {snap.spread:>15,.0f} IRT  ({spread_t:>12,.0f} تومان)  ({snap.spread_pct:.4f}%)")
    print(f"     fetched_at : {snap.fetched_at.isoformat()}")

    print(f"\n     {'─' * 64}")
    print(f"     {'Ask (فروش)':^31} | {'Bid (خرید)':^31}")
    print(f"     {'IRT':>12}  {'Toman':>10}  {'Vol':>6}  | {'IRT':>12}  {'Toman':>10}  {'Vol':<6}")
    print(f"     {'─' * 64}")

    rows = max(len(snap.top_asks), len(snap.top_bids))
    for i in range(rows):
        if i < len(snap.top_asks):
            ap, av = snap.top_asks[i]
            ask_str = f"{ap:>12,.0f}  {ap/10:>10,.0f}  {av:>6.2f}"
        else:
            ask_str = f"{'':>12}  {'':>10}  {'':>6}"

        if i < len(snap.top_bids):
            bp, bv = snap.top_bids[i]
            bid_str = f"{bp:>12,.0f}  {bp/10:>10,.0f}  {bv:<6.2f}"
        else:
            bid_str = f"{'':>12}  {'':>10}  {'':6}"

        print(f"     {ask_str}  | {bid_str}")

    print(f"     {'─' * 64}")

    db = SessionLocal()
    try:
        db.add(UsdtPrice(
            symbol          = snap.symbol,
            record_date     = snap.fetched_at.date(),
            record_time     = snap.fetched_at.strftime("%H:%M:%S"),
            last_price      = snap.last_price,
            best_bid        = snap.best_bid,
            best_ask        = snap.best_ask,
            bid_volume      = snap.bid_volume,
            ask_volume      = snap.ask_volume,
            spread          = snap.spread,
            spread_pct      = snap.spread_pct,
            fetched_at      = snap.fetched_at.replace(tzinfo=None),
            api_last_update = snap.api_last_update,
        ))
        db.commit()
        print(f"\n  ✅ ذخیره شد | {snap.fetched_at.date()} {snap.fetched_at.strftime('%H:%M:%S')}")
    except Exception as e:
        db.rollback()
        print(f"  ❌ DB error: {e}")
        raise
    finally:
        db.close()
def get_latest_usdt_price() -> dict | None:
    """آخرین قیمت ذخیره‌شده از DB"""
    db = SessionLocal()
    try:
        row = db.query(UsdtPrice).order_by(
            UsdtPrice.record_date.desc(),
            UsdtPrice.record_time.desc(),
        ).first()
        if not row:
            return None
        return {
            "symbol":     row.symbol,
            "last_price": row.last_price,
            "best_bid":   row.best_bid,
            "best_ask":   row.best_ask,
            "spread":     row.spread,
            "spread_pct": row.spread_pct,
            "fetched_at": row.fetched_at,
        }
    finally:
        db.close()


if __name__ == "__main__":
    save_usdt_price()