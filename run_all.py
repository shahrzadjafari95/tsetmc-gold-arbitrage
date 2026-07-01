import json

from app.brspi import save_today
from app.brspi_history import run_history_scraper
from app.db import Base, engine
from app.scraper import run_scraper
from app.emami_price import save_emami_price
from app.xauusd_tradingview import save_xauusd_tradingview
from app.bubble_calc import calc_and_save_bubbles
from app.transactions import run_transactions_scraper
from app.usdt_price_nobitex import save_usdt_price

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)

    print("=== 1. Fund NAV + closing prices (tsetmc) ===")
    run_scraper(days=365)

    print("\n=== 2. XAU/USD from TradingView ===")
    xau_payload = save_xauusd_tradingview()
    if xau_payload:
        print(json.dumps(xau_payload, ensure_ascii=False))

    print("\n=== 3. قیمت سکه امامی ===")
    save_emami_price()

    print("\n=== 4. حباب صندوق‌ها ===")
    calc_and_save_bubbles()

    print("\n=== 5. Live data امروز (BrsApi) ===")
    save_today()

    print("\n=== 6. تاریخچه حقیقی/حقوقی (BrsApi history) ===")
    run_history_scraper(days_back=365)

    print("\n=== 7. ریز معاملات ===")
    run_transactions_scraper(days=1)

    print("\n=== 8. قیمت تتر (USDT/IRT) — نوبیتکس ===")
    save_usdt_price()
