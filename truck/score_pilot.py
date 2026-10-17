"""Score a filled truck/pilot_log.csv against the go / no-go rules.

channel is one of: boxes, popup, rent.
An empty log prints the targets and stops. It does not invent a result.

Run from the repo root, after the other truck scripts:
    python truck/score_pilot.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from src.clean import GP, REV, load_clean  # noqa: E402
from src import style  # noqa: E402

_ = (GP, REV, load_clean, style.SERIES)

LOG = ROOT / "truck" / "pilot_log.csv"
TABLES = ROOT / "outputs" / "truck" / "tables"

def targets() -> dict[str, float]:
    box = pd.read_csv(TABLES / "eid_box_targets.csv").set_index("metric")["value"]
    capacity = pd.read_csv(TABLES / "truck_capacity.csv").set_index("metric")["value"]
    return {
        "boxes_of_6_to_replace_gap": float(box["boxes_to_replace_fitr_profit_Box of 6"]),
        "boxes_of_6_to_cover_packaging": float(box["boxes_to_cover_packaging_Box of 6"]),
        "popup_go_orders_per_day": float(capacity["rent_breakeven_orders_per_day"]),
        "buy_go_orders_per_day": float(capacity["buy_used_two_year_orders_per_day"]),
    }


def main() -> None:
    goal = targets()
    log = pd.read_csv(LOG)
    print("Targets (from the measured gap and the cost model)")
    print(f"  Boxes go: at least {goal['boxes_of_6_to_replace_gap']:.0f} boxes of 6, and {goal['boxes_of_6_to_cover_packaging']:.0f} to cover packaging.")
    print(f"  Pop-up go: average at least {goal['popup_go_orders_per_day']:.0f} orders/day (the rent break-even).")
    print(f"  Rent go-to-buy: average at least {goal['buy_go_orders_per_day']:.0f} orders/day over the season.")
    if log.empty:
        print("pilot_log.csv has no rows. Fill it during the test, then run this again.")
        return
    for channel, part in log.groupby("channel"):
        if channel == "boxes":
            sold = part["boxes_of_6"].fillna(0).sum() + 2 * part["boxes_of_12"].fillna(0).sum()
            replace = sold >= goal["boxes_of_6_to_replace_gap"]
            cover = sold >= goal["boxes_of_6_to_cover_packaging"]
            print(f"Boxes: {sold:.0f} box-of-6 equivalents. Replace gap: {replace}. Cover $500: {cover}.")
        elif channel == "popup":
            avg = part["orders"].mean()
            print(f"Pop-up: {avg:.1f} orders/day. Go to a truck rental: {avg >= goal['popup_go_orders_per_day']}.")
        elif channel == "rent":
            avg = part["orders"].mean()
            print(f"Rental: {avg:.1f} orders/day over {len(part)} days. Go to buy: {avg >= goal['buy_go_orders_per_day']}.")
        else:
            print(f"Unknown channel '{channel}'. Use boxes, popup, or rent.")


if __name__ == "__main__":
    main()
