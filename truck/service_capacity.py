"""Can two people serve the truck targets, and what a high permit does.

Hourly rates are measured from the branches. Multiplying by an 8-hour shift
is an assumption. The permit stress uses the top of the Zion range already
cited in docs/truck_sources.md.

Run from the repo root, after truck/truck_menu.py:
    python truck/service_capacity.py
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

sys.path.insert(0, str(ROOT / "truck"))
import truck_model as model  # noqa: E402

TABLES = ROOT / "outputs" / "tables"
FIGS = ROOT / "outputs" / "figures"

# ASSUMPTION - verify locally. A truck shift, not a branch's open hours.
TRUCK_OPEN_HOURS = 8
# Zion permits run from about $800 to $17k+. The model uses the floor.
PERMIT_HIGH = 17_000


def hourly(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work["hour"] = work["Time"].str[:2].astype(int)
    return (
        work.groupby(["Date", "Branch", "hour"])["Transaction ID"]
        .nunique()
        .rename("orders")
        .reset_index()
    )


def capacity_rows(df: pd.DataFrame, profit_per_order: float) -> pd.DataFrame:
    hours = hourly(df)
    harbour = hours[hours["Branch"] == "Harbour"]
    peak = harbour.groupby("Date")["orders"].max()
    open_hours = harbour.groupby("Date")["hour"].nunique()
    harbour_day = (
        df[df["Branch"] == "Harbour"].groupby("Date")["Transaction ID"].nunique()
    )
    pace = float(harbour_day.mean() / open_hours.mean())
    typical_peak = float(peak.median())
    record_peak = float(hours["orders"].max())
    record_where = hours.loc[hours["orders"].idxmax()]

    rent_be = (model.daily_operating_cost("rent") ) / profit_per_order
    buy_orders = model.orders_for_payback("buy_used", model.CHART_DAYS, profit_per_order)

    def day(rate: float) -> float:
        return rate * TRUCK_OPEN_HOURS

    rows = [
        ("harbour_orders_per_open_hour", pace, "MEASURED",
         "Harbour's average orders per day divided by the hours that had at least one order."),
        ("harbour_typical_peak_hour", typical_peak, "MEASURED",
         "Median of Harbour's busiest hour each day."),
        ("chain_record_hour", record_peak, "MEASURED",
         f"{record_where.Date.date()} {record_where.Branch} hour {int(record_where.hour)}."),
        ("eight_hours_at_harbour_pace", day(pace), "ESTIMATE",
         f"ASSUMPTION: a {TRUCK_OPEN_HOURS:.0f}-hour shift at Harbour's average pace."),
        ("eight_hours_at_typical_peak", day(typical_peak), "ESTIMATE",
         f"ASSUMPTION: the typical Harbour peak hour, held for all {TRUCK_OPEN_HOURS:.0f} hours."),
        ("eight_hours_at_record_hour", day(record_peak), "ESTIMATE",
         f"ASSUMPTION: the record hour, held for all {TRUCK_OPEN_HOURS:.0f} hours. A ceiling, not a plan."),
        ("rent_breakeven_orders_per_day", rent_be, "ESTIMATE",
         "From truck_model.py. Daily rent cost / product profit per order."),
        ("buy_used_two_year_orders_per_day", buy_orders, "ESTIMATE",
         f"Orders/day that repay a used trailer in {model.PAYBACK_LIMIT_YEARS:.0f} years over {model.CHART_DAYS} days."),
    ]
    return pd.DataFrame(rows, columns=["metric", "value", "kind", "note"])


def permit_rows(profit_per_order: float) -> pd.DataFrame:
    """Same cash profit, higher upfront. Depreciation uses the new upfront."""
    base_upfront = model.upfront_cost("buy_used")
    high_upfront = base_upfront - model.PERMITS + PERMIT_HIGH
    demand = {key: orders for key, _, orders in model.measured_demand(load_clean())}
    rows = []
    for name, upfront in (("permit_floor_800", base_upfront), ("permit_ceiling_17000", high_upfront)):
        for label, orders in (("harbour_avg", demand["harbour_avg"]), ("best_branch_day", demand["best_branch_day"])):
            days = model.CHART_DAYS
            product = orders * profit_per_order * days
            cash_fixed = model.annual_cash_fixed("buy_used")
            daily = model.daily_operating_cost("buy_used")
            cash = product - daily * days - cash_fixed
            payback = upfront / cash if cash > 0 else np.inf
            rows.append({
                "case": name,
                "demand": label,
                "orders_per_day": orders,
                "upfront": upfront,
                "cash_profit_44_days": cash,
                "payback_years": payback,
                "kind": "ESTIMATE",
                "note": "Zion permit range is about $800 to $17k+. Lebanon is still ASSUMPTION - verify locally.",
            })
    return pd.DataFrame(rows)


def plot(table: pd.DataFrame) -> None:
    """Orders a day the shift can hold, against the rent and buy tests."""
    style.apply()
    keep = [
        ("eight_hours_at_harbour_pace", "8h at Harbour's\naverage pace"),
        ("rent_breakeven_orders_per_day", "Rent\nbreak-even"),
        ("eight_hours_at_typical_peak", "8h at Harbour's\ntypical peak hour"),
        ("buy_used_two_year_orders_per_day", "Buy-used\n2-year test"),
        ("eight_hours_at_record_hour", "8h at the\nrecord hour"),
    ]
    values = [float(table.set_index("metric").loc[key, "value"]) for key, _ in keep]
    labels = [label for _, label in keep]
    colors = [style.SERIES[0], style.SERIES[1], style.SERIES[0], style.SERIES[1], style.SERIES[0]]
    fig, ax = plt.subplots(figsize=(9.6, 5.4))
    x = np.arange(len(values))
    bars = ax.bar(x, values, color=colors, width=0.72, zorder=3)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 6, f"{value:.0f}", ha="center", va="bottom", fontsize=9, color=style.INK)
    ax.set_ylim(0, max(values) * 1.18)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Orders per day")
    ax.set_title("Harbour's pace over 8 hours, versus the truck tests")
    fig.text(
        0.01, 0.01,
        "Blue bars: measured hourly rate x an assumed 8-hour shift. Orange bars: estimated decision tests.",
        color=style.MUTED, fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(FIGS / "truck_capacity.png")
    plt.close(fig)


def main() -> None:
    df = load_clean()
    _ = (GP, REV)
    _, profit_per_order = model.load_unit_economics()
    table = capacity_rows(df, profit_per_order)
    permits = permit_rows(profit_per_order)
    TABLES.mkdir(parents=True, exist_ok=True)
    FIGS.mkdir(parents=True, exist_ok=True)
    table.to_csv(TABLES / "truck_capacity.csv", index=False, float_format="%.4f")
    permits.to_csv(TABLES / "truck_permit_stress.csv", index=False, float_format="%.4f")
    plot(table)
    print("Capacity")
    for row in table.itertuples():
        print(f"  {row.metric}: {row.value:.1f} ({row.kind})")
    print("Permit stress, buy used, 44 days")
    for row in permits.itertuples():
        pay = "no payback" if not np.isfinite(row.payback_years) else f"{row.payback_years:.2f} years"
        print(f"  {row.case} | {row.demand}: upfront ${row.upfront:,.0f} cash ${row.cash_profit_44_days:,.0f} payback {pay}")
    print("Saved -> outputs/tables/truck_capacity.csv")
    print("Saved -> outputs/tables/truck_permit_stress.csv")
    print("Saved -> outputs/figures/truck_capacity.png")


if __name__ == "__main__":
    main()
