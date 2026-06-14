from app.db import Base, engine
from app.scraper import run_scraper
from app.gold_price import save_xau_usd
from app.bubble import calculate_and_save_bubbles
from app.coin_price import save_coin_price

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