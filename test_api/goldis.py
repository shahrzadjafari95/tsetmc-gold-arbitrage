import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://tsetmc.com",
    "Accept": "application/json, text/plain, */*",
}

ins_code = "68376789401977331"  # گلدیس
url = f"https://cdn.tsetmc.com/api/ClosingPrice/GetClosingPriceDailyList/{ins_code}/0"

r = requests.get(url, headers=HEADERS, timeout=15)
r.raise_for_status()
data = r.json()

records = data.get("closingPriceDaily", [])
print("Top-level keys:", data.keys())
print("Number of records:", len(records))

if records:
    print("\nFields in each record:")
    for k, v in records[0].items():
        print(f"  {k}: {v}")