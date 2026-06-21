from datetime import date
from app.db import SessionLocal
from app.models import FundSnapshot, ClosingPriceDaily, GoldPrice18K, FundBubble, EmamiCoinPrice
from app.gold_funds import GOLD_FUNDS

# سکه امامی = 8.133 گرم طلای 22 عیار = 7.4 گرم طلای خالص
# معادل طلای 18 عیار: 7.4 * (24/18) = 9.867 گرم طلای 18 عیار
EMAMI_GOLD_GRAMS_18K = 9.867


def calc_and_save_bubbles():
    today = date.today()
    db = SessionLocal()

    try:
        gold = db.query(GoldPrice18K).filter_by(record_date=today).first()
        if not gold:
            print("❌ No 18K gold price for today")
            return

        emami = db.query(EmamiCoinPrice).filter_by(record_date=today).first()
        if not emami:
            print("❌ No Emami coin price for today")
            return

        gold_18k_per_gram = gold.gold_18k_irr
        emami_price = emami.price

        # ارزش ذاتی سکه امامی بر اساس قیمت طلای جهانی
        emami_intrinsic_value = EMAMI_GOLD_GRAMS_18K * gold_18k_per_gram

        # حباب سکه امامی = (قیمت بازار سکه - ارزش ذاتی) / ارزش ذاتی
        emami_bubble = (emami_price - emami_intrinsic_value) / emami_intrinsic_value * 100
        print(f"\n🪙 سکه امامی: {emami_price:,.0f} | ارزش ذاتی: {emami_intrinsic_value:,.0f} | حباب: {emami_bubble:.2f}%\n")

        saved = 0

        for name, ins_code in GOLD_FUNDS.items():

            snap = (
                db.query(FundSnapshot)
                .filter_by(fund_ins_code=ins_code)
                .order_by(FundSnapshot.record_date.desc())
                .first()
            )
            closing = (
                db.query(ClosingPriceDaily)
                .filter_by(ins_code=ins_code)
                .order_by(ClosingPriceDaily.record_date.desc())
                .first()
            )

            if not snap or not closing or not snap.nav_red or not closing.p_closing:
                print(f"  ⚠️ Skipping {name}: missing data")
                continue

            market = closing.p_closing
            nav_red = snap.nav_red

            # گرم طلای 18 عیار پشت هر واحد صندوق
            gold_grams_per_unit = nav_red / gold_18k_per_gram

            # ارزش ذاتی هر واحد بر اساس قیمت طلای خام (بدون حباب سکه)
            intrinsic_value_per_unit = gold_grams_per_unit * gold_18k_per_gram  # = nav_red

            # معادل سکه امامی برای هر واحد
            emami_equivalent = gold_grams_per_unit / EMAMI_GOLD_GRAMS_18K
            # قیمت منصفانه هر واحد بر اساس سکه امامی
            fair_value_emami = emami_equivalent * emami_price

            # ─────────────────────────────────────────────
            # 1. حباب اسمی = فاصله قیمت بازار از NAV
            #    نشان می‌دهد صندوق گران‌تر یا ارزان‌تر از NAV معامله می‌شود
            nominal_bubble = (market - nav_red) / nav_red * 100

            # 2. حباب واقعی = فاصله قیمت بازار از ارزش سکه‌ای
            #    نشان می‌دهد بازار چقدر از قیمت سکه امامی فاصله دارد
            real_bubble = (market - fair_value_emami) / fair_value_emami * 100

            # 3. حباب ذاتی = فاصله NAV از ارزش طلای خام
            #    نشان می‌دهد NAV صندوق چقدر از قیمت طلای خام فاصله دارد
            #    برای صندوق‌های سالم باید نزدیک به صفر باشد
            intrinsic_bubble = (nav_red - intrinsic_value_per_unit) / intrinsic_value_per_unit * 100

            exists = db.query(FundBubble).filter_by(
                fund_ins_code=ins_code,
                record_date=today,
            ).first()

            if exists:
                exists.market_price = market
                exists.nav_red = nav_red
                exists.nominal_bubble_pct = round(nominal_bubble, 4)
                exists.real_bubble_pct = round(real_bubble, 4)
                exists.intrinsic_bubble_pct = round(intrinsic_bubble, 4)
            else:
                db.add(FundBubble(
                    fund_ins_code=ins_code,
                    record_date=today,
                    market_price=market,
                    nav_red=nav_red,
                    nominal_bubble_pct=round(nominal_bubble, 4),
                    real_bubble_pct=round(real_bubble, 4),
                    intrinsic_bubble_pct=round(intrinsic_bubble, 4),
                ))

            saved += 1
            print(
                f"  {name}: "
                f"اسمی={nominal_bubble:+.2f}% | "
                f"واقعی={real_bubble:+.2f}% | "
                f"ذاتی={intrinsic_bubble:+.2f}% | "
                f"پشتوانه={gold_grams_per_unit*1000:.3f}mg"
            )

        db.commit()
        print(f"\n✅ Saved bubbles for {saved} funds")

    finally:
        db.close()