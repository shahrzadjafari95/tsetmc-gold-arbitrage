import requests
from datetime import datetime, date, timedelta

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://tsetmc.com",
    "Accept": "application/json",
}


def _get(url: str) -> dict:
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    return r.json()


def get_closing_price_history(ins_code: str, days: int = 365) -> list[dict]:
    url = f"https://cdn.tsetmc.com/api/ClosingPrice/GetClosingPriceDailyList/{ins_code}/0"
    data = _get(url)
    cutoff = date.today() - timedelta(days=days)

    result = []
    for rec in data.get("closingPriceDaily", []):
        date_str = str(rec.get("dEven", ""))
        if len(date_str) != 8:
            continue
        try:
            rec_date = datetime.strptime(date_str, "%Y%m%d").date()
        except ValueError:
            continue
        if rec_date < cutoff:
            continue
        result.append({
            "date":         rec_date,
            "price_first":  rec.get("priceFirst"),
            "price_min":    rec.get("priceMin"),
            "price_max":    rec.get("priceMax"),
            "price_last":   rec.get("pDrCotVal"),
            "p_closing":    rec.get("pClosing"),
            "q_tot_tran5j": rec.get("qTotTran5J"),
            "raw":          rec,
        })
    return result


def get_etf_nav_today(ins_code: str) -> dict | None:
    url = f"https://cdn.tsetmc.com/api/Fund/GetETFByInsCode/{ins_code}"
    data = _get(url)
    etf = data.get("etf")
    if not etf:
        return None
    try:
        rec_date = datetime.strptime(str(etf.get("deven", "")), "%Y%m%d").date()
    except ValueError:
        return None
    return {
        "date":     rec_date,
        "nav_sub":  etf.get("pSubTran"),
        "nav_red":  etf.get("pRedTran"),
        "nav_stat": None,
        "net_asset": None,
        "units":    None,
    }