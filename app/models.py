import datetime

from sqlalchemy import (
    BigInteger,
    Column,
    Date,
    DateTime,
    Float,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)

from app.db import Base


def _utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


# -------------------------
# FUND META DATA
# -------------------------
class Fund(Base):
    __tablename__ = "funds"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    ins_code = Column(String, unique=True, index=True, nullable=False)
    reg_no = Column(BigInteger, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


# -------------------------
# CORE ARBITRAGE SNAPSHOT
# -------------------------
class FundSnapshot(Base):
    __tablename__ = "fund_snapshots"
    __table_args__ = (
        UniqueConstraint("fund_ins_code", "record_date", name="uq_snapshot_fund_date"),
    )

    id = Column(Integer, primary_key=True)
    fund_ins_code = Column(String, index=True, nullable=False)
    reg_no = Column(BigInteger, index=True)
    record_date = Column(Date, index=True, nullable=False)

    # 🔥 CORE ARBITRAGE FIELDS
    nav_sub = Column(Float)
    nav_red = Column(Float)
    nav_stat = Column(Float)

    # 📊 SIZE / VALIDITY
    net_asset = Column(Float)
    units = Column(Float)

    created_at = Column(DateTime(timezone=True), default=_utcnow)


# -------------------------
# DAILY CLOSING PRICE SNAPSHOT
# -------------------------
class ClosingPriceDaily(Base):
    __tablename__ = "closing_price_daily"
    __table_args__ = (
        UniqueConstraint("ins_code", "record_date", name="uq_closing_ins_date"),
    )

    id = Column(Integer, primary_key=True)
    ins_code = Column(String, index=True, nullable=False)
    record_date = Column(Date, index=True, nullable=False)

    # Commonly queried fields from the TSETMC response
    price_first = Column(Float)
    price_min = Column(Float)
    price_max = Column(Float)
    price_last = Column(Float)
    p_closing = Column(Float)
    q_tot_tran5j = Column(Float)

    # Keep the entire original payload so no API field is lost
    raw_data = Column(JSON, nullable=False)

    created_at = Column(DateTime(timezone=True), default=_utcnow)


    # -------------------------
# GOLD PRICE (XAU/USD)
# -------------------------
class GoldPrice(Base):
    __tablename__ = "gold_prices"
    __table_args__ = (
        UniqueConstraint("record_date", name="uq_gold_price_date"),
    )

    id = Column(Integer, primary_key=True)
    record_date = Column(Date, index=True, nullable=False)
    xau_usd = Column(Float)  # XAU/USD spot price
    created_at = Column(DateTime(timezone=True), default=_utcnow)


# -------------------------
# حباب روزانه
# -------------------------
class FundBubble(Base):
    __tablename__ = "fund_bubbles"
    __table_args__ = (
        UniqueConstraint("fund_ins_code", "record_date", name="uq_bubble_fund_date"),
    )

    id = Column(Integer, primary_key=True)
    fund_ins_code = Column(String, index=True, nullable=False)
    fund_name = Column(String)
    record_date = Column(Date, index=True, nullable=False)
    nav_red = Column(Float)       # NAV ابطال
    price_last = Column(Float)    # قیمت بازار
    bubble_pct = Column(Float)    # حباب درصد = (price/nav - 1) * 100
    created_at = Column(DateTime(timezone=True), default=_utcnow)


# -------------------------
# COIN PRICE (سکه بهار آزادی)
# -------------------------
class CoinPrice(Base):
    __tablename__ = "coin_prices"
    __table_args__ = (
        UniqueConstraint("record_date", name="uq_coin_price_date"),
    )

    id = Column(Integer, primary_key=True)
    record_date = Column(Date, index=True, nullable=False)
    price = Column(Float)        # قیمت لحظه‌ای (ریال)
    price_high = Column(Float)   # بالاترین روز
    price_low = Column(Float)    # پایین‌ترین روز
    created_at = Column(DateTime(timezone=True), default=_utcnow)