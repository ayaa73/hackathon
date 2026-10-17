"""What the Eid al-Fitr gap is made of: orders, basket, or missing names.

Same local baseline as holiday_dips.py: same weekday within +/- 21 days,
excluding the Fitr dates themselves.

Run from the repo root:
    python truck/dip_mechanism.py
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

TABLES = ROOT / "outputs" / "tables"
FIGS = ROOT / "outputs" / "figures"

WINDOW_DAYS = 21
FITR = pd.date_range("2026-03-20", "2026-03-23")
# The Friday-to-Monday inside the same window, used only for the named-customer check.
COMPARE = pd.date_range("2026-03-06", "2026-03-09")


def local_mean(daily: pd.DataFrame, day: pd.Timestamp, column: str, exclude: set) -> float:
    start = day - pd.Timedelta(days=WINDOW_DAYS)
    end = day + pd.Timedelta(days=WINDOW_DAYS)
    window = daily[(daily.index >= start) & (daily.index <= end)]
    window = window[window.index.dayofweek == day.dayofweek]
    window = window[~window.index.isin(exclude)]
    return float(window[column].mean())


def return_rate(df: pd.DataFrame, event: pd.DatetimeIndex) -> tuple[float, int, int]:
    """Share of identified customers from the prior 21 days who appear on `event`."""
    named = df[df["Customer ID"].notna()]
    start = event.min() - pd.Timedelta(days=WINDOW_DAYS)
    prior = named[(named["Date"] >= start) & (named["Date"] < event.min())]
    prior_ids = set(prior["Customer ID"])
    event_ids = set(named.loc[named["Date"].isin(event), "Customer ID"])
    if not prior_ids:
        return np.nan, 0, 0
    return len(prior_ids & event_ids) / len(prior_ids), len(prior_ids), len(prior_ids & event_ids)


def main() -> None:
    df = load_clean()
    daily = df.groupby("Date").agg(
        orders=("Transaction ID", "nunique"),
        items=("Quantity", "sum"),
        revenue=(REV, "sum"),
        gross_profit=(GP, "sum"),
    )
    exclude = set(FITR)
    actual_orders = float(daily.loc[FITR, "orders"].sum())
    actual_items = float(daily.loc[FITR, "items"].sum())
    actual_rev = float(daily.loc[FITR, "revenue"].sum())
    expected_orders = sum(local_mean(daily, day, "orders", exclude) for day in FITR)
    expected_items = sum(local_mean(daily, day, "items", exclude) for day in FITR)
    expected_rev = sum(local_mean(daily, day, "revenue", exclude) for day in FITR)

    actual_ticket = actual_rev / actual_orders
    expected_ticket = expected_rev / expected_orders
    actual_ipo = actual_items / actual_orders
    expected_ipo = expected_items / expected_orders

    fitr_rate, fitr_prior, fitr_back = return_rate(df, FITR)
    compare_rate, compare_prior, compare_back = return_rate(df, COMPARE)
    unnamed_share = float(df["Customer ID"].isna().mean())

    rows = [
        ("orders", actual_orders, expected_orders, "MEASURED", "Count of transactions."),
        ("items", actual_items, expected_items, "MEASURED", "Sum of quantity."),
        ("revenue", actual_rev, expected_rev, "MEASURED", "Sum of line revenue."),
        ("ticket_per_order", actual_ticket, expected_ticket, "MEASURED", "Revenue / orders. The basket price."),
        ("items_per_order", actual_ipo, expected_ipo, "MEASURED", "Items / orders. The basket size."),
        ("named_customer_return_fitr", fitr_rate, np.nan, "MEASURED",
         f"{fitr_back:.0f} of {fitr_prior:.0f} identified customers from the prior 21 days also bought on Fitr."),
        ("named_customer_return_6_9_mar", compare_rate, np.nan, "MEASURED",
         f"{compare_back:.0f} of {compare_prior:.0f} identified customers from the prior 21 days also bought on 6-9 Mar, a normal Fri-Mon."),
        ("rows_with_no_customer_id", unnamed_share, np.nan, "MEASURED",
         "Share of lines with a blank customer id. The return rates cover the rest only."),
    ]
    table = pd.DataFrame(rows, columns=["metric", "actual", "expected", "kind", "note"])
    table["gap"] = table["actual"] - table["expected"]
    table["gap_pct"] = table["gap"] / table["expected"] * 100

    TABLES.mkdir(parents=True, exist_ok=True)
    FIGS.mkdir(parents=True, exist_ok=True)
    table.to_csv(TABLES / "eid_dip_mechanism.csv", index=False, float_format="%.4f")
    plot(table)

    print("Eid al-Fitr vs the local same-weekday baseline")
    for row in table.itertuples():
        if pd.notna(row.gap_pct):
            print(f"  {row.metric}: actual {row.actual:.2f} expected {row.expected:.2f} gap {row.gap_pct:.1f}%")
        else:
            print(f"  {row.metric}: {row.actual:.3f}  {row.note}")
    print("Saved -> outputs/tables/eid_dip_mechanism.csv")
    print("Saved -> outputs/figures/eid_dip_mechanism.png")


def plot(table: pd.DataFrame) -> None:
    """Percent gap for the basket pieces. One axis."""
    style.apply()
    keep = ["orders", "items", "revenue", "ticket_per_order", "items_per_order"]
    labels = {
        "orders": "Orders",
        "items": "Items",
        "revenue": "Revenue",
        "ticket_per_order": "Ticket",
        "items_per_order": "Items per order",
    }
    part = table.set_index("metric").loc[keep]
    fig, ax = plt.subplots(figsize=(9.2, 5.2))
    y = np.arange(len(part))
    values = part["gap_pct"].to_numpy()
    colors = [style.SERIES[1] if value < 0 else style.SERIES[2] for value in values]
    ax.barh(y, values, color=colors, height=0.62, zorder=3)
    span = max(abs(values.min()), abs(values.max()), 5)
    ax.set_xlim(-span * 1.55, span * 0.85)
    for yi, value in zip(y, values):
        ax.text(value - 0.4, yi, f"{value:.1f}%", ha="right", va="center", fontsize=9, color=style.INK)
    ax.axvline(0, color=style.INK, lw=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels([labels[name] for name in keep])
    ax.set_xlabel("Eid al-Fitr vs the local same-weekday baseline (%)")
    ax.set_title("The Fitr gap is missing orders")
    ax.tick_params(axis="y", colors=style.INK)
    fig.text(
        0.01, 0.01,
        "MEASURED. Ticket and items per order barely move. The revenue gap is fewer transactions.",
        color=style.MUTED, fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(FIGS / "eid_dip_mechanism.png")
    plt.close(fig)


if __name__ == "__main__":
    main()
