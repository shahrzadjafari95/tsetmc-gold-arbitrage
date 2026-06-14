import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://shahrzadjafari@localhost:5432/market_data",
)

engine = create_engine(DB_URL, echo=False)

SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()
