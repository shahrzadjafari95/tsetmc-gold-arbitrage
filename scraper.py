from app.db import Base, engine
from app import models  # noqa: F401 - register models
from app.save_selected_funds import FUNDS, _upsert_fund, save_closing_price_daily
from app.db import SessionLocal


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created (or already exist)")


def run_selected_funds(days: int = 365) -> None:
    for name, ins_code in FUNDS.items():
        db = SessionLocal()
        try:
            inserted = _upsert_fund(db, name=name, ins_code=ins_code)
            db.commit()
            print(f"[{name}] Fund {'inserted' if inserted else 'already existed'}")
        except Exception as e:
            db.rollback()
            print(f"[{name}] ❌ Fund save error: {e}")
        finally:
            db.close()

        save_closing_price_daily(ins_code, name, days=days)


if __name__ == "__main__":
    init_db()
    run_selected_funds()
