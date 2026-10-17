"""Mornings at Stories: how idle are they, and who buys? (all MEASURED)

Outputs
  outputs/tables/morning_orders_per_hour.csv   orders per hour by branch, hour, weekday/weekend
  outputs/tables/morning_facts.csv             the facts the morning offer rests on
  outputs/figures/morning_idle_hours.png       weekday orders per hour by branch

Run from the repo root:  python morning/morning_demand.py
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
BRANCHES = ["Garden", "Harbour", "Uptown"]
DRINKS = {"Hot Coffee", "Cold Coffee", "Matcha & Tea", "Cold Drinks"}


def add_parts(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["daypart"] = pd.cut(df.hour, [6, 10, 18, 24], labels=["morning", "day", "night"]).astype(str)
    df["weekend"] = df.Date.dt.dayofweek >= 5
    return df


def orders(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby("Transaction ID").agg(
        Date=("Date", "first"), branch=("Branch", "first"), hour=("hour", "first"),
        daypart=("daypart", "first"), weekend=("weekend", "first"),
        order_type=("Order Type", "first"), customer=("Customer ID", "first"),
        lines=("Product", "size"), gp=(GP, "sum"), rev=(REV, "sum"),
        cats=("Category", lambda c: frozenset(c)))


def per_hour(df: pd.DataFrame, tx: pd.DataFrame) -> pd.DataFrame:
    days = df.groupby("weekend").Date.nunique()
    t = tx.groupby(["branch", "weekend", "hour"]).size().rename("orders").reset_index()
    t["orders_per_hour"] = t.orders / t.weekend.map(days)
    t["day_type"] = np.where(t.weekend, "weekend", "weekday")
    return t.drop(columns="weekend")


def facts(df: pd.DataFrame, tx: pd.DataFrame, ph: pd.DataFrame) -> pd.DataFrame:
    rows = []

    def add(metric, value, note):
        rows.append({"metric": metric, "value": value, "kind": "MEASURED", "note": note})

    wd = ph[ph.day_type == "weekday"]
    for b in BRANCHES:
        w = wd[wd.branch == b]
        morning = w[w.hour.between(7, 10)].orders_per_hour.mean()
        night = w[w.hour.between(19, 23)].orders_per_hour.mean()
        add(f"{b}: weekday orders/hour 7-10", round(morning, 2), f"vs {night:.2f} at 19-23 ({morning / night:.0%} of night)")
    m = tx[tx.daypart == "morning"]
    add("Morning share of orders", round(len(m) / len(tx) * 100, 1), "% of all orders, 7-10")
    add("Morning share of revenue", round(m.rev.sum() / tx.rev.sum() * 100, 1), "% of revenue")
    share_by_dow = tx.groupby(tx.Date.dt.dayofweek).daypart.apply(lambda x: (x == "morning").mean() * 100)
    add("Morning share, lowest-highest weekday", f"{share_by_dow.min():.1f}-{share_by_dow.max():.1f}",
        "% of a day's orders; same on weekdays and weekends -> no office/workday signal in the data")
    for dp in ("morning", "night"):
        s = df[df.daypart == dp]
        add(f"Hot coffee share of items, {dp}", round((s.Category == "Hot Coffee").mean() * 100, 1), "% of items sold")
        add(f"Takeaway share of orders, {dp}", round((tx[tx.daypart == dp].order_type == "Takeaway").mean() * 100, 1), "%")
    add("Morning takeaway share, weekday vs weekend",
        " vs ".join(f"{v:.1f}" for v in m.groupby("weekend").order_type.apply(lambda x: (x == "Takeaway").mean() * 100)),
        "% (equal -> no office signal)")
    hot = m[m.cats.apply(lambda c: "Hot Coffee" in c)]
    coffee_only = hot[hot.cats.apply(lambda c: c <= DRINKS)]
    add("Morning orders containing hot coffee", len(hot), "orders in 6 months")
    add("...of which drinks only (no food)", round(len(coffee_only) / len(hot) * 100, 1), "% -> the bundle's opening")
    add("Morning profit per order", round(m.gp.mean(), 2), f"vs {tx[tx.daypart == 'night'].gp.mean():.2f} at night")
    mem = tx.dropna(subset=["customer"])
    mv = mem.groupby("customer").daypart.apply(lambda x: (x == "morning").sum())
    add("Members with at least one morning visit", round((mv >= 1).mean() * 100, 1), "% of 3,494 members")
    add("Members with 3+ morning visits", round((mv >= 3).mean() * 100, 1), "% -> mornings are occasional, not a habit")
    return pd.DataFrame(rows)


def plot(ph: pd.DataFrame, path: Path) -> None:
    style.apply()
    wd = ph[ph.day_type == "weekday"]
    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    ax.axvspan(6.5, 10.5, color=style.SERIES[3], alpha=0.12, lw=0)
    ax.text(8.5, wd.orders_per_hour.max() * 1.02, "Morning 7-10: idle hours", ha="center",
            fontsize=9, color=style.INK_2, weight="bold")
    for i, b in enumerate(BRANCHES):
        s = wd[wd.branch == b].sort_values("hour")
        ax.plot(s.hour, s.orders_per_hour, color=style.SERIES[i], lw=2, marker="o", ms=4, label=b)
        last = s.iloc[-3]
        ax.annotate(b, (last.hour, last.orders_per_hour), xytext=(4, 6), textcoords="offset points",
                    fontsize=9, color=style.INK_2)
    ax.set_xticks(range(7, 24, 2), [f"{h}:00" for h in range(7, 24, 2)])
    ax.set_ylim(0, wd.orders_per_hour.max() * 1.12)
    ax.set_ylabel("Orders per hour (weekday average)")
    ax.set_title("Weekday orders per hour: mornings run at about 40% of night", pad=26)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=3, fontsize=9)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    df = add_parts(load_clean())
    tx = orders(df)
    ph = per_hour(df, tx)
    ph.round(3).to_csv(TABLES / "morning_orders_per_hour.csv", index=False)
    f = facts(df, tx, ph)
    f.to_csv(TABLES / "morning_facts.csv", index=False)
    plot(ph, FIGS / "morning_idle_hours.png")
    pd.set_option("display.width", 200)
    print(f.drop(columns="kind").to_string(index=False))


if __name__ == "__main__":
    main()
