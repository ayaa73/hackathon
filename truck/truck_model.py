"""Truck scenarios anchored to what Stories' branches actually do.

100 / 200 / 300 orders a day are kept only as stretch cases. They sit above
any day a Stories branch has recorded. Demand levels are computed here from
the transaction file. Costs that are not in the file are constants below.

Run from the repo root, after truck/truck_menu.py:
    python truck/truck_model.py
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

TABLES = ROOT / "outputs" / "tables"
FIGS = ROOT / "outputs" / "figures"
SUMMARY = TABLES / "truck_menu_summary.csv"

# --- Costs. None of these are in the transaction file. ---

STAFF_COUNT = 2
STAFF_DAY_RATE = 40  # ASSUMPTION - verify locally. USD per person per day.
FUEL_AND_GENERATOR = 40  # ASSUMPTION - verify locally.
SITE_FEE = 50  # ASSUMPTION - verify locally.
MISC_DAY = 30  # ASSUMPTION - verify locally.

VEHICLE_RENT_PER_DAY = 150  # ASSUMPTION - verify locally.
GENERATOR_RENT_PER_DAY = 40  # ASSUMPTION - verify locally.
SPARE_ESPRESSO_MACHINE = True
MACHINE_IF_NO_SPARE = 5_500  # Zion entry 2-group, low end.
GRINDER_IF_NO_SPARE = 1_500  # Zion low end.
BRANDING_AND_CUPS = 1_500  # ASSUMPTION - verify locally.

USED_TRAILER = 30_000  # Zion used trailer, bottom of $30k-60k.
USED_EQUIPMENT = 15_000  # Zion equipment package, bottom of $15k-40k.
WRAP = 2_500  # Zion wrap, bottom of $2.5k-5k.
PERMITS = 800  # Zion permits, bottom of ~$800-17k+. Optimistic.
OPENING_INVENTORY = 3_000  # Zion opening inventory, bottom of $3k-5k.
NEW_TRAILER = 49_999  # HorecaStore 14-ft list price.
SHIPPING = 3_000  # ASSUMPTION - verify locally. Not on the HorecaStore page.

# Owned-truck fixed costs. ASSUMPTION - verify locally.
INSURANCE_PER_YEAR = 1_500
MAINTENANCE_PER_YEAR = 2_000
STORAGE_PER_YEAR = 1_200
DEPRECIATION_YEARS = 5

# One unpaid travel day per trading day, for trips outside Beirut.
# Staff and fuel only. No sales, no site fee. Off for the main tables.
INCLUDE_UNPAID_TRAVEL_DAY = False

DAYS_PER_YEAR = {
    "holidays_only": 18,
    "holidays_plus_summer_weekends": 44,
    "holidays_weekends_events": 80,
}
# Fixed costs on the per-day chart are spread over this many trading days.
CHART_DAYS = 44
PAYBACK_LIMIT_YEARS = 2
# Stretch cases are not a forecast. No Stories branch-day has reached them.
STRETCH = {"stretch_200": 200, "stretch_300": 300}

OPTIONS = [
    ("rent", "1 Rent"),
    ("buy_used", "2 Buy used"),
    ("buy_new", "3 Buy new"),
]


def measured_demand(df: pd.DataFrame) -> list[tuple[str, str, float]]:
    """Orders per branch-day, computed. Returns (key, label, orders)."""
    orders = (
        df.groupby(["Date", "Branch"])["Transaction ID"]
        .nunique()
        .rename("orders")
        .reset_index()
    )
    uptown = float(orders.loc[orders["Branch"] == "Uptown", "orders"].mean())
    garden = float(orders.loc[orders["Branch"] == "Garden", "orders"].mean())
    harbour = float(orders.loc[orders["Branch"] == "Harbour", "orders"].mean())
    tuesday = orders[(orders["Branch"] == "Harbour") & (orders["Date"].dt.dayofweek == 1)]
    harbour_tuesday = float(tuesday["orders"].mean())
    best = float(orders["orders"].max())
    return [
        ("uptown_avg", "Uptown avg", uptown),
        ("garden_avg", "Garden avg", garden),
        ("harbour_avg", "Harbour avg", harbour),
        ("harbour_tuesday", "Harbour Tuesday", harbour_tuesday),
        ("best_branch_day", "Best day ever", best),
    ]


def load_unit_economics() -> tuple[float, float]:
    summary = pd.read_csv(SUMMARY).set_index("metric")
    ticket = float(summary.loc["ticket_per_order", "value"])
    profit = float(summary.loc["product_profit_per_order", "value"])
    if ticket <= 0 or profit <= 0:
        raise SystemExit("Ticket and product profit per order must be positive.")
    return ticket, profit


def owned_day() -> float:
    return STAFF_COUNT * STAFF_DAY_RATE + FUEL_AND_GENERATOR + SITE_FEE + MISC_DAY


def travel_day_cost() -> float:
    """Staff and fuel for a day with no sales. ASSUMPTION - verify locally."""
    return STAFF_COUNT * STAFF_DAY_RATE + FUEL_AND_GENERATOR


def daily_operating_cost(option: str, travel: bool = INCLUDE_UNPAID_TRAVEL_DAY) -> float:
    base = owned_day()
    if option == "rent":
        base += VEHICLE_RENT_PER_DAY + GENERATOR_RENT_PER_DAY
    if travel:
        base += travel_day_cost()
    return base


def upfront_cost(option: str, spare_machine: bool = SPARE_ESPRESSO_MACHINE) -> float:
    if option == "rent":
        equipment = 0 if spare_machine else MACHINE_IF_NO_SPARE + GRINDER_IF_NO_SPARE
        return BRANDING_AND_CUPS + equipment
    if option == "buy_used":
        return USED_TRAILER + USED_EQUIPMENT + WRAP + PERMITS + OPENING_INVENTORY
    if option == "buy_new":
        return NEW_TRAILER + SHIPPING + WRAP + PERMITS + OPENING_INVENTORY
    raise KeyError(option)


def annual_cash_fixed(option: str) -> float:
    """Insurance, maintenance, storage. Renting does not carry these."""
    if option == "rent":
        return 0.0
    return INSURANCE_PER_YEAR + MAINTENANCE_PER_YEAR + STORAGE_PER_YEAR


def annual_depreciation(option: str) -> float:
    if option == "rent":
        return 0.0
    return upfront_cost(option) / DEPRECIATION_YEARS


def scenario_orders(demand: list[tuple[str, str, float]]) -> list[tuple[str, str, float, str]]:
    rows = [(key, label, orders, "MEASURED") for key, label, orders in demand]
    rows.append(("stretch_200", "Stretch 200", STRETCH["stretch_200"], "STRETCH - above any day Stories has recorded"))
    rows.append(("stretch_300", "Stretch 300", STRETCH["stretch_300"], "STRETCH - above any day Stories has recorded"))
    return rows


def build_grid(profit_per_order: float, ticket: float, levels: list[tuple[str, str, float, str]]) -> pd.DataFrame:
    rows = []
    for travel in (False, True):
        for key, label in OPTIONS:
            daily = daily_operating_cost(key, travel)
            upfront = upfront_cost(key)
            cash_fixed = annual_cash_fixed(key)
            depreciation = annual_depreciation(key)
            for demand_key, demand_label, orders, kind in levels:
                for days_name, days in DAYS_PER_YEAR.items():
                    product_gp = orders * profit_per_order * days
                    opex = daily * days + cash_fixed
                    cash_profit = product_gp - opex
                    net = cash_profit - depreciation
                    payback = upfront / cash_profit if cash_profit > 0 else np.inf
                    # Break-even spreads cash fixed costs and depreciation over the trading days.
                    breakeven = (daily + (cash_fixed + depreciation) / days) / profit_per_order
                    rows.append({
                        "option": key,
                        "option_label": label,
                        "travel_day": travel,
                        "orders_scenario": demand_key,
                        "orders_label": demand_label,
                        "orders_per_day": orders,
                        "demand_kind": kind,
                        "days_scenario": days_name,
                        "days_per_year": days,
                        "revenue": orders * ticket * days,
                        "product_gross_profit": product_gp,
                        "operating_cost": opex,
                        "depreciation": depreciation,
                        "net_profit": net,
                        "cash_profit": cash_profit,
                        "upfront": upfront,
                        "first_year_cash": cash_profit - upfront,
                        "payback_years": payback,
                        "breakeven_orders_per_day": breakeven,
                        "within_2_years": bool(payback <= PAYBACK_LIMIT_YEARS),
                    })
    return pd.DataFrame(rows)


def breakeven_table(grid: pd.DataFrame) -> pd.DataFrame:
    """One row per option at each day-count, travel off. Break-even does not depend on demand."""
    base = grid[(~grid["travel_day"]) & (grid["orders_scenario"] == "garden_avg")]
    rows = []
    for row in base.itertuples():
        rows.append({
            "option": row.option,
            "option_label": row.option_label,
            "days_per_year": row.days_per_year,
            "daily_operating_cost": daily_operating_cost(row.option, False),
            "annual_cash_fixed": annual_cash_fixed(row.option),
            "depreciation": row.depreciation,
            "breakeven_orders_per_day": row.breakeven_orders_per_day,
            "note": "ESTIMATE. (daily cost + insurance, maintenance, storage and depreciation / days) / product profit per order.",
        })
    return pd.DataFrame(rows)


def plot_profit_per_day(profit_per_order: float, demand: list[tuple[str, str, float]]) -> None:
    """Net profit per trading day. Buy-used spreads a year of fixed costs over 44 days."""
    style.apply()
    orders = np.linspace(0, 250, 251)
    rent_daily = daily_operating_cost("rent", False)
    buy_daily = daily_operating_cost("buy_used", False)
    buy_fixed_per_day = (annual_cash_fixed("buy_used") + annual_depreciation("buy_used")) / CHART_DAYS
    rent = orders * profit_per_order - rent_daily
    buy = orders * profit_per_order - buy_daily - buy_fixed_per_day

    fig, ax = plt.subplots(figsize=(10.2, 5.8))
    ax.plot(orders, rent, color=style.SERIES[0], lw=2.2, label="Rent", zorder=3)
    ax.plot(orders, buy, color=style.SERIES[1], lw=2.2, label="Buy used", zorder=3)
    ax.axhline(0, color=style.INK, lw=0.8, zorder=2)

    handles = [
        Line2D([0], [0], color=style.SERIES[0], lw=2.2, label="Rent"),
        Line2D([0], [0], color=style.SERIES[1], lw=2.2, label="Buy used"),
    ]
    for i, (key, label, level) in enumerate(demand):
        color = style.SERIES[3 + (i % 5)]
        ax.axvline(level, color=color, ls="--", lw=1, zorder=1)
        handles.append(Line2D([0], [0], color=color, ls="--", lw=1, label=f"{label} ({level:.0f})"))
    ax.legend(
        handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.22),
        ncol=4, frameon=False, fontsize=8,
    )
    ax.set_xlim(0, 250)
    ax.set_xlabel("Orders per day")
    ax.set_ylabel("Net profit per trading day ($)")
    ax.set_title("Truck profit per day at branch-sized demand")
    fig.text(
        0.01, 0.01,
        "ESTIMATE. Buy-used line spreads insurance, maintenance, storage and 5-year depreciation over 44 trading days. Vertical lines are MEASURED.",
        color=style.MUTED, fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.subplots_adjust(bottom=0.28)
    fig.savefig(FIGS / "truck_profit_per_day.png")
    plt.close(fig)


def plot_payback(grid: pd.DataFrame) -> None:
    """Payback at 44 trading days for the measured demand levels. Losses are labelled, not drawn as years."""
    style.apply()
    part = grid[(~grid["travel_day"]) & (grid["days_per_year"] == CHART_DAYS) & (grid["demand_kind"] == "MEASURED")]
    demand_order = list(dict.fromkeys(part["orders_label"]))
    x = np.arange(len(demand_order))
    width = 0.24
    fig, ax = plt.subplots(figsize=(10.2, 5.8))
    finite = []
    for i, (key, label) in enumerate(OPTIONS):
        heights = []
        for name in demand_order:
            row = part[(part["option"] == key) & (part["orders_label"] == name)].iloc[0]
            heights.append(row.payback_years if row.cash_profit > 0 else np.nan)
        heights = np.array(heights, dtype=float)
        finite.extend(heights[np.isfinite(heights)])
        offset = (i - 1) * width
        bars = ax.bar(x + offset, np.nan_to_num(heights), width, color=style.SERIES[i], label=label, zorder=3)
        for bar, value in zip(bars, heights):
            if not np.isfinite(value):
                ax.text(bar.get_x() + bar.get_width() / 2, 0.15, "loss", ha="center", va="bottom", fontsize=7, color=style.INK)
            else:
                ax.text(bar.get_x() + bar.get_width() / 2, value + 0.15, f"{value:.1f}", ha="center", va="bottom", fontsize=7, color=style.INK)
    ax.axhline(PAYBACK_LIMIT_YEARS, color=style.MUTED, ls="--", lw=1, zorder=2)
    ax.annotate(
        "2-year test",
        xy=(0, PAYBACK_LIMIT_YEARS),
        xycoords=("axes fraction", "data"),
        xytext=(6, 4),
        textcoords="offset points",
        ha="left", va="bottom", color=style.MUTED, fontsize=8,
    )
    top = max(finite) if finite else PAYBACK_LIMIT_YEARS
    ax.set_ylim(0, top * 1.28)
    ax.set_xticks(x)
    ax.set_xticklabels(demand_order, fontsize=8)
    ax.set_ylabel("Payback (years)")
    ax.set_xlabel("Measured branch demand, applied to a truck for 44 trading days")
    ax.set_title("Payback at demand Stories has actually seen")
    ax.legend(loc="upper right")
    fig.text(
        0.01, 0.01,
        "ESTIMATE. Cash payback = upfront / (product profit - cash costs). 'loss' means cash profit is negative, so there is no payback.",
        color=style.MUTED, fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(FIGS / "truck_payback.png")
    plt.close(fig)


def plot_breakeven(breaks: pd.DataFrame, demand: list[tuple[str, str, float]]) -> None:
    """Break-even at 44 days against measured branch demand. One axis."""
    style.apply()
    part = breaks[breaks["days_per_year"] == CHART_DAYS]
    fig, ax = plt.subplots(figsize=(10.2, 5.4))
    labels = part["option_label"].tolist()
    values = part["breakeven_orders_per_day"].to_numpy(dtype=float)
    y = np.arange(len(labels))
    ax.barh(y, values, color=[style.SERIES[i] for i in range(len(labels))], height=0.55, zorder=3)
    for yi, value in zip(y, values):
        ax.text(value - 2, yi, f"{value:.0f}", ha="right", va="center", color=style.SURFACE, fontsize=10, fontweight="bold")
    handles = []
    for i, (_, label, level) in enumerate(demand):
        color = style.SERIES[3 + (i % 5)]
        ax.axvline(level, color=color, ls="--", lw=1, zorder=2)
        handles.append(Line2D([0], [0], color=color, ls="--", lw=1, label=f"{label} ({level:.0f})"))
    ax.legend(
        handles=handles, loc="upper center", bbox_to_anchor=(0.55, -0.18),
        ncol=3, frameon=False, fontsize=8,
    )
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Orders per day")
    ax.set_xlim(0, 230)
    ax.set_title("Break-even versus what the branches already do")
    ax.tick_params(axis="y", colors=style.INK)
    fig.text(
        0.01, 0.01,
        "ESTIMATE bars, at 44 trading days. Dashed lines are MEASURED branch orders/day. 200 and 300 are off this scale on purpose.",
        color=style.MUTED, fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.subplots_adjust(bottom=0.28)
    fig.savefig(FIGS / "truck_breakeven.png")
    plt.close(fig)


def orders_for_payback(option: str, days: int, profit_per_order: float) -> float:
    """Orders/day that pay the upfront back in PAYBACK_LIMIT_YEARS, cash, travel off."""
    daily = daily_operating_cost(option, False)
    cash_fixed = annual_cash_fixed(option)
    need = upfront_cost(option) / PAYBACK_LIMIT_YEARS
    # (orders * ppo - daily) * days - cash_fixed >= need
    per_day = (need + cash_fixed) / days + daily
    return per_day / profit_per_order


def print_summary(grid: pd.DataFrame, profit_per_order: float, demand: list[tuple[str, str, float]]) -> None:
    base = grid[(~grid["travel_day"]) & (grid["days_per_year"] == CHART_DAYS)]
    print(f"At {CHART_DAYS} trading days, travel day off:")
    for _, label, orders in demand:
        print(f"  {label}: {orders:.1f} orders/day (MEASURED)")
        for key, name in OPTIONS:
            row = base[(base["option"] == key) & (base["orders_label"] == label)].iloc[0]
            pay = "no payback" if not np.isfinite(row.payback_years) else f"{row.payback_years:.2f} years"
            print(f"    {name}: net ${row.net_profit:,.0f}  cash ${row.cash_profit:,.0f}  payback {pay}")
    print("Break-even orders/day at 44 days:")
    for key, name in OPTIONS:
        row = base[base["option"] == key].iloc[0]
        print(f"  {name}: {row.breakeven_orders_per_day:.1f}")
    for key, name in OPTIONS:
        level = orders_for_payback(key, CHART_DAYS, profit_per_order)
        print(f"2-year cash payback for {name} at {CHART_DAYS} days: {level:.0f} orders/day")
    print("Realistic levels that pay back within 2 years (travel off):")
    hit = grid[(~grid["travel_day"]) & (grid["demand_kind"] == "MEASURED") & (grid["within_2_years"])]
    if hit.empty:
        print("  None.")
    else:
        for row in hit.itertuples():
            print(f"  {row.option_label} | {row.orders_label} {row.orders_per_day:.0f}/day | {row.days_per_year:.0f} days | {row.payback_years:.2f} years")


def main() -> None:
    if not SUMMARY.exists():
        raise SystemExit("Missing truck_menu_summary.csv. Run python truck/truck_menu.py first.")
    df = load_clean()
    _ = (GP, REV)  # required import; revenue and profit per order come from the menu summary
    ticket, profit_per_order = load_unit_economics()
    demand = measured_demand(df)
    levels = scenario_orders(demand)
    grid = build_grid(profit_per_order, ticket, levels)
    breaks = breakeven_table(grid)
    TABLES.mkdir(parents=True, exist_ok=True)
    FIGS.mkdir(parents=True, exist_ok=True)
    grid.to_csv(TABLES / "truck_scenarios.csv", index=False, float_format="%.4f")
    breaks.to_csv(TABLES / "truck_breakeven.csv", index=False, float_format="%.4f")
    plot_profit_per_day(profit_per_order, demand)
    plot_payback(grid)
    plot_breakeven(breaks, demand)
    print_summary(grid, profit_per_order, demand)
    print("Saved -> outputs/tables/truck_scenarios.csv")
    print("Saved -> outputs/tables/truck_breakeven.csv")
    print("Saved -> outputs/figures/truck_profit_per_day.png")
    print("Saved -> outputs/figures/truck_payback.png")
    print("Saved -> outputs/figures/truck_breakeven.png")


if __name__ == "__main__":
    main()
