"""Four ways to reach customers who are not standing in a branch.

Run from the repo root, after truck/truck_menu.py, truck/eid_boxes.py and
truck/truck_model.py:
    python truck/channel_comparison.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

from src.clean import GP, REV, load_clean  # noqa: E402
from src import style  # noqa: E402

# Reuse the truck cost model rather than typing the same assumptions twice.
sys.path.insert(0, str(ROOT / "truck"))
import truck_model as model  # noqa: E402

TABLES = ROOT / "outputs" / "truck" / "tables"
FIGS = ROOT / "outputs" / "truck" / "figures"

# Pop-up. ASSUMPTION - verify locally. Beirut Holidays is 13 days in the calendar.
POPUP_STAND_PER_DAY = 100
POPUP_DAYS = 13
POPUP_EVENT = "Beirut Holidays, Antelias-Naccache, 16-28 Jul 2026"
# Boxes use the branches. The only new cash is the packaging assumption in eid_boxes.py.
BOX_DAYS = 4  # Eid al-Fitr length. The cost of a trading day is the branch's, already paid.


def popup_daily() -> float:
    return POPUP_STAND_PER_DAY + model.STAFF_COUNT * model.STAFF_DAY_RATE


def year_result(orders: float, daily: float, days: int, profit_per_order: float, upfront: float, cash_fixed: float, depreciation: float) -> dict:
    product = orders * profit_per_order * days
    cash = product - daily * days - cash_fixed
    net = cash - depreciation
    cash_per_day = daily + (cash_fixed / days if days else 0)
    full_per_day = cash_per_day + (depreciation / days if days else 0)
    breakeven = full_per_day / profit_per_order
    return {
        "upfront": upfront,
        "cost_per_trading_day": cash_per_day,
        "breakeven_orders_per_day": breakeven,
        "net_profit": net,
        "cash_profit": cash,
    }


def main() -> None:
    df = load_clean()
    _ = (GP, REV)
    ticket, profit_per_order = model.load_unit_economics()
    demand = {key: orders for key, _, orders in model.measured_demand(df)}
    targets = pd.read_csv(TABLES / "eid_box_targets.csv").set_index("metric")["value"]
    boxes = pd.read_csv(TABLES / "eid_boxes.csv")
    box6 = boxes[(boxes["item"] == "Box of 6") & (boxes["branch"] == "Harbour")].iloc[0]

    # Boxes: one Fitr, sell enough Harbour boxes of 6 to replace the profit gap.
    lost_profit = float(targets["fitr_gross_profit_lost"])
    packaging = float(targets["packaging_and_promotion"])
    box_profit = float(box6["box_profit"])
    boxes_needed = lost_profit / box_profit
    box_net = lost_profit - packaging  # replaces the gap, then pays for packaging

    channels = []

    def add(name, upfront, daily, days, cash_fixed, depreciation, risk, proves, note):
        garden = year_result(demand["garden_avg"], daily, days, profit_per_order, upfront, cash_fixed, depreciation)
        harbour = year_result(demand["harbour_avg"], daily, days, profit_per_order, upfront, cash_fixed, depreciation)
        channels.append({
            "channel": name,
            "upfront_cost": upfront,
            "cost_per_trading_day": garden["cost_per_trading_day"],
            "breakeven_orders_per_day": garden["breakeven_orders_per_day"],
            "net_profit_garden_demand": garden["net_profit"],
            "net_profit_harbour_demand": harbour["net_profit"],
            "days_in_the_year_case": days,
            "risk": risk,
            "what_it_proves": proves,
            "note": note,
        })

    add(
        "1 Eid boxes + limited edition",
        packaging,
        0.0,
        BOX_DAYS,
        0.0,
        0.0,
        "low",
        "Whether people will pre-order before they leave Beirut.",
        "ESTIMATE upfront $500. Net profit column is replaced below: boxes are not sold at a branch's orders/day.",
    )
    # Override the truck-style net: the box test is the Fitr profit gap, not Garden orders.
    channels[-1]["breakeven_orders_per_day"] = packaging / box_profit
    channels[-1]["net_profit_garden_demand"] = box_net
    channels[-1]["net_profit_harbour_demand"] = box_net
    channels[-1]["cost_per_trading_day"] = 0.0
    channels[-1]["note"] = (
        f"ESTIMATE. Upfront ${packaging:.0f}. Break-even is boxes of 6, not orders/day "
        f"({packaging / box_profit:.1f} Harbour boxes cover the packaging). "
        f"Net profit ${box_net:.0f} if pre-orders replace the Fitr gross-profit gap "
        f"(${lost_profit:.0f}) and then pay the ${packaging:.0f}. Same figure in both demand columns on purpose."
    )

    add(
        "2 Pop-up stand",
        0.0,
        popup_daily(),
        POPUP_DAYS,
        0.0,
        0.0,
        "medium",
        "Whether off-site demand can clear a cheap daily cost.",
        f"ESTIMATE. Stand ${POPUP_STAND_PER_DAY:.0f}/day + 2 staff. Spare machine $0. "
        f"{POPUP_EVENT}, {POPUP_DAYS} days. Ticket ${ticket:.2f} from the truck menu.",
    )
    add(
        "3 Rent a truck",
        model.upfront_cost("rent"),
        model.daily_operating_cost("rent", False),
        model.CHART_DAYS,
        model.annual_cash_fixed("rent"),
        model.annual_depreciation("rent"),
        "high",
        "Whether a mobile shop holds Harbour-sized demand for a season.",
        "ESTIMATE. 44 trading days. Spare machine assumed. US rental rates are not a Lebanon quote.",
    )
    add(
        "4 Buy a used truck",
        model.upfront_cost("buy_used"),
        model.daily_operating_cost("buy_used", False),
        model.CHART_DAYS,
        model.annual_cash_fixed("buy_used"),
        model.annual_depreciation("buy_used"),
        "highest",
        "Nothing, until a rented season has already cleared the 2-year payback level.",
        "ESTIMATE. Upfront is the low end of US listings. Net profit is after 5-year depreciation.",
    )

    table = pd.DataFrame(channels)
    TABLES.mkdir(parents=True, exist_ok=True)
    FIGS.mkdir(parents=True, exist_ok=True)
    table.to_csv(TABLES / "truck_channel_comparison.csv", index=False, float_format="%.4f")
    plot(table)
    print(table[["channel", "upfront_cost", "cost_per_trading_day", "breakeven_orders_per_day",
                 "net_profit_garden_demand", "net_profit_harbour_demand"]].to_string(index=False))
    print("Saved -> outputs/truck/tables/truck_channel_comparison.csv")
    print("Saved -> outputs/truck/figures/truck_channel_comparison.png")


def plot(table: pd.DataFrame) -> None:
    """Net profit at Garden-like and Harbour-like demand. One axis."""
    style.apply()
    fig, ax = plt.subplots(figsize=(10.2, 5.8))
    x = np.arange(len(table))
    width = 0.36
    garden = table["net_profit_garden_demand"].to_numpy()
    harbour = table["net_profit_harbour_demand"].to_numpy()
    b1 = ax.bar(x - width / 2, garden, width, color=style.SERIES[0], label="Garden-like demand", zorder=3)
    b2 = ax.bar(x + width / 2, harbour, width, color=style.SERIES[1], label="Harbour-like demand", zorder=3)
    ax.axhline(0, color=style.INK, lw=0.8, zorder=2)
    span = max(np.abs(garden).max(), np.abs(harbour).max())

    def money(v: float) -> str:
        return f"-${abs(v):,.0f}" if v < 0 else f"${v:,.0f}"

    for bars in (b1, b2):
        for i, bar in enumerate(bars):
            if i == 0:  # Eid boxes: same small figure in both columns, labelled once below
                continue
            value = bar.get_height()
            offset = span * 0.03
            y = value + offset if value >= 0 else value - offset
            va = "bottom" if value >= 0 else "top"
            ax.text(bar.get_x() + bar.get_width() / 2, y, money(value), ha="center", va=va, fontsize=8, color=style.INK)
    ax.text(0, span * 0.06, f"{money(garden[0])}\n(same at both demand levels:\n37 boxes replace the Eid gap\nand cover the $500)",
            ha="center", va="bottom", fontsize=8, color=style.INK)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: money(v)))
    ax.set_ylim(-span * 1.35, span * 1.35)
    ax.set_xticks(x)
    ax.set_xticklabels(["Eid boxes", "Pop-up\n13 days", "Rent truck\n44 days", "Buy used\n44 days"])
    ax.set_ylabel("Net profit per year ($)")
    ax.set_title("Four ways to reach customers who are not in a branch")
    ax.legend(loc="upper left", frameon=False)
    fig.text(
        0.01, 0.01,
        "ESTIMATE. Boxes: profit if pre-orders replace the Fitr gap and pay $500. Truck and pop-up: branch order rates applied to those formats.",
        color=style.MUTED, fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(FIGS / "truck_channel_comparison.png")
    plt.close(fig)


if __name__ == "__main__":
    main()
