"""Which assumptions would change the Project 3 recommendation, and at what value.

Reads the tables morning_offer.py writes. The only new input is the cost of an extra
morning staff shift, taken from the truck case ($40 a day per person, an ASSUMPTION there too).

Run from the repo root (after morning_offer.py):  python morning/decision_thresholds.py
Writes outputs/morning/tables/decision_thresholds.csv
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

TABLES = ROOT / "outputs" / "morning" / "tables"
TABLES.mkdir(parents=True, exist_ok=True)
STAFF_SHIFT_PER_DAY = 40.0   # ASSUMPTION: same daily staff cost as the truck case (docs/2_holiday_truck.md)
CENTRAL_NEW_SHARE = 0.5
CENTRAL_EXTRA = 5


def main() -> None:
    ch = pd.read_csv(TABLES / "morning_channel_economics.csv")
    sc = pd.read_csv(TABLES / "morning_scenarios.csv")
    days = int(sc.office_days_per_year.iloc[0])
    rows = []

    def add(lever, assumption, today, threshold, flips_to):
        rows.append({"lever": lever, "assumption_in_estimate": assumption, "value_used": today,
                     "break_even_value": threshold, "if_worse_than_break_even": flips_to})

    loyal = ch[(ch.bundle == "Coffee + any pastry") & ch.channel.str.startswith("Walk-in")].iloc[0]
    add("Loyalty card (6th free)", "Share of bundle orders from new customers", "30% / 50% / 70%",
        f"{loyal.min_share_of_orders_that_must_be_new_pct:.0f}% new",
        "Card only rewards existing customers: drop it, keep the bundle price")

    for b in ["Harbour", "Garden", "Uptown"]:
        r = sc[(sc.branch == b) & (sc.new_customer_share == CENTRAL_NEW_SHARE)
               & (sc.extra_orders_per_branch_per_office_day == CENTRAL_EXTRA)].iloc[0]
        per_order_year = r.gross_profit_per_year_usd / CENTRAL_EXTRA
        shift = STAFF_SHIFT_PER_DAY * days
        need = shift / per_order_year
        add(f"Staffing ({b})", "Today's morning team serves the extra orders", "No extra cost",
            f"+{need:.0f} orders a day (+{need / r.morning_orders_per_day_now:.0%} on today's mornings) "
            f"to pay one extra ${STAFF_SHIFT_PER_DAY:.0f} shift",
            "If the offer needs an extra person, it does not pay at +2 to +10 orders a day: run it only with today's team")

    pack = ch[(ch.bundle == "Office pack (4+4)") & ch.channel.str.contains("Own courier")]
    profit = pack.bundle_profit.iloc[0]
    add("Office-pack delivery", "Courier cost per trip (sourced $2-6)", "$2 / $4 / $6",
        f"${0.5 * profit:.2f} a trip makes it need 50% new customers (pack profit ${profit:.2f})",
        "Above that, drop free delivery; keep walk-in office packs")

    single = ch[(ch.bundle == "Coffee + any pastry") & ch.channel.str.contains("Own courier")]
    add("Single-bundle delivery (rejected)", "Courier cost per trip", "$2 / $4 / $6",
        f"${0.3 * single.bundle_profit.iloc[0]:.2f} a trip would be needed to pay at 30% new customers",
        "Stays rejected unless a courier quote is below that")

    out = pd.DataFrame(rows)
    out.to_csv(TABLES / "decision_thresholds.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_colwidth", 120)
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
