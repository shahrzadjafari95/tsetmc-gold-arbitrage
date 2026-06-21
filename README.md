# TSETMC Gold Funds Scraper

This project collects and stores market data for Iranian gold funds and related gold prices.

It currently:

- Fetches TSETMC closing price history for a curated list of gold funds
- Pulls today's ETF NAV data from TSETMC when available
- Stores daily prices and snapshots in PostgreSQL
- Calculates fund bubble metrics
- Collects additional live data such as gold 18K price, Emami coin price, live fund data, client type history, and transactions

## Project Layout

```text
tsetmc-scraper/
├── app/
│   ├── db.py
│   ├── models.py
│   ├── scraper.py
│   ├── tsetmc.py
│   ├── gold_funds.py
│   ├── bubble_calc.py
│   ├── gold18k_price.py
│   ├── emami_price.py
│   ├── brspi.py
│   ├── client_type_scraper.py
│   ├── transactions.py
│   └── config.py
├── main.py
├── run_all.py
├── view_data.py
└── test_api/
```

## Requirements

- Python 3.13+
- PostgreSQL

## Setup

### 1. Create a virtual environment

```bash
cd ~/Desktop/tsetmc-scraper
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Create the database

By default, the app connects to:

```text
postgresql+psycopg2://shahrzadjafari@localhost:5432/market_data
```

Create the database locally:

```bash
createdb market_data
```

Or set your own connection string with `DATABASE_URL`:

```bash
export DATABASE_URL="postgresql+psycopg2://USER:PASSWORD@localhost:5432/market_data"
```

## Running

### Initialize tables and run the main scraper

`main.py` creates the tables and runs the core scraper:

```bash
python3 main.py
```

### Run the full workflow

`run_all.py` runs the broader pipeline:

```bash
python3 run_all.py
```

It performs these steps:

1. Creates tables if needed
2. Fetches 365 days of fund NAV and closing prices from TSETMC
3. Saves gold 18K price
4. Saves Emami coin price
5. Calculates fund bubble metrics
6. Saves live fund data from BrsApi
7. Saves client type history from algotik
8. Saves recent transaction data

## Inspecting Data

Use `view_data.py` to print the latest stored records:

```bash
python3 view_data.py
```

## Tracked Gold Funds

The active gold funds are defined in [`app/gold_funds.py`](/Users/shahrzadjafari/Desktop/tsetmc-scraper/app/gold_funds.py).

Current funds:

| Name | insCode |
|------|---------|
| گوهر | 12390706505809150 |
| زر | 33254899395816171 |
| عیار | 34144395039913458 |
| کهربا | 25559236668122210 |
| طلا | 46700660505281786 |
| گلدیس | 68376789401977331 |
| آلتون | 28374437855144739 |
| درنا | 17248898258246807 |
| لیان | 6362118829011821 |
| ناب | 30582275818828857 |
| آتش | 56987424987755487 |
| قیراط | 6237807001018762 |
| زرگر | 16817885126368964 |
| زروان | 28255729477187163 |
| مثقال | 32469128621155736 |
| نفیس | 4626686276232042 |
| امرالد | 30895446582685604 |
| زرفام | 33144542989832366 |
| درخشان | 61805666737517582 |
| تابش | 9089296888187061 |
| ریتون | 14035144070182412 |
| جواهر | 38544104313215500 |
| زمرد | 64795751499397128 |
| گنج | 58514988269776425 |
| گلدا | 48968268685622891 |
| جام طلا | 35389487611786089 |
| میراث | 53633583359422860 |
| نگین فارس | 53514992320442853 |
| همیان | 50072269736641214 |
| رزگلد | 17244733069907210 |
| رز ترنج | 20244389840999638 |

## Database Tables

These are defined in [`app/models.py`](/Users/shahrzadjafari/Desktop/tsetmc-scraper/app/models.py):

| Table | Description |
|-------|-------------|
| `funds` | Fund metadata |
| `fund_snapshots` | Daily NAV snapshot per fund |
| `closing_price_daily` | Daily closing price history per fund |
| `fund_transactions` | Fund transaction rows |
| `fund_live_data` | Daily live snapshot from BrsApi |
| `client_type_daily` | Historical client type data |
| `emami_coin_prices` | Emami coin price history |
| `gold_prices_18k` | Gold 18K price history |
| `fund_bubbles` | Bubble metrics per fund per day |

## Notes

- If you change the database URL, `app/db.py` reads it from `DATABASE_URL`.
- Some scrapers are non-fatal and may skip data when a source does not return a response.
- `test_api/` contains small debug and source-specific scripts used during development.
