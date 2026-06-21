from app.brspi import save_fund_live_data
from app.client_type_scraper import run_fund_live_scraper
from app.db import Base, engine
from app.scraper import run_scraper
from app.emami_price import save_emami_price
from app.gold18k_price import save_gold_18k_price
from app.bubble_calc import calc_and_save_bubbles
from app.transactions import run_transactions_scraper

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)

    print("=== 1. Fund NAV + closing prices (tsetmc) ===")
    run_scraper(days=365)

    print("\n=== 2. قیمت طلای ۱۸ عیار ===")
    save_gold_18k_price()

    print("\n=== 3. قیمت سکه امامی ===")
    save_emami_price()

    print("\n=== 4. حباب صندوق‌ها ===")
    calc_and_save_bubbles()

    print("\n=== 5. Live data امروز (BrsApi) ===")
    save_fund_live_data()

    print("\n=== 6. تاریخچه حقیقی/حقوقی (algotik) ===")
    run_fund_live_scraper()

    print("\n=== 7. ریز معاملات ===")
    run_transactions_scraper(days=1)