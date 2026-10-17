"""The morning offer: office bundles, breakfast board, delivery vs loyalty card.

1. Morning menu matrix (7-10) picks the bundle items: morning Stars + the most popular
   morning pastry (menu-engineering rule: pair a Star with a popular item).
2. Bundle prices and profit per branch (10% bundle discount, measured unit costs).
3. Upsell ceiling: how much the bundle earns from EXISTING coffee-only morning orders.
4. Channel economics per order: walk-in with a loyalty card vs delivery (first 3 free)
   and the share of orders that must be NEW for each channel to pay.
5. Scenarios: extra bundle orders per branch per weekday, yearly gross profit, and a
   capacity check against each branch's own night peak.
6. Test design checked on history: before/after on the morning share of orders,
   placebo false alarms and the smallest effect detectable.

Everything not computed from the data is an ASSUMPTION at the top of this file.

Run from the repo root (after morning_demand.py):  python morning/morning_offer.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from scipy import stats  # noqa: E402

from src.clean import GP, load_clean  # noqa: E402
from src import style  # noqa: E402
from menu_engineering.menu_matrix import classify  # noqa: E402
from morning.morning_demand import BRANCHES, DRINKS, add_parts, orders  # noqa: E402

TABLES = ROOT / "outputs" / "tables"
FIGS = ROOT / "outputs" / "figures"

# ---- Assumptions (verify locally) ------------------------------------------------
BUNDLE_DISCOUNT = 0.10           # bundle priced 10% below buying the items separately
WEEKDAYS_PER_YEAR = 255          # Mon-Fri minus ~5 public holidays (office days)
DELIVERY_COST = 2.00             # USD Stories pays a rider/aggregator per delivery
FREE_DELIVERIES_PER_NEW_CUSTOMER = 3
LOYALTY_EVERY_N = 6              # loyalty card: 6th morning bundle free
INCREMENTAL_SHARE = 0.70         # share of offer orders that are genuinely new (scenarios)
EXTRA_ORDERS_PER_BRANCH_DAY = [5, 10, 20]
UPSELL_CONVERSION = [0.10, 0.20, 0.30]
BUNDLES = {
    "Quick morning": ["Vanilla Latte", "Butter Croissant"],
    "Office breakfast": ["Spanish Latte", "Egg Sandwich"],
    "Office pack (4+4)": ["Cappuccino", "Flat White", "Vanilla Latte", "Spanish Latte",
                          "Butter Croissant", "Butter Croissant", "Chocolate Croissant", "Cinnamon Roll"],
}


def morning_matrix(df: pd.DataFrame) -> pd.DataFrame:
    p, th = classify(df[df.daypart == "morning"])
    p = p[p.Category.isin(["Hot Coffee", "Bakery", "Breakfast"])]
    p = p[["Product", "Category", "class", "units", "profit_per_unit", "popularity_share_pct"]]
    p["morning_avg_profit_per_unit"] = round(th["profit_threshold_usd"], 2)
    return p.sort_values(["Category", "units"], ascending=[True, False])


def bundle_table(df: pd.DataFrame) -> pd.DataFrame:
    price = df.groupby(["Branch", "Product"])["Unit Price (USD)"].mean()
    cost = df.groupby(["Branch", "Product"])["Unit Cost (USD)"].mean()
    rows = []
    for b in BRANCHES:
        for name, items in BUNDLES.items():
            sep = sum(price[(b, i)] for i in items)
            c = sum(cost[(b, i)] for i in items)
            bp = sep * (1 - BUNDLE_DISCOUNT)
            rows.append({"branch": b, "bundle": name, "items": " + ".join(items),
                         "price_separate": round(sep, 2), "bundle_price": round(bp, 2),
                         "bundle_cost": round(c, 2), "bundle_profit": round(bp - c, 2),
                         "margin_pct": round((bp - c) / bp * 100, 1)})
    return pd.DataFrame(rows)


def upsell_ceiling(df: pd.DataFrame, tx: pd.DataFrame, bundles: pd.DataFrame) -> pd.DataFrame:
    m = tx[tx.daypart == "morning"]
    coffee_only = m[m.cats.apply(lambda c: "Hot Coffee" in c and c <= DRINKS)]
    quick = bundles[bundles.bundle == "Quick morning"].set_index("branch")
    price = df.groupby(["Branch", "Product"])["Unit Price (USD)"].mean()
    cost = df.groupby(["Branch", "Product"])["Unit Cost (USD)"].mean()
    rows = []
    for conv in UPSELL_CONVERSION:
        gain = 0.0
        for b in BRANCHES:
            n = (coffee_only.branch == b).sum()
            # customer already buys the coffee; the bundle adds a croissant at 10% off both items
            extra = quick.loc[b, "bundle_profit"] - (price[(b, "Vanilla Latte")] - cost[(b, "Vanilla Latte")])
            gain += n * conv * extra
        rows.append({"conversion": conv, "coffee_only_morning_orders_6mo": len(coffee_only),
                     "extra_gross_profit_per_year": round(gain * 2)})
    return pd.DataFrame(rows)


def channel_economics(bundles: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for name, g in bundles.groupby("bundle", sort=False):
        profit = g.bundle_profit.mean()
        cost = g.bundle_cost.mean()
        loyalty_cost = cost / LOYALTY_EVERY_N
        for channel, per_order_cost in [("Walk-in + loyalty card (6th free)", loyalty_cost),
                                        (f"Delivery, first {FREE_DELIVERIES_PER_NEW_CUSTOMER} free", DELIVERY_COST),
                                        ("Delivery, customer pays the fee", 0.0)]:
            rows.append({"bundle": name, "channel": channel, "bundle_profit": round(profit, 2),
                         "channel_cost_per_order": round(per_order_cost, 2),
                         "net_profit_per_new_order": round(profit - per_order_cost, 2),
                         "min_share_of_orders_that_must_be_new_pct":
                             round(per_order_cost / profit * 100, 1) if profit > 0 else None})
    return pd.DataFrame(rows)


def scenarios(bundles: pd.DataFrame, tx: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
    quick = bundles[bundles.bundle == "Quick morning"].set_index("branch").bundle_profit
    loyalty_cost = bundles[bundles.bundle == "Quick morning"].set_index("branch").bundle_cost / LOYALTY_EVERY_N
    wd = tx[~tx.weekend]
    n_wd = df[~df.weekend].Date.nunique()
    rows = []
    for extra in EXTRA_ORDERS_PER_BRANCH_DAY:
        total = 0.0
        for b in BRANCHES:
            per_order = INCREMENTAL_SHARE * quick[b] - loyalty_cost[b]
            yearly = extra * WEEKDAYS_PER_YEAR * per_order
            total += yearly
            w = wd[wd.branch == b]
            morning_ph = (w.hour.between(7, 10)).sum() / n_wd / 4
            night_ph = (w.hour.between(19, 23)).sum() / n_wd / 5
            rows.append({"extra_bundle_orders_per_branch_per_weekday": extra, "branch": b,
                         "morning_orders_per_hour_now": round(morning_ph, 2),
                         "morning_orders_per_hour_after": round(morning_ph + extra / 4, 2),
                         "night_orders_per_hour_now": round(night_ph, 2),
                         "within_night_capacity": morning_ph + extra / 4 <= night_ph,
                         "gross_profit_per_year_usd": round(yearly)})
        rows.append({"extra_bundle_orders_per_branch_per_weekday": extra, "branch": "ALL",
                     "gross_profit_per_year_usd": round(total)})
    return pd.DataFrame(rows)


def test_design(tx: pd.DataFrame, test_branch: str = "Harbour") -> pd.DataFrame:
    """Weekly morning share at the test branch minus the controls; placebo on history."""
    tx = tx.copy()
    tx["week"] = tx.Date.dt.to_period("W-SUN")
    full = tx.groupby("week").Date.nunique() == 7
    tx = tx[tx.week.map(full)]
    share = tx.groupby(["week", tx.branch == test_branch]).daypart.apply(lambda x: (x == "morning").mean()).unstack()
    gap = (share[True] - share[False]).values * 100  # percentage points
    alarms = n = 0
    for s in range(8, len(gap) - 8 + 1):
        alarms += stats.ttest_ind(gap[s:s + 8], gap[s - 8:s], equal_var=False).pvalue < 0.05
        n += 1
    sd = gap.std(ddof=1)
    trend = np.polyfit(np.arange(len(gap)), gap, 1)[0]
    rows = [{"metric": "weekly morning-share gap SD (pts)", "value": round(sd, 2)},
            {"metric": "trend in gap per week (pts)", "value": round(trend, 3)},
            {"metric": "placebo 8-week before/after tests", "value": n},
            {"metric": "placebo false alarms", "value": int(alarms)},
            {"metric": "false alarm rate %", "value": round(alarms / n * 100, 1)}]
    for w in (8, 12):
        rows.append({"metric": f"smallest detectable change in morning share, {w} weeks vs {w} before (pts)",
                     "value": round(2.8 * sd * np.sqrt(2 / w), 2)})
    rows.append({"metric": f"{test_branch} morning share now (%)",
                 "value": round((tx[tx.branch == test_branch].daypart == "morning").mean() * 100, 1)})
    return pd.DataFrame(rows)


def plot(sc: pd.DataFrame, ch: pd.DataFrame, path: Path) -> None:
    style.apply()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw={"width_ratios": [1, 1.25]})
    tot = sc[sc.branch == "ALL"]
    x = np.arange(len(tot))
    bars = ax1.bar(x, tot.gross_profit_per_year_usd, color=style.SERIES[0], width=0.55,
                   edgecolor=style.SURFACE, linewidth=2)
    for bar, v in zip(bars, tot.gross_profit_per_year_usd):
        ax1.text(bar.get_x() + bar.get_width() / 2, v * 1.02, f"${v:,.0f}", ha="center", va="bottom",
                 fontsize=10, weight="bold", color=style.INK)
    ax1.set_xticks(x, [f"+{e} per branch\nper weekday" for e in tot.extra_bundle_orders_per_branch_per_weekday])
    ax1.set_ylim(0, tot.gross_profit_per_year_usd.max() * 1.18)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v:,.0f}"))
    ax1.set_title("Extra gross profit per year\n(Quick morning bundle, loyalty card)", fontsize=11)
    ax1.grid(axis="x", visible=False)

    q = ch[ch.bundle.isin(["Quick morning", "Office pack (4+4)"])]
    labels = [f"{r.bundle}\n{r.channel}" for _, r in q.iterrows()]
    y = np.arange(len(q))[::-1]
    colors = [style.SERIES[2] if v <= 15 else style.SERIES[1] for v in q.min_share_of_orders_that_must_be_new_pct]
    ax2.barh(y, q.min_share_of_orders_that_must_be_new_pct, color=colors, height=0.6,
             edgecolor=style.SURFACE, linewidth=2)
    for yi, v in zip(y, q.min_share_of_orders_that_must_be_new_pct):
        ax2.text(v + 0.8, yi, f"{v:.0f}%", va="center", fontsize=9, weight="bold", color=style.INK)
    ax2.set_yticks(y, labels, fontsize=8)
    ax2.set_xlim(0, max(q.min_share_of_orders_that_must_be_new_pct.max() * 1.3, 10))
    ax2.set_xlabel("Share of offer orders that must be NEW customers to break even (%)")
    ax2.set_title("Free delivery only pays on big orders", fontsize=11)
    ax2.grid(axis="y", visible=False)
    fig.text(0.01, -0.02, "ESTIMATE. Assumptions at the top of morning/morning_offer.py: 10% bundle discount, "
             f"${DELIVERY_COST:.2f} per delivery, 6th bundle free, {INCREMENTAL_SHARE:.0%} of orders new, "
             f"{WEEKDAYS_PER_YEAR} weekdays.", fontsize=8, color=style.MUTED)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    df = add_parts(load_clean())
    tx = orders(df)

    mm = morning_matrix(df)
    mm.to_csv(TABLES / "morning_menu_matrix.csv", index=False)
    b = bundle_table(df)
    b.to_csv(TABLES / "morning_bundles.csv", index=False)
    up = upsell_ceiling(df, tx, b)
    up.to_csv(TABLES / "morning_upsell_ceiling.csv", index=False)
    ch = channel_economics(b)
    ch.to_csv(TABLES / "morning_channel_economics.csv", index=False)
    sc = scenarios(b, tx, df)
    sc.to_csv(TABLES / "morning_scenarios.csv", index=False)
    td = test_design(tx)
    td.to_csv(TABLES / "morning_test_design.csv", index=False)
    plot(sc, ch, FIGS / "morning_offer_economics.png")

    pd.set_option("display.width", 220)
    print(mm.to_string(index=False), "\n")
    print(b.to_string(index=False), "\n")
    print(up.to_string(index=False), "\n")
    print(ch.to_string(index=False), "\n")
    print(sc.to_string(index=False), "\n")
    print(td.to_string(index=False))


if __name__ == "__main__":
    main()
