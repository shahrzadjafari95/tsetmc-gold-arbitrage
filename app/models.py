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