# TSETMC Gold Fund Scraper

A data pipeline that collects daily market data for Iranian gold ETFs, XAU/USD, and سکه بهار آزادی prices.

---

## Project Structure

```
tsetmc-scraper/
├── app/
│   ├── db.py              # Database connection (PostgreSQL)
│   ├── models.py          # SQLAlchemy table definitions
│   ├── scraper.py         # Fund NAV + closing price scraper
│   ├── tsetmc.py          # TSETMC API fetchers
│   ├── gold_price.py      # XAU/USD fetcher (Yahoo Finance)
│   ├── coin_price.py      # سکه بهار آزادی fetcher (tgju.org)
│   └── bubble.py          # Daily bubble % calculator
├── run_all.py             # Main entrypoint — runs everything
├── view_data.py           # Inspect what's saved in the DB
└── logs/                  # Scraper logs (created automatically)
```

---

## Prerequisites

**Python 3.13+** and **PostgreSQL** must be installed.

---

## Setup

### 1. Clone and create virtual environment

```bash
cd ~/Desktop
git clone <your-repo> tsetmc-scraper
cd tsetmc-scraper
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install sqlalchemy psycopg2-binary requests yfinance jdatetime
```

### 3. Create the PostgreSQL database

```bash
createdb market_data
```

Or if you need a specific user:

```bash
psql -c "CREATE DATABASE market_data;"
```

### 4. Configure the database URL

The default connection string in `app/db.py` is:

```
postgresql+psycopg2://<your-mac-username>@localhost:5432/market_data
```

Edit `app/db.py` if your username or DB name is different:

```python
DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://YOUR_USERNAME@localhost:5432/market_data",
)
```

---

## Running the Scraper

### First run — creates all tables and fetches 1 year of history

```bash
source .venv/bin/activate
python3 run_all.py
```

### What it does

| Step | Description |
|------|-------------|
| 1 | Fetches closing prices (1 year) + today's NAV for 6 gold funds |
| 2 | Fetches XAU/USD gold price history (1 year) via Yahoo Finance |
| 3 | Fetches today's سکه بهار آزادی price from tgju.org |
| 4 | Calculates bubble % for each fund = `(market_price / nav_red - 1) × 100` |

### Inspect saved data

```bash
python3 view_data.py
```

---

## Tracked Funds

| Name | insCode |
|------|---------|
| گوهر | 12390706505809150 |
| زر | 33254899395816171 |
| عیار | 34144395039913458 |
| کهربا | 25559236668122210 |
| طلا | 46700660505281786 |
| گلدیس | 68376789401977331 |

To add a new fund, add its `insCode` to `GOLD_FUNDS` in `app/scraper.py`.

---

## Database Tables

| Table | Description |
|-------|-------------|
| `funds` | Fund metadata (name, insCode) |
| `closing_price_daily` | Daily OHLC market prices per fund |
| `fund_snapshots` | Daily NAV (nav_red, nav_sub) per fund |
| `gold_prices` | XAU/USD daily price |
| `coin_prices` | سکه بهار آزادی daily price (IRR) |
| `fund_bubbles` | Daily bubble % per fund |

---

## Data Sources

| Data | Source | Endpoint |
|------|--------|----------|
| Closing prices | TSETMC | `cdn.tsetmc.com/api/ClosingPrice/GetClosingPriceDailyList` |
| ETF NAV (today) | TSETMC | `cdn.tsetmc.com/api/Fund/GetETFByInsCode` |
| XAU/USD | Yahoo Finance (yfinance) | Gold Futures `GC=F` |
| سکه بهار آزادی | tgju.org | `call4.tgju.org/ajax.json` → key: `sekee` |
