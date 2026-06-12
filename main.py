from app.db import Base, engine
from app import models  # noqa: F401 — ensures all models are registered with Base
from app.scraper import run_scraper


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created (or already exist)")


if __name__ == "__main__":
    init_db()
    run_scraper()