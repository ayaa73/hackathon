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

Run from the repo root (after morning_demand.py and morning_supply.py):  python morning/morning_offer.py
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

TABLES = ROOT / "outputs" / "morning" / "tables"
FIGS = ROOT / "outputs" / "morning" / "figures"
TABLES.mkdir(parents=True, exist_ok=True)
FIGS.mkdir(parents=True, exist_ok=True)

# ---- Inputs and assumptions --------------------------------------------------------
# Sources are listed in docs/3_morning_sources.md. DESIGN = a choice we make, not a fact.
BUNDLE_DISCOUNT = 0.10           # DESIGN: bundle 10% below buying the items separately
# Office days per year: MEASURED from the calendar (Mon-Fri minus HolidayDB weekday
# public holidays, Jan-Jun 2026, x2); computed by morning_supply.py.
OFFICE_DAYS_FILE = "morning_office_days.csv"
# Delivery cost per order, SOURCED: courier services such as Wakilni charge restaurants
# "typically 2 to 6 USD per delivery in Beirut" (Voxire, May 2026).
COURIER_COST = {"low": 2.0, "mid": 4.0, "high": 6.0}
# Delivery apps, SOURCED: Toters / Talabat commission 22-30% of order value (Voxire, May 2026).
APP_COMMISSION = {"strong brand": 0.22, "standard": 0.30}
FREE_DELIVERIES_PER_NEW_CUSTOMER = 3   # DESIGN
LOYALTY_EVERY_N = 6              # DESIGN: 6th morning bundle free (a free item is the most common
                                 # reward: 48% of food & drink programs on Square Loyalty)
NEW_CUSTOMER_SHARES = [0.3, 0.5, 0.7]  # ASSUMPTION range: share of offer orders that are new
EXTRA_ORDERS_PER_BRANCH_DAY = [2, 5, 10]  # ASSUMPTION range; +2/day = what the test can detect
UPSELL_CONVERSION = [0.10, 0.20, 0.30]
WORKABLE_NEW_SHARE_PCT = 35      # DESIGN: a channel is "workable" if it pays with 35% new customers or fewer
BUNDLES = {
    "Coffee + any pastry": None,  # flexible: priced at each branch's morning hot-coffee and bakery mix
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
    morning = df[df.daypart == "morning"]
    rows = []
    for b in BRANCHES:
        for name, items in BUNDLES.items():
            if items is None:  # morning-mix-weighted hot coffee + bakery item at this branch
                sep = c = 0.0
                for cat in ("Hot Coffee", "Bakery"):
                    m = morning[(morning.Branch == b) & (morning.Category == cat)]
                    w = m.groupby("Product").Quantity.sum()
                    sep += (price[b].reindex(w.index) * w).sum() / w.sum()
                    c += (cost[b].reindex(w.index) * w).sum() / w.sum()
                items = ["any hot coffee", "any bakery item (weighted by morning sales)"]
            else:
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
        profit, cost, price = g.bundle_profit.mean(), g.bundle_cost.mean(), g.bundle_price.mean()
        channels = [("Walk-in + loyalty card (6th free)", cost / LOYALTY_EVERY_N, "DESIGN; cost = product cost of 1 bundle in 6")]
        for lvl, c in COURIER_COST.items():
            channels.append((f"Own courier, free delivery (${c:.0f}, {lvl})", c, "SOURCED range $2-6 (Voxire)"))
        for lvl, r in APP_COMMISSION.items():
            channels.append((f"Delivery app commission {r:.0%} ({lvl})", price * r, "SOURCED 22-30% (Voxire)"))
        for channel, per_order_cost, basis in channels:
            rows.append({"bundle": name, "channel": channel, "basis": basis,
                         "bundle_price": round(price, 2), "bundle_profit": round(profit, 2),
                         "channel_cost_per_order": round(per_order_cost, 2),
                         "net_profit_per_new_order": round(profit - per_order_cost, 2),
                         "min_share_of_orders_that_must_be_new_pct":
                             round(per_order_cost / profit * 100, 1) if profit > 0 else None})
    return pd.DataFrame(rows)


def scenarios(bundles: pd.DataFrame, tx: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
    office_days = int(pd.read_csv(TABLES / OFFICE_DAYS_FILE).office_days_per_year.iloc[0])
    flex = bundles[bundles.bundle == "Coffee + any pastry"].set_index("branch")
    wd = tx[~tx.weekend]
    n_wd = df[~df.weekend].Date.nunique()
    rows = []
    for new_share in NEW_CUSTOMER_SHARES:
        for extra in EXTRA_ORDERS_PER_BRANCH_DAY:
            total = 0.0
            for b in BRANCHES:
                # every offer order pays the loyalty cost; only the new share adds profit
                per_order = new_share * flex.loc[b, "bundle_profit"] - flex.loc[b, "bundle_cost"] / LOYALTY_EVERY_N
                yearly = extra * office_days * per_order
                total += yearly
                w = wd[wd.branch == b]
                morning_ph = w.hour.between(7, 10).sum() / n_wd / 4
                night_ph = w.hour.between(19, 23).sum() / n_wd / 5
                rows.append({"new_customer_share": new_share, "extra_orders_per_branch_per_office_day": extra,
                             "branch": b, "office_days_per_year": office_days,
                             "morning_orders_per_day_now": round(morning_ph * 4, 1),
                             "morning_orders_increase_pct": round(extra / (morning_ph * 4) * 100),
                             "morning_orders_per_hour_after": round(morning_ph + extra / 4, 2),
                             "night_orders_per_hour_now": round(night_ph, 2),
                             "within_night_pace": morning_ph + extra / 4 <= night_ph,
                             "gross_profit_per_year_usd": round(yearly)})
            rows.append({"new_customer_share": new_share, "extra_orders_per_branch_per_office_day": extra,
                         "branch": "ALL", "office_days_per_year": office_days,
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
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.5, 4.8), gridspec_kw={"width_ratios": [1, 1.3]})
    tot = sc[sc.branch == "ALL"]
    x = np.arange(len(EXTRA_ORDERS_PER_BRANCH_DAY))
    w = 0.26
    for j, share in enumerate(NEW_CUSTOMER_SHARES):
        t = tot[tot.new_customer_share == share].set_index("extra_orders_per_branch_per_office_day").loc[EXTRA_ORDERS_PER_BRANCH_DAY]
        bars = ax1.bar(x + (j - 1) * w, t.gross_profit_per_year_usd, w, color=style.SERIES[j],
                       edgecolor=style.SURFACE, linewidth=2, label=f"{share:.0%} of offer orders new")
        for bar, v in zip(bars, t.gross_profit_per_year_usd):
            ax1.text(bar.get_x() + bar.get_width() / 2, max(v, 0) + 300, f"${v / 1000:.1f}k", ha="center",
                     fontsize=7.5, color=style.INK_2)
    ax1.set_xticks(x, [f"+{e}" for e in EXTRA_ORDERS_PER_BRANCH_DAY])
    ax1.set_xlabel("Extra morning orders per branch per office day")
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v:,.0f}"))
    ax1.set_title("Extra gross profit per year, 3 branches\n(coffee + any pastry, loyalty card)", fontsize=11, pad=26)
    ax1.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=3, fontsize=7.5)
    ax1.grid(axis="x", visible=False)

    q = ch[ch.bundle.isin(["Coffee + any pastry", "Office pack (4+4)"])].copy()
    q["label"] = q.bundle + ": " + q.channel
    y = np.arange(len(q))[::-1]
    vals = q.min_share_of_orders_that_must_be_new_pct.clip(upper=120)
    colors = [style.SERIES[2] if v <= WORKABLE_NEW_SHARE_PCT else style.SERIES[1] for v in vals]
    ax2.barh(y, vals, color=colors, height=0.62, edgecolor=style.SURFACE, linewidth=2)
    for yi, v in zip(y, q.min_share_of_orders_that_must_be_new_pct):
        ax2.text(min(v, 120) + 1.2, yi, f"{v:.0f}%" + (" (never pays)" if v > 100 else ""), va="center",
                 fontsize=8, weight="bold", color=style.INK)
    ax2.axvline(100, color=style.MUTED, ls="--", lw=1)
    ax2.axvline(WORKABLE_NEW_SHARE_PCT, color=style.SERIES[2], ls=":", lw=1)
    ax2.text(WORKABLE_NEW_SHARE_PCT + 1, -0.85, f"workable: needs {WORKABLE_NEW_SHARE_PCT}% new or less",
             fontsize=7.5, color=style.INK_2)
    ax2.set_yticks(y, q.label, fontsize=7.5)
    ax2.set_xlim(0, 150)
    ax2.set_ylim(-1.2, len(q) - 0.4)
    ax2.set_xlabel("Share of offer orders that must be NEW customers to break even (%)")
    ax2.set_title("Free delivery only pays on office packs", fontsize=11)
    ax2.grid(axis="y", visible=False)
    fig.text(0.01, -0.03, "ESTIMATE. Office days and delivery costs sourced (docs/3_morning_sources.md); "
             "bundle discount and loyalty reward are design choices; the share of new customers is unknown, so 3 values are shown.",
             fontsize=8, color=style.MUTED)
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
