"""Can the branches actually supply the morning offer? (MEASURED unless marked)

1. Opening and staffing evidence: is every branch trading from 7:00?
2. Office days: weekdays minus weekday public holidays (HolidayDB 2026, sourced in
   docs/3_morning_sources.md), used to annualize the morning scenarios.
3. Bundle items today, per branch: units per day (all day and 7-10), share of days the
   item is sold in the morning, day-to-day variation (standard deviation).
4. Extra stock the scenarios would need, as a % of today's daily volume of each item.
5. Unit-cost stability: did any item's unit cost change during Jan-Jun?
6. Prep and storage of each bundle item (from how the item is made; not in the data).

Run from the repo root:  python morning/morning_supply.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from src.clean import load_clean  # noqa: E402
from src import style  # noqa: E402

TABLES = ROOT / "outputs" / "morning" / "tables"
FIGS = ROOT / "outputs" / "morning" / "figures"
TABLES.mkdir(parents=True, exist_ok=True)
FIGS.mkdir(parents=True, exist_ok=True)
BRANCHES = ["Garden", "Harbour", "Uptown"]

# Lebanon public holidays Jan-Jun 2026, HolidayDB (https://holidaydb.com/guides/public-holidays/lebanon/2026)
PUBLIC_HOLIDAYS_H1_2026 = pd.to_datetime([
    "2026-01-01", "2026-01-06", "2026-02-09", "2026-02-14", "2026-03-20", "2026-03-21", "2026-03-22",
    "2026-03-23", "2026-03-25", "2026-04-03", "2026-04-05", "2026-04-06", "2026-04-10", "2026-04-12",
    "2026-04-13", "2026-05-01", "2026-05-03", "2026-05-10", "2026-05-25", "2026-05-27", "2026-05-28",
    "2026-06-17", "2026-06-26"])

# The scenario bundle (Quick morning) and the premium one (Office breakfast)
BUNDLE_ITEMS = {"Vanilla Latte": "Quick morning", "Butter Croissant": "Quick morning",
                "Spanish Latte": "Office breakfast", "Egg Sandwich": "Office breakfast"}
PREP = {  # how each item is made and kept (operational knowledge, not in the data)
    "Vanilla Latte": ("espresso bar, made to order", "milk chilled; beans ambient"),
    "Spanish Latte": ("espresso bar, made to order", "milk chilled; beans ambient"),
    "Butter Croissant": ("ready to sell; reheat optional", "ambient, sell same day"),
    "Egg Sandwich": ("assembled to order or pre-made at opening", "chilled, short shelf life"),
}
EXTRA_ORDERS = [2, 5, 10]


def office_days(df: pd.DataFrame) -> dict:
    span = pd.date_range(df.Date.min(), df.Date.max())
    weekdays = span[span.dayofweek < 5]
    hol = PUBLIC_HOLIDAYS_H1_2026[PUBLIC_HOLIDAYS_H1_2026.dayofweek < 5]
    od = len(weekdays) - len(set(hol) & set(weekdays))
    return {"weekdays_jan_jun": len(weekdays), "weekday_public_holidays": len(set(hol) & set(weekdays)),
            "office_days_jan_jun": od, "office_days_per_year": od * 2}


def opening(df: pd.DataFrame) -> pd.DataFrame:
    tx = df.groupby("Transaction ID").agg(Date=("Date", "first"), branch=("Branch", "first"), t=("Time", "first"))
    tx["minutes"] = pd.to_timedelta(tx.t).dt.total_seconds() / 60
    first = tx.groupby(["branch", "Date"]).minutes.min()
    days = df.Date.nunique()
    rows = []
    for b in BRANCHES:
        f = first.loc[b]
        rows.append({"branch": b, "days_trading": f.size, "days_in_period": days,
                     "earliest_first_order": f"{int(f.min() // 60):02d}:{int(f.min() % 60):02d}",
                     "median_first_order": f"{int(f.median() // 60):02d}:{int(f.median() % 60):02d}",
                     "days_first_order_before_8am_pct": round((f < 480).mean() * 100, 1)})
    return pd.DataFrame(rows)


def stock(df: pd.DataFrame) -> pd.DataFrame:
    span = pd.date_range(df.Date.min(), df.Date.max())
    days = len(span)
    rows = []
    for b in BRANCHES:
        s = df[(df.Branch == b) & df.Product.isin(BUNDLE_ITEMS)]
        daily = s.groupby(["Date", "Product"]).Quantity.sum().unstack().reindex(span).fillna(0)
        morning = s[s.hour.between(7, 10)]
        mdaily = morning.groupby(["Date", "Product"]).Quantity.sum().unstack().reindex(span).fillna(0)
        for p in BUNDLE_ITEMS:
            mean, sd = daily[p].mean(), daily[p].std()
            row = {"branch": b, "item": p, "bundle": BUNDLE_ITEMS[p],
                   "units_per_day_all_day": round(mean, 2), "units_per_day_7_10": round(mdaily[p].mean(), 2),
                   "days_sold_7_10_pct": round((mdaily[p] > 0).mean() * 100, 1),
                   "daily_sd": round(sd, 2), "prep": PREP[p][0], "storage": PREP[p][1]}
            for e in EXTRA_ORDERS:
                row[f"extra_units_if_+{e}_bundles"] = e
                row[f"stock_increase_if_+{e}_pct"] = round(e / mean * 100) if mean else None
                row[f"+{e}_vs_daily_swing"] = round(e / sd, 1) if sd else None
            rows.append(row)
        # Flexible bundles: "hot coffee + any pastry" spreads the extra units over a whole category
        for label, cats in [("Any hot coffee", ["Hot Coffee"]), ("Any bakery item", ["Bakery"])]:
            c = df[(df.Branch == b) & df.Category.isin(cats)]
            daily_c = c.groupby("Date").Quantity.sum().reindex(span).fillna(0)
            mc = c[c.hour.between(7, 10)].groupby("Date").Quantity.sum().reindex(span).fillna(0)
            row = {"branch": b, "item": label, "bundle": "Flexible: coffee + any pastry",
                   "units_per_day_all_day": round(daily_c.mean(), 2), "units_per_day_7_10": round(mc.mean(), 2),
                   "days_sold_7_10_pct": round((mc > 0).mean() * 100, 1), "daily_sd": round(daily_c.std(), 2),
                   "prep": "category total", "storage": "category total"}
            for e in EXTRA_ORDERS:
                row[f"extra_units_if_+{e}_bundles"] = e
                row[f"stock_increase_if_+{e}_pct"] = round(e / daily_c.mean() * 100)
                row[f"+{e}_vs_daily_swing"] = round(e / daily_c.std(), 1)
            rows.append(row)
    return pd.DataFrame(rows)


def cost_stability(df: pd.DataFrame) -> pd.DataFrame:
    df = df.assign(month=df.Date.dt.month)
    n = df.groupby(["Branch", "Product"])["Unit Cost (USD)"].nunique()
    m = df.groupby(["Branch", "Product", "month"])["Unit Cost (USD)"].mean().unstack()
    return pd.DataFrame([{"branch_item_pairs": len(n), "pairs_with_one_unit_cost_all_period": int((n == 1).sum()),
                          "max_month_to_month_cost_change_pct": round(float((m.pct_change(axis=1).abs().max().max() or 0) * 100), 2)}])


def plot(st: pd.DataFrame, path: Path) -> None:
    style.apply()
    q = st
    fig, ax = plt.subplots(figsize=(9.5, 4.4))
    items = ["Butter Croissant", "Any bakery item"]
    x = np.arange(len(BRANCHES))
    w = 0.2
    for j, it in enumerate(items):
        r = q[q.item == it].set_index("branch").loc[BRANCHES]
        now = ax.bar(x + (j * 2 - 1.5) * w, r.units_per_day_all_day, w, color=style.SERIES[j],
                     edgecolor=style.SURFACE, linewidth=2, label=f"{it}: per day today")
        add = ax.bar(x + (j * 2 - 0.5) * w, r.units_per_day_all_day + 5, w, color=style.SERIES[j], alpha=0.45,
                     edgecolor=style.SURFACE, linewidth=2, label=f"{it}: with +5 bundles a day")
        for bar, pct in zip(add, r["stock_increase_if_+5_pct"]):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.15, f"+{pct:.0f}%",
                    ha="center", fontsize=8.5, color=style.INK_2, weight="bold")
    ax.set_xticks(x, BRANCHES)
    ax.set_ylabel("Units per day per branch")
    ax.set_title("+5 bundles a day: a fixed croissant bundle strains stock; 'any pastry' spreads it", pad=40)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, fontsize=8.5)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    df = load_clean()
    od = office_days(df)
    pd.DataFrame([od]).to_csv(TABLES / "morning_office_days.csv", index=False)
    op = opening(df)
    op.to_csv(TABLES / "morning_opening_evidence.csv", index=False)
    st = stock(df)
    st.to_csv(TABLES / "morning_supply_check.csv", index=False)
    cs = cost_stability(df)
    cs.to_csv(TABLES / "morning_cost_stability.csv", index=False)
    plot(st, FIGS / "morning_supply_check.png")
    pd.set_option("display.width", 240)
    print(od, "\n")
    print(op.to_string(index=False), "\n")
    print(st.drop(columns=["prep", "storage"]).to_string(index=False), "\n")
    print(cs.to_string(index=False))


if __name__ == "__main__":
    main()
