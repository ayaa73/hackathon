"""Holiday revenue gaps against a local same-weekday baseline.

The old case compared each Eid day with that weekday's average over all six
months. Sales rose from January to June, so a late-May day looked "up" against
a baseline dragged down by winter. This script does not do that.

New baseline, for each holiday day: the average of the same weekday inside a
+/- 21 day window, excluding that holiday's own dates. A holiday is not its
own control. Computed from the transaction file. Nothing here is typed in.

Run from the repo root:
    python truck/holiday_dips.py
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

TABLES = ROOT / "outputs" / "truck" / "tables"
FIGS = ROOT / "outputs" / "truck" / "figures"

# Dates only. HolidayDB lists these for 2026. The window length is the method.
WINDOW_DAYS = 21
HOLIDAYS = [
    ("Eid al-Fitr", "2026-03-20", "2026-03-23"),
    ("Easter", "2026-04-03", "2026-04-06"),
    ("Orthodox Easter", "2026-04-10", "2026-04-13"),
    ("Labour Day", "2026-05-01", "2026-05-01"),
    ("Eid al-Adha", "2026-05-27", "2026-05-28"),
]


def holiday_dates() -> dict[str, pd.DatetimeIndex]:
    return {name: pd.date_range(start, end) for name, start, end in HOLIDAYS}


def local_baseline(series: pd.Series, day: pd.Timestamp, exclude: set) -> float:
    """Same weekday within +/- WINDOW_DAYS, excluding `exclude`."""
    start = day - pd.Timedelta(days=WINDOW_DAYS)
    end = day + pd.Timedelta(days=WINDOW_DAYS)
    window = series[(series.index >= start) & (series.index <= end)]
    window = window[window.index.dayofweek == day.dayofweek]
    window = window[~window.index.isin(exclude)]
    if window.empty:
        return np.nan
    return float(window.mean())


def daily(df: pd.DataFrame, branch: str | None) -> tuple[pd.Series, pd.Series]:
    part = df if branch is None else df[df["Branch"] == branch]
    revenue = part.groupby("Date")[REV].sum()
    profit = part.groupby("Date")[GP].sum()
    return revenue, profit


def gaps_for(revenue: pd.Series, profit: pd.Series, branch: str) -> pd.DataFrame:
    rows = []
    for name, days in holiday_dates().items():
        exclude = set(days)
        for day in days:
            actual_rev = float(revenue.get(day, 0.0))
            actual_gp = float(profit.get(day, 0.0))
            expected_rev = local_baseline(revenue, day, exclude)
            expected_gp = local_baseline(profit, day, exclude)
            rows.append({
                "holiday": name,
                "branch": branch,
                "date": day.date().isoformat(),
                "actual_revenue": actual_rev,
                "expected_revenue": expected_rev,
                "revenue_gap": actual_rev - expected_rev,
                "revenue_gap_pct": (actual_rev - expected_rev) / expected_rev * 100,
                "actual_gross_profit": actual_gp,
                "expected_gross_profit": expected_gp,
                "gross_profit_gap": actual_gp - expected_gp,
                "kind": "MEASURED",
                "baseline": f"same weekday within +/- {WINDOW_DAYS} days, excluding this holiday",
            })
    return pd.DataFrame(rows)


def summarise(detail: pd.DataFrame) -> pd.DataFrame:
    """One row per holiday and branch: sums of the daily gaps."""
    rows = []
    for (holiday, branch), part in detail.groupby(["holiday", "branch"], sort=False):
        actual = part["actual_revenue"].sum()
        expected = part["expected_revenue"].sum()
        gap = actual - expected
        rows.append({
            "holiday": holiday,
            "branch": branch,
            "days": len(part),
            "actual_revenue": actual,
            "expected_revenue": expected,
            "revenue_gap": gap,
            "revenue_gap_pct": gap / expected * 100,
            "actual_gross_profit": part["actual_gross_profit"].sum(),
            "expected_gross_profit": part["expected_gross_profit"].sum(),
            "gross_profit_gap": part["gross_profit_gap"].sum(),
            "kind": "MEASURED",
        })
    return pd.DataFrame(rows)


def plot(summary: pd.DataFrame) -> None:
    """Chain % gap by holiday, labelled with the dollar gap. One axis."""
    style.apply()
    chain = summary[summary["branch"] == "Chain"].copy()
    order = [name for name, _, _ in HOLIDAYS]
    chain = chain.set_index("holiday").loc[order]
    fig, ax = plt.subplots(figsize=(9.6, 5.6))
    y = np.arange(len(chain))
    values = chain["revenue_gap_pct"].to_numpy()
    colors = [style.SERIES[1] if value < 0 else style.SERIES[2] for value in values]
    ax.barh(y, values, color=colors, height=0.62, zorder=3)
    span = max(abs(values.min()), abs(values.max()))
    ax.set_xlim(-span * 1.45, span * 1.45)
    for yi, pct, dollars in zip(y, values, chain["revenue_gap"]):
        label = f"${dollars:,.0f}"
        if pct < 0:
            ax.text(pct - span * 0.04, yi, label, ha="right", va="center", fontsize=9, color=style.INK)
        else:
            ax.text(pct + span * 0.04, yi, label, ha="left", va="center", fontsize=9, color=style.INK)
    ax.axvline(0, color=style.INK, lw=0.8, zorder=2)
    ax.set_yticks(y)
    ax.set_yticklabels(order)
    ax.set_xlabel("Revenue vs the local same-weekday baseline (%)")
    ax.set_title("Holiday revenue gap")
    ax.tick_params(axis="y", colors=style.INK)
    fig.text(
        0.01, 0.01,
        "MEASURED. Each day vs the same weekday within +/- 21 days, excluding that holiday. Dollar labels are the revenue gap.",
        color=style.MUTED, fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(FIGS / "eid_holiday_dips.png")
    plt.close(fig)


def main() -> None:
    df = load_clean()
    frames = [gaps_for(*daily(df, None), "Chain")]
    for branch in sorted(df["Branch"].unique()):
        frames.append(gaps_for(*daily(df, branch), branch))
    detail = pd.concat(frames, ignore_index=True)
    summary = summarise(detail)

    monthly = df.groupby(df["Date"].dt.to_period("M"))[REV].sum()
    growth = monthly.iloc[-1] / monthly.iloc[0] - 1
    by_day = df.groupby("Date")[REV].sum().sort_values()
    worst = by_day.head(1)
    fitr_worst_day = pd.Timestamp("2026-03-21")
    fitr_worst = float(by_day.loc[fitr_worst_day])
    fitr_rank = int(by_day.rank(method="min").loc[fitr_worst_day])

    TABLES.mkdir(parents=True, exist_ok=True)
    FIGS.mkdir(parents=True, exist_ok=True)
    # Daily rows plus a TOTAL block so both views are in one file.
    totals = summary.copy()
    totals.insert(2, "date", "TOTAL")
    out = pd.concat([detail, totals], ignore_index=True)
    out.to_csv(TABLES / "eid_holiday_dips.csv", index=False, float_format="%.4f")
    plot(summary)

    print(f"January to June revenue growth: {growth * 100:.1f}%  (MEASURED, {monthly.index[0]} -> {monthly.index[-1]})")
    print(f"Lowest day in the file: {worst.index[0].date()} ${float(worst.iloc[0]):,.0f}  (MEASURED)")
    print(f"Worst Eid al-Fitr day: {fitr_worst_day.date()} ${fitr_worst:,.0f}, rank {fitr_rank} of {len(by_day)}  (MEASURED)")
    print("Chain totals, local same-weekday baseline:")
    chain = summary[summary["branch"] == "Chain"]
    for row in chain.itertuples():
        print(
            f"  {row.holiday}: actual ${row.actual_revenue:,.0f} vs expected ${row.expected_revenue:,.0f}"
            f" -> ${row.revenue_gap:,.0f} ({row.revenue_gap_pct:.1f}%),"
            f" gross-profit gap ${row.gross_profit_gap:,.0f}"
        )
    print("Saved -> outputs/truck/tables/eid_holiday_dips.csv")
    print("Saved -> outputs/truck/figures/eid_holiday_dips.png")


if __name__ == "__main__":
    main()
