from datetime import datetime, timedelta
import jdatetime
import requests

FUNDS_URL = "https://cdn.tsetmc.com/api/Fund/GetFunds/6"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://tsetmc.com",
}


def get_funds() -> dict:
    """Fetch all funds from TSETMC."""
    r = requests.get(FUNDS_URL, headers=HEADERS, timeout=10)
    r.raise_for_status()
    return r.json()


def get_fund_nav_history(ins_code: str, days: int = 7) -> list[dict]:
    """
    Fetch NAV history for a fund using its insCode.
    Returns a list of daily NAV records filtered to the last `days` days.
    """
    url = f"https://cdn.tsetmc.com/api/Fund/GetFundNetAsset/{ins_code}/0"  # 0 not 1
    r = requests.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()
    data = r.json()

    records = data.get("fundNetAsset", [])
    cutoff = datetime.now().date() - timedelta(days=days)

    filtered = []
    for rec in records:
        try:
            date_str = str(rec.get("dEven", ""))
            if len(date_str) != 8:
                continue
            rec_date = datetime.strptime(date_str, "%Y%m%d").date()
            if rec_date < cutoff:
                continue
            filtered.append({
                "date": rec_date,
                "nav_sub": rec.get("navSubscription"),
                "nav_red": rec.get("navRedemption"),
                "nav_stat": rec.get("nav"),
                "net_asset": rec.get("totalNetAssets"),
                "units": rec.get("unitsOutstanding"),
                "raw": rec,
            })
        except Exception as e:
            print(f"  ⚠️ Date parse error: {e}")

    return filtered

def get_closing_price_history(ins_code: str, days: int = 365) -> list[dict]:
    url = f"https://cdn.tsetmc.com/api/ClosingPrice/GetClosingPriceDailyList/{ins_code}/0"
    r = requests.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()
    data = r.json()

    records = data.get("closingPriceDaily", [])
    cutoff = datetime.now().date() - timedelta(days=days)

    filtered = []
    for rec in records:
        try:
            date_str = str(rec.get("dEven", ""))
            if len(date_str) != 8:
                continue
            rec_date = datetime.strptime(date_str, "%Y%m%d").date()  # already Gregorian
            if rec_date < cutoff:
                continue
            filtered.append({
                "date": rec_date,
                "price_first": rec.get("priceFirst"),
                "price_min": rec.get("priceMin"),
                "price_max": rec.get("priceMax"),
                "price_last": rec.get("pDrCotVal"),
                "p_closing": rec.get("pClosing"),
                "q_tot_tran5j": rec.get("qTotTran5J"),
                "raw": rec,
            })
        except Exception as e:
            print(f"  ⚠️ Closing price parse error: {e}")

    return filtered

# سکه بهار آزادی insCode
COIN_INS_CODE = "67180011968026994"

def get_coin_price_history(days: int = 365) -> list[dict]:
    """قیمت سکه بهار آزادی از TSETMC"""
    url = f"https://cdn.tsetmc.com/api/ClosingPrice/GetClosingPriceDailyList/{COIN_INS_CODE}/0"
    r = requests.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()
    data = r.json()

    records = data.get("closingPriceDaily", [])
    cutoff = datetime.now().date() - timedelta(days=days)

    filtered = []
    for rec in records:
        try:
            date_str = str(rec.get("dEven", ""))
            if len(date_str) != 8:
                continue
            rec_date = datetime.strptime(date_str, "%Y%m%d").date()
            if rec_date < cutoff:
                continue
            filtered.append({
                "date": rec_date,
                "price": rec.get("pClosing"),
                "raw": rec,
            })
        except Exception:
            continue

    return filtered


def get_etf_nav_today(ins_code: str) -> dict | None:
    """Fetch today's NAV for an ETF using GetETFByInsCode."""
    url = f"https://cdn.tsetmc.com/api/Fund/GetETFByInsCode/{ins_code}"
    r = requests.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()
    data = r.json()
    etf = data.get("etf")
    if not etf:
        return None

    date_str = str(etf.get("deven", ""))
    try:
        rec_date = datetime.strptime(date_str, "%Y%m%d").date()
    except ValueError:
        return None

    return {
        "date": rec_date,
        "nav_sub": etf.get("pSubTran"),
        "nav_red": etf.get("pRedTran"),
        "nav_stat": None,
        "net_asset": None,
        "units": None,
    }