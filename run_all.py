from app.db import Base, engine
from app.scraper import run_scraper
from app.gold_price import save_xau_usd, get_xau_usd_latest_from_db, get_xau_usd_now
from app.bubble import calculate_and_save_bubbles
from app.coin_price import save_coin_price
from app.transactions import run_transactions_scraper


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)

    print("=== 1. Scraping fund NAV + closing prices ===")
    run_scraper(days=365)

    print("\n=== 2. Fetching XAU/USD ===")
    save_xau_usd(days=365)

    print("\n=== 3. سکه بهار آزادی ===")
    save_coin_price()

    print("\n=== 4. Calculating bubbles ===")
    calculate_and_save_bubbles()


    
    print("\n=== 5. Live price right now ===")
    print(get_xau_usd_now()) 

    # Latest saved in DB
    print("\n=== 6. Latest saved in DB ===")
    row = get_xau_usd_latest_from_db()
    print(f"{row['date'].strftime('%Y-%m-%d')} | {row['xau_usd']}")

    # add at the end:
    print("\n=== 5. Fetching fund transactions ===")
    run_transactions_scraper(days=1)