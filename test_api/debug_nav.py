# debug_nav3.py
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://tsetmc.com",
    "Accept": "application/json, text/plain, */*",
}

ins_code = "25559236668122210"  # کهربا

urls_to_try = [
    f"https://cdn.tsetmc.com/api/Fund/GetETFByInsCode/{ins_code}/0",
    f"https://cdn.tsetmc.com/api/Fund/GetETFListByInsCode/{ins_code}/0",
    f"https://cdn.tsetmc.com/api/Fund/GetETFHistory/{ins_code}/0",
    f"https://cdn.tsetmc.com/api/Fund/GetETFByInsCodeHistory/{ins_code}/0",
    f"https://cdn.tsetmc.com/api/Fund/GetFundHistory/{ins_code}/0",
    f"https://cdn.tsetmc.com/api/Fund/GetETFDailyList/{ins_code}/0",
    f"https://cdn.tsetmc.com/api/Fund/GetETFByInsCodeList/{ins_code}/0",
]

for url in urls_to_try:
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        content_type = r.headers.get("Content-Type", "")
        print(f"[{r.status_code}] {url}")
        if r.status_code == 200 and "json" in content_type:
            print(f"  ✅ JSON: {r.text[:400]}")
        print()
    except Exception as e:
        print(f"❌ {url} → {e}\n")