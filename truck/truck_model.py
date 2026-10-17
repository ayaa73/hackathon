"""Rent vs buy scenarios for the holiday truck.

Run from the repo root, after truck/truck_menu.py:
    python truck/truck_model.py

Ticket and product profit per order are read from
outputs/tables/truck_menu_summary.csv. Every constant below is an assumption.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

from src.clean import GP, REV, load_clean  # noqa: E402
from src import style  # noqa: E402

# Imported because the brief requires it. Demand is not re-measured here.
_ = (GP, REV, load_clean)

TABLES = ROOT / "outputs" / "tables"
FIGS = ROOT / "outputs" / "figures"
SUMMARY = TABLES / "truck_menu_summary.csv"

# --- Assumptions. Edit these. None of them are in the transaction file. ---

# Orders per day. ASSUMPTION - verify locally. Not observed for a truck.
ORDERS_PER_DAY = {"low": 100, "mid": 200, "high": 300}

# Days per year the truck actually trades.
# holidays_only = 18 dated days in truck/holiday_calendar.csv before the security cut
#   (Fitr 4 + Adha 2 + New Year/Orthodox Christmas/Christmas 3 + Easter 4
#   + Orthodox Easter 4 + Assumption 1). See docs/truck_sources.md.
# holidays_plus_summer_weekends = 44 = those 18 plus Jul-Aug Fri/Sat/Sun,
#   without counting Saturday 15 Aug twice (27 weekend days - 1).
# holidays_weekends_events = 80. ASSUMPTION - verify locally. Not a count of sourced dates.
DAYS_PER_YEAR = {
    "holidays_only": 18,
    "holidays_plus_summer_weekends": 44,
    "holidays_weekends_events": 80,
}

# Daily operating cost when the vehicle is owned. ASSUMPTION - verify locally.
STAFF_COUNT = 2
STAFF_DAY_RATE = 40  # USD per person per day
FUEL_AND_GENERATOR = 40  # USD per day
SITE_FEE = 50  # municipality / site, USD per day
MISC_DAY = 30  # USD per day

# Option 1, rent a pilot. ASSUMPTION - verify locally (no Lebanon rate card in the sources).
VEHICLE_RENT_PER_DAY = 150
GENERATOR_RENT_PER_DAY = 40
# Spare branch machine. If operations cannot confirm one, set this False.
SPARE_ESPRESSO_MACHINE = True
MACHINE_IF_NO_SPARE = 5_500  # Zion entry 2-group, low end of the stated range
GRINDER_IF_NO_SPARE = 1_500  # Zion low end
BRANDING_AND_CUPS = 1_500  # ASSUMPTION - verify locally. One-time.

# Option 2, buy a used trailer. Low end of Zion Foodtrucks ranges (US, not Lebanon).
USED_TRAILER = 30_000  # Zion used outfitted trailer, bottom of $30k-60k
USED_EQUIPMENT = 15_000  # Zion full equipment package, bottom of $15k-40k
WRAP = 2_500  # Zion wrap, bottom of $2.5k-5k
PERMITS = 800  # Zion permits, bottom of ~$800-17k+. Optimistic.
OPENING_INVENTORY = 3_000  # Zion opening inventory, bottom of $3k-5k

# Option 3, buy the HorecaStore 14-ft trailer.
NEW_TRAILER = 49_999  # HorecaStore list price
SHIPPING = 3_000  # ASSUMPTION - verify locally. Not priced on the HorecaStore page.

PAYBACK_LIMIT_YEARS = 2
MID = "mid"


def daily_operating_cost(option: str) -> float:
    """Cash cost of one trading day, before product cost (product cost is in gross profit)."""
    owned = STAFF_COUNT * STAFF_DAY_RATE + FUEL_AND_GENERATOR + SITE_FEE + MISC_DAY
    if option == "rent":
        return owned + VEHICLE_RENT_PER_DAY + GENERATOR_RENT_PER_DAY
    return owned


def upfront_cost(option: str, spare_machine: bool = SPARE_ESPRESSO_MACHINE) -> float:
    if option == "rent":
        equipment = 0 if spare_machine else MACHINE_IF_NO_SPARE + GRINDER_IF_NO_SPARE
        return BRANDING_AND_CUPS + equipment
    if option == "buy_used":
        return USED_TRAILER + USED_EQUIPMENT + WRAP + PERMITS + OPENING_INVENTORY
    if option == "buy_new":
        return NEW_TRAILER + SHIPPING + WRAP + PERMITS + OPENING_INVENTORY
    raise KeyError(option)


OPTIONS = [
    ("rent", "1 Rent pilot"),
    ("buy_used", "2 Buy used"),
    ("buy_new", "3 Buy new"),
]


def load_unit_economics() -> tuple[float, float]:
    summary = pd.read_csv(SUMMARY).set_index("metric")
    ticket = float(summary.loc["ticket_per_order", "value"])
    profit_per_order = float(summary.loc["product_profit_per_order", "value"])
    if ticket <= 0 or profit_per_order <= 0:
        raise SystemExit("Ticket and product profit per order must be positive.")
    return ticket, profit_per_order


def scenarios(ticket: float, profit_per_order: float) -> pd.DataFrame:
    rows = []
    for key, label in OPTIONS:
        daily = daily_operating_cost(key)
        upfront = upfront_cost(key)
        breakeven = daily / profit_per_order
        for demand_name, orders in ORDERS_PER_DAY.items():
            for days_name, days in DAYS_PER_YEAR.items():
                revenue = orders * ticket * days
                product_gp = orders * profit_per_order * days
                opex = daily * days
                net = product_gp - opex
                payback = upfront / net if net > 0 else np.inf
                rows.append({
                    "option": key,
                    "option_label": label,
                    "orders_scenario": demand_name,
                    "orders_per_day": orders,
                    "days_scenario": days_name,
                    "days_per_year": days,
                    "revenue": revenue,
                    "product_gross_profit": product_gp,
                    "operating_cost": opex,
                    "net_profit": net,
                    "upfront": upfront,
                    "first_year_cash": net - upfront,
                    "payback_years": payback,
                    "breakeven_orders_per_day": breakeven,
                    "within_2_years": bool(payback <= PAYBACK_LIMIT_YEARS),
                })
    return pd.DataFrame(rows)


def breakeven_table(ticket: float, profit_per_order: float) -> pd.DataFrame:
    rows = []
    for key, label in OPTIONS:
        daily = daily_operating_cost(key)
        breakeven = daily / profit_per_order
        rows.append({
            "option": key,
            "option_label": label,
            "daily_operating_cost": daily,
            "profit_per_order": profit_per_order,
            "ticket_per_order": ticket,
            "breakeven_orders_per_day": breakeven,
            "clears_low_100": breakeven <= ORDERS_PER_DAY["low"],
            "clears_mid_200": breakeven <= ORDERS_PER_DAY["mid"],
            "clears_high_300": breakeven <= ORDERS_PER_DAY["high"],
            "note": "ESTIMATE. Break-even = daily operating cost / product profit per order.",
        })
    return pd.DataFrame(rows)


def plot_payback(grid: pd.DataFrame) -> None:
    """Payback years at the mid order scenario. One axis."""
    style.apply()
    mid = grid[grid["orders_scenario"] == MID]
    day_names = list(DAYS_PER_YEAR)
    x = np.arange(len(day_names))
    width = 0.24
    fig, ax = plt.subplots(figsize=(9.8, 5.8))
    finite = []
    for i, (key, label) in enumerate(OPTIONS):
        part = mid[mid["option"] == key].set_index("days_scenario").loc[day_names]
        heights = part["payback_years"].to_numpy(dtype=float)
        finite.extend(heights[np.isfinite(heights)])
        offset = (i - 1) * width
        bars = ax.bar(
            x + offset, heights, width, color=style.SERIES[i], label=label, zorder=3,
        )
        for bar, value in zip(bars, heights):
            text = "n/a" if not np.isfinite(value) else f"{value:.2f}"
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                (0 if not np.isfinite(value) else value) + 0.12,
                text,
                ha="center",
                va="bottom",
                fontsize=8,
                color=style.INK,
            )
    ax.axhline(PAYBACK_LIMIT_YEARS, color=style.MUTED, ls="--", lw=1, zorder=2)
    ax.annotate(
        "2-year test",
        xy=(1, PAYBACK_LIMIT_YEARS),
        xycoords=("axes fraction", "data"),
        xytext=(-6, 5),
        textcoords="offset points",
        ha="right",
        va="bottom",
        color=style.MUTED,
        fontsize=8,
    )
    ax.set_xticks(x)
    ax.set_xticklabels(["18 days\nHolidays only", "44 days\n+ summer weekends", "80 days\n+ events"])
    ax.set_ylabel("Payback (years)")
    ax.set_xlabel("Days the truck trades in a year  ·  mid scenario, 200 orders/day")
    top = max(finite) if finite else PAYBACK_LIMIT_YEARS
    ax.set_ylim(0, top * 1.22)
    ax.set_title("Payback at 200 orders/day")
    ax.legend(loc="upper right")
    fig.text(
        0.01, 0.01,
        "ESTIMATE. Rent assumes a spare branch espresso machine ($0). Buy prices are the low end of US listings.",
        color=style.MUTED, fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(FIGS / "truck_payback.png")
    plt.close(fig)


def plot_breakeven(breaks: pd.DataFrame) -> None:
    """Break-even orders/day against the 100 / 200 / 300 scenarios. One axis."""
    style.apply()
    fig, ax = plt.subplots(figsize=(9.8, 5.4))
    labels = breaks["option_label"].tolist()
    values = breaks["breakeven_orders_per_day"].to_numpy(dtype=float)
    y = np.arange(len(labels))
    ax.barh(y, values, color=[style.SERIES[i] for i in range(len(labels))], height=0.62, zorder=3)
    for yi, value in zip(y, values):
        ax.text(
            value - 3, yi, f"{value:.0f}",
            ha="right", va="center", color=style.SURFACE, fontsize=10, fontweight="bold",
        )
    scenario_style = [
        (ORDERS_PER_DAY["low"], "Low 100", style.SERIES[3]),
        (ORDERS_PER_DAY["mid"], "Mid 200", style.SERIES[4]),
        (ORDERS_PER_DAY["high"], "High 300", style.SERIES[5]),
    ]
    handles = []
    for orders, name, color in scenario_style:
        ax.axvline(orders, color=color, ls="--", lw=1.1, zorder=2)
        handles.append(Line2D([0], [0], color=color, ls="--", lw=1.1, label=name))
    # White space between the Low and Mid lines. Keeps the labels off the title.
    ax.legend(
        handles=handles, loc="center", bbox_to_anchor=(0.46, 0.62),
        frameon=False, handlelength=1.6,
    )
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Orders per day")
    ax.set_xlim(0, 360)
    ax.set_title("Break-even orders per day")
    ax.tick_params(axis="y", colors=style.INK)
    fig.text(
        0.01, 0.01,
        "ESTIMATE. Bars are break-even. Dashed lines are the low / mid / high scenarios, not measured truck demand.",
        color=style.MUTED, fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.05, 1, 0.96))
    fig.savefig(FIGS / "truck_breakeven.png")
    plt.close(fig)


def print_summary(grid: pd.DataFrame, breaks: pd.DataFrame, profit_per_order: float) -> None:
    print("Break-even orders/day (same for every day-count; it is a daily test)")
    for row in breaks.itertuples():
        print(f"  {row.option_label}: {row.breakeven_orders_per_day:.1f}  "
              f"(daily cost ${row.daily_operating_cost:.0f} / ${profit_per_order:.2f} profit per order)")
    print(f"Pays back within {PAYBACK_LIMIT_YEARS:.0f} years:")
    hit = grid[grid["within_2_years"]]
    if hit.empty:
        print("  None.")
    else:
        for row in hit.itertuples():
            print(f"  {row.option_label} | {row.orders_scenario} {row.orders_per_day:.0f}/day | "
                  f"{row.days_scenario} {row.days_per_year:.0f} days | payback {row.payback_years:.2f} years")
    print("Mid scenario payback (200 orders/day):")
    mid = grid[grid["orders_scenario"] == MID]
    for row in mid.itertuples():
        print(f"  {row.option_label} | {row.days_per_year:.0f} days | "
              f"net ${row.net_profit:,.0f} | payback {row.payback_years:.2f} years | "
              f"first-year cash ${row.first_year_cash:,.0f}")

    # Sensitivity only. Not a fourth chart series. Spare machine is the base case.
    rent_daily = daily_operating_cost("rent")
    no_spare = upfront_cost("rent", spare_machine=False)
    print(f"Sensitivity: rent with no spare machine, upfront ${no_spare:,.0f} "
          f"(branding ${BRANDING_AND_CUPS:,.0f} + machine ${MACHINE_IF_NO_SPARE:,.0f} "
          f"+ grinder ${GRINDER_IF_NO_SPARE:,.0f}).")
    for days_name, days in DAYS_PER_YEAR.items():
        net = (ORDERS_PER_DAY[MID] * profit_per_order - rent_daily) * days
        payback = no_spare / net if net > 0 else np.inf
        print(f"  mid, {days_name}, {days} days: payback {payback:.2f} years")


def main() -> None:
    if not SUMMARY.exists():
        raise SystemExit("Missing truck_menu_summary.csv. Run python truck/truck_menu.py first.")
    ticket, profit_per_order = load_unit_economics()
    grid = scenarios(ticket, profit_per_order)
    breaks = breakeven_table(ticket, profit_per_order)
    TABLES.mkdir(parents=True, exist_ok=True)
    FIGS.mkdir(parents=True, exist_ok=True)
    grid.to_csv(TABLES / "truck_scenarios.csv", index=False, float_format="%.4f")
    breaks.to_csv(TABLES / "truck_breakeven.csv", index=False, float_format="%.4f")
    plot_payback(grid)
    plot_breakeven(breaks)
    print_summary(grid, breaks, profit_per_order)
    print("Saved -> outputs/tables/truck_scenarios.csv")
    print("Saved -> outputs/tables/truck_breakeven.csv")
    print("Saved -> outputs/figures/truck_payback.png")
    print("Saved -> outputs/figures/truck_breakeven.png")


if __name__ == "__main__":
    main()
