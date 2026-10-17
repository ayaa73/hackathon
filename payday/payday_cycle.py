"""The monthly payday cycle in Stories' sales (all MEASURED).

Each day's orders are compared with the average of the same weekday within +/-21 days
(public holidays excluded), so weekday patterns and the steady growth trend cancel out.
Then: is there a day-of-month pattern, is it the same in every month, branch and customer
type, and how much gross profit does the mid-month dip represent?

Outputs
  outputs/tables/payday_by_day_of_month.csv
  outputs/tables/payday_robustness.csv
  outputs/tables/payday_dip_value.csv
  outputs/figures/payday_cycle.png

Run from the repo root:  python payday/payday_cycle.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from scipy import stats  # noqa: E402

from src.clean import GP, REV, load_clean  # noqa: E402
from src import style  # noqa: E402

TABLES = ROOT / "outputs" / "tables"
FIGS = ROOT / "outputs" / "figures"
BRANCHES = ["Garden", "Harbour", "Uptown"]
WINDOW = 21
N_PERM = 5000
# Lebanon public holidays Jan-Jun 2026, HolidayDB (https://holidaydb.com/guides/public-holidays/lebanon/2026)
HOLIDAYS = pd.to_datetime([
    "2026-01-01", "2026-01-06", "2026-02-09", "2026-02-14", "2026-03-20", "2026-03-21", "2026-03-22",
    "2026-03-23", "2026-03-25", "2026-04-03", "2026-04-05", "2026-04-06", "2026-04-10", "2026-04-12",
    "2026-04-13", "2026-05-01", "2026-05-03", "2026-05-10", "2026-05-25", "2026-05-27", "2026-05-28",
    "2026-06-17", "2026-06-26"])
PEAK = "Peak (28th-7th)"
TROUGH = "Dip (14th-27th)"
MID = "8th-13th"


def phase(day: pd.Series) -> np.ndarray:
    return np.select([(day <= 7) | (day >= 28), day.between(14, 27)], [PEAK, TROUGH], MID)


def orders_table(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby("Transaction ID").agg(Date=("Date", "first"), branch=("Branch", "first"),
                                            customer=("Customer ID", "first"), gp=(GP, "sum"), rev=(REV, "sum"))


def daily_deviation(tx: pd.DataFrame, value: str = "orders") -> pd.DataFrame:
    span = pd.date_range(tx.Date.min(), tx.Date.max())
    g = tx.groupby("Date").agg(orders=("gp", "size"), gp=("gp", "sum"), rev=("rev", "sum"))
    g = g.reindex(span).fillna(0)
    g["ticket"] = g.rev / g.orders.replace(0, np.nan)
    g["dow"] = g.index.dayofweek
    g = g[~g.index.isin(HOLIDAYS)].copy()
    exp = []
    for t in g.index:
        ref = g[(abs((g.index - t).days) <= WINDOW) & (g.dow == g.loc[t, "dow"]) & (g.index != t)]
        exp.append(ref[value].mean())
    g["expected"] = exp
    g["dev_pct"] = (g[value] / g.expected - 1) * 100
    g["gap"] = g[value] - g.expected
    g["day"] = g.index.day
    g["phase"] = phase(g.day)
    return g


def perm_p(dev: pd.Series, mask: np.ndarray, rng) -> float:
    obs = dev[mask].mean() - dev[~mask].mean()
    null = np.array([dev.values[p].mean() - dev.values[~p].mean()
                     for p in (rng.permutation(mask) for _ in range(N_PERM))])
    return float(np.mean(np.abs(null) >= abs(obs)))


def main() -> None:
    rng = np.random.default_rng(2026)
    df = load_clean()
    tx = orders_table(df)
    d = daily_deviation(tx)

    by_day = d.groupby("day").agg(orders_vs_normal_pct=("dev_pct", "mean"), days=("dev_pct", "size")).round(2)
    by_day["phase"] = phase(by_day.index.to_series())
    by_day.to_csv(TABLES / "payday_by_day_of_month.csv")

    rows = []
    peak = (d.phase == PEAK).values
    trough = (d.phase == TROUGH).values

    def add(scope, sub, note=""):
        pk, tr = sub[sub.phase == PEAK].dev_pct.mean(), sub[sub.phase == TROUGH].dev_pct.mean()
        rows.append({"scope": scope, "peak_28_7_vs_normal_pct": round(pk, 2), "dip_14_27_vs_normal_pct": round(tr, 2),
                     "peak_minus_dip_pts": round(pk - tr, 2), "note": note})

    add("Chain, all months", d, f"permutation p (peak vs rest) = {perm_p(d.dev_pct, peak, rng):.4f}; "
                                f"(dip vs rest) = {perm_p(d.dev_pct, trough, rng):.4f}")
    for m, sub in d.groupby(d.index.month):
        add(f"Chain, month {m}", sub)
    for b in BRANCHES:
        add(f"Branch {b}", daily_deviation(tx[tx.branch == b]))
    add("Members only", daily_deviation(tx[tx.customer.notna()]))
    add("Walk-ins only", daily_deviation(tx[tx.customer.isna()]))
    kw = stats.kruskal(*[d[d.phase == p].ticket.dropna() for p in (PEAK, MID, TROUGH)]).pvalue
    tk = d.groupby("phase").ticket.mean()
    rows.append({"scope": "Average ticket (USD) by phase", "peak_28_7_vs_normal_pct": round(tk[PEAK], 2),
                 "dip_14_27_vs_normal_pct": round(tk[TROUGH], 2), "peak_minus_dip_pts": None,
                 "note": f"Kruskal-Wallis p = {kw:.2f}: ticket size does not change; the cycle is in visits"})
    rob = pd.DataFrame(rows)
    rob.to_csv(TABLES / "payday_robustness.csv", index=False)

    g = daily_deviation(tx, "gp")
    dip = g[g.phase == TROUGH]
    pk = g[g.phase == PEAK]
    val = pd.DataFrame([{
        "dip_days_in_data": len(dip), "gross_profit_gap_per_dip_day_usd": round(dip.gap.mean(), 1),
        "gross_profit_gap_per_peak_day_usd": round(pk.gap.mean(), 1),
        "dip_gross_profit_gap_6_months_usd": round(dip.gap.sum()),
        "dip_gross_profit_gap_per_year_usd": round(dip.gap.sum() * 2),
        "note": "Gross profit the dip days earn below their normal level (same weekday, +/-21 days). "
                "Ceiling for 'filling the dip'."}])
    val.to_csv(TABLES / "payday_dip_value.csv", index=False)

    style.apply()
    fig, ax = plt.subplots(figsize=(10, 4.4))
    colors = [style.SERIES[0] if p == PEAK else style.SERIES[1] if p == TROUGH else style.MUTED
              for p in by_day.phase]
    ax.bar(by_day.index, by_day.orders_vs_normal_pct, color=colors, width=0.75, edgecolor=style.SURFACE, linewidth=1)
    ax.axhline(0, color=style.INK_2, lw=0.8)
    ax.set_xticks(range(1, 32, 2))
    ax.set_xlabel("Day of the month")
    ax.set_ylabel("Orders vs a normal day (%)")
    ax.set_title("Orders follow the pay cycle: busier from the 28th to the 7th, quieter from the 14th to the 27th", pad=26)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=style.SERIES[0], label=PEAK), Patch(color=style.SERIES[1], label=TROUGH),
                       Patch(color=style.MUTED, label=MID)], loc="lower left", bbox_to_anchor=(0, 1.0), ncol=3, fontsize=9)
    ax.grid(axis="x", visible=False)
    fig.text(0.01, -0.02, "MEASURED. Each day vs the same weekday within +/-21 days, public holidays excluded, "
             "Jan-Jun 2026, all branches.", fontsize=8, color=style.MUTED)
    fig.tight_layout()
    fig.savefig(FIGS / "payday_cycle.png", bbox_inches="tight")
    plt.close(fig)

    pd.set_option("display.width", 220)
    pd.set_option("display.max_colwidth", 120)
    print(rob.to_string(index=False), "\n")
    print(val.drop(columns="note").to_string(index=False))


if __name__ == "__main__":
    main()
