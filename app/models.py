import datetime
from sqlalchemy import BigInteger, Column, Date, DateTime, Float, Integer, JSON, String, UniqueConstraint
from app.db import Base


def _utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


class Fund(Base):
    __tablename__ = "funds"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    ins_code = Column(String, unique=True, index=True, nullable=False)
    reg_no = Column(BigInteger, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class FundSnapshot(Base):
    __tablename__ = "fund_snapshots"
    __table_args__ = (UniqueConstraint("fund_ins_code", "record_date", name="uq_snapshot_fund_date"),)
    id = Column(Integer, primary_key=True)
    fund_ins_code = Column(String, index=True, nullable=False)
    reg_no = Column(BigInteger, index=True)
    record_date = Column(Date, index=True, nullable=False)
    nav_sub = Column(Float)
    nav_red = Column(Float)
    nav_stat = Column(Float)
    net_asset = Column(Float)
    units = Column(Float)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class ClosingPriceDaily(Base):
    __tablename__ = "closing_price_daily"
    __table_args__ = (UniqueConstraint("ins_code", "record_date", name="uq_closing_ins_date"),)
    id = Column(Integer, primary_key=True)
    ins_code = Column(String, index=True, nullable=False)
    record_date = Column(Date, index=True, nullable=False)
    price_first = Column(Float)
    price_min = Column(Float)
    price_max = Column(Float)
    price_last = Column(Float)
    p_closing = Column(Float)
    q_tot_tran5j = Column(Float)
    raw_data = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class FundTransaction(Base):
    __tablename__ = "fund_transactions"
    __table_args__ = (UniqueConstraint("fund_name", "record_date", "row", name="uq_transaction_fund_date_row"),)
    id = Column(Integer, primary_key=True)
    fund_name = Column(String, index=True, nullable=False)
    record_date = Column(Date, index=True, nullable=False)
    row = Column(Integer, nullable=False)
    time = Column(String)
    volume = Column(Float)
    price = Column(Float)
    canceled = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class FundLiveData(Base):
    """snapshot روزانه از BrsApi — قیمت + حجم + حقیقی/حقوقی"""
    __tablename__ = "fund_live_data"
    __table_args__ = (UniqueConstraint("ins_code", "record_date", name="uq_live_ins_date"),)

    id = Column(Integer, primary_key=True)
    ins_code = Column(String, index=True, nullable=False)
    record_date = Column(Date, index=True, nullable=False)
    record_time = Column(String)

    # قیمت‌ها
    p_closing = Column(Float)
    p_last = Column(Float)
    p_first = Column(Float)
    p_min = Column(Float)
    p_max = Column(Float)
    p_yesterday = Column(Float)
    p_change = Column(Float)
    p_change_pct = Column(Float)

    # حجم و تعداد معاملات
    trade_count = Column(Integer)
    trade_volume = Column(BigInteger)
    trade_value = Column(Float)

    # حقیقی / حقوقی — تعداد و حجم
    buy_count_i = Column(Integer)
    buy_count_n = Column(Integer)
    sell_count_i = Column(Integer)
    sell_count_n = Column(Integer)
    buy_vol_i = Column(Float)
    buy_vol_n = Column(Float)
    sell_vol_i = Column(Float)
    sell_vol_n = Column(Float)

    # computed — بر اساس حجم
    buy_per_capita_i = Column(Float)
    sell_per_capita_i = Column(Float)
    net_individual_flow = Column(Float)   # buy_vol_i - sell_vol_i

    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class EmamiCoinPrice(Base):
    """قیمت سکه امامی (جایگزین CoinPrice)"""
    __tablename__ = "emami_coin_prices"
    __table_args__ = (UniqueConstraint("record_date", name="uq_emami_date"),)

    id = Column(Integer, primary_key=True)
    record_date = Column(Date, index=True, nullable=False)
    price = Column(Float)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class GoldPrice18K(Base):
    """قیمت طلای ۱۸ عیار (جایگزین GoldPrice)"""
    __tablename__ = "gold_prices_18k"
    __table_args__ = (UniqueConstraint("record_date", name="uq_gold18k_date"),)

    id = Column(Integer, primary_key=True)
    record_date = Column(Date, index=True, nullable=False)
    xau_usd = Column(Float)
    usd_irr = Column(Float)
    gold_18k_irr = Column(Float)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class XAUUSDTradingView(Base):
    """TradingView XAU/USD snapshot."""
    __tablename__ = "xauusd_tradingview"
    __table_args__ = (UniqueConstraint("symbol", "fetched_at", name="uq_xauusd_symbol_fetched_at"),)

    id = Column(Integer, primary_key=True)
    symbol = Column(String, nullable=False, default="XAUUSD", index=True)
    price = Column(Float, nullable=False)
    fetched_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class FundBubble(Base):
    __tablename__ = "fund_bubbles"
    __table_args__ = (UniqueConstraint("fund_ins_code", "record_date", name="uq_bubble_fund_date"),)

    id = Column(Integer, primary_key=True)
    fund_ins_code = Column(String, index=True, nullable=False)
    record_date = Column(Date, index=True, nullable=False)
    market_price = Column(Float)
    nav_red = Column(Float)
    nominal_bubble_pct = Column(Float)
    real_bubble_pct = Column(Float)
    intrinsic_bubble_pct = Column(Float)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class UsdtPrice(Base):
    """قیمت تتر از نوبیتکس — شامل last price و best bid/ask"""
    __tablename__ = "usdt_prices"
    __table_args__ = (UniqueConstraint("record_date", "record_time", name="uq_usdt_date_time"),)

    id = Column(Integer, primary_key=True)
    symbol = Column(String, default="USDTIRT", nullable=False)
    record_date = Column(Date, index=True, nullable=False)
    record_time = Column(String, nullable=False)      # HH:MM:SS

    last_price = Column(Float)                        # lastTradePrice
    best_bid = Column(Float)                          # bids[0][0]
    best_ask = Column(Float)                          # asks[0][0]
    bid_volume = Column(Float)                        # bids[0][1]
    ask_volume = Column(Float)                        # asks[0][1]
    spread = Column(Float)                            # best_ask - best_bid
    spread_pct = Column(Float)                        # spread / best_ask * 100
    fetched_at = Column(DateTime, nullable=False)     # UTC timestamp
    api_last_update = Column(Float)                   # lastUpdate از API (epoch ms)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
