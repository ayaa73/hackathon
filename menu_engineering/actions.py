"""Turn the menu matrix into actions per branch, designed pairings, and money estimates.

Every money figure here is an ESTIMATE built on MEASURED inputs from the data.
The assumption behind each estimate is written next to it in the output table.

Run from the repo root (after menu_matrix.py):  python menu_engineering/actions.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

from src.clean import GP, load_clean  # noqa: E402
from src import style  # noqa: E402

TABLES = ROOT / "outputs" / "tables"
FIGS = ROOT / "outputs" / "figures"
BRANCHES = ["Garden", "Harbour", "Uptown"]
ANNUALIZE = 2  # the data covers 6 months (Jan-Jun 2026)

# ---- Assumptions (edit here) -------------------------------------------------
UPSELL_CONVERSION = 0.10       # share of single-item orders that become 2-item orders
PLOWHORSE_PRICE_RISE = 0.20    # USD added to each Plowhorse
BOWLS_EXTRA_PER_DAY = 2        # extra bowls sold per day per branch after rebranding
BOWL_BRANCHES = ["Harbour", "Uptown"]  # Garden waits until its sourcing costs are fixed
BUNDLE_DISCOUNT = 0.05         # bundle priced 5% below buying both items separately

ACTION_BY_CLASS = {
    "STAR": "PUSH: top of menu, lead every pairing, never discount",
    "PLOWHORSE": "PAIR with a Star + test +$0.20 price",
    "PUZZLE": "REBRAND: photo, better menu spot, lunch combo",
    "DOG": "MERGE / REPLACE",
}
OVERRIDES = {
    "Espresso": "KEEP (core coffee item): add a double-shot upsell instead of removing",
    "Mint Tea": "MERGE with English Breakfast Tea into one 'Tea selection'; suggest Chai Latte",
    "English Breakfast Tea": "MERGE with Mint Tea into one 'Tea selection'; suggest Chai Latte",
}
PAIRINGS = [
    ("Iced Latte + Butter Croissant", "Iced Latte", "Butter Croissant"),
    ("Cold Brew + Brownie", "Cold Brew", "Brownie"),
    ("Chicken Pesto Sandwich + Peach Iced Tea", "Chicken Pesto Sandwich", "Peach Iced Tea"),
    ("Quinoa Bowl + Iced Matcha (lunch)", "Quinoa Bowl", "Iced Matcha"),
]


def item_actions() -> pd.DataFrame:
    rows = []
    for b in BRANCHES:
        m = pd.read_csv(TABLES / f"menu_matrix_{b.lower()}.csv")
        for _, r in m.iterrows():
            action = OVERRIDES.get(r.Product, ACTION_BY_CLASS[r["class"]])
            if r.Product == "Blueberry Muffin" and r["class"] == "DOG":
                action = f"REMOVE at {b} only (test 6 weeks); keep at other branches"
            if b == "Garden" and r.Category == "Desserts":
                action += " | Garden: fix +49% sourcing cost before repricing desserts"
            rows.append({"branch": b, "product": r.Product, "category": r.Category,
                         "class": r["class"], "units_6mo": int(r.units),
                         "profit_per_unit": r.profit_per_unit, "margin_pct": round(r.margin_pct, 1),
                         "action": action})
    return pd.DataFrame(rows)


def money_estimates(df: pd.DataFrame, actions: pd.DataFrame) -> pd.DataFrame:
    tx = df.groupby("Transaction ID").agg(branch=("Branch", "first"), lines=("Product", "size"), gp=(GP, "sum"))
    rows = []
    for b in BRANCHES:
        t = tx[tx.branch == b]
        single = t[t.lines == 1]
        gp1, gp2 = single.gp.mean(), t[t.lines == 2].gp.mean()
        upsell = len(single) * UPSELL_CONVERSION * (gp2 - gp1) * ANNUALIZE
        rows.append({"branch": b, "lever": "Pairing upsell",
                     "measured_input": f"{len(single):,} single-item orders in 6 months; "
                                       f"1-item order profit ${gp1:.2f} vs 2-item ${gp2:.2f}",
                     "assumption": f"{UPSELL_CONVERSION:.0%} of single-item orders add a second item",
                     "profit_per_year_usd": round(upsell)})

        plow_units = actions[(actions.branch == b) & (actions["class"] == "PLOWHORSE")].units_6mo.sum()
        rows.append({"branch": b, "lever": "Plowhorse +$0.20",
                     "measured_input": f"{plow_units:,} Plowhorse units sold in 6 months",
                     "assumption": f"+${PLOWHORSE_PRICE_RISE:.2f} per unit, sales volume unchanged",
                     "profit_per_year_usd": round(plow_units * PLOWHORSE_PRICE_RISE * ANNUALIZE)})

        if b in BOWL_BRANCHES:
            bowls = actions[(actions.branch == b) & actions["product"].isin(["Quinoa Bowl", "Chicken Salad Bowl"])]
            ppu = (bowls.profit_per_unit * bowls.units_6mo).sum() / bowls.units_6mo.sum()
            rows.append({"branch": b, "lever": "Puzzle push (bowls)",
                         "measured_input": f"bowl profit ${ppu:.2f} per unit at {b}",
                         "assumption": f"+{BOWLS_EXTRA_PER_DAY} bowls/day after rebranding",
                         "profit_per_year_usd": round(BOWLS_EXTRA_PER_DAY * ppu * 365)})
    return pd.DataFrame(rows)


def pairing_table(df: pd.DataFrame) -> pd.DataFrame:
    price = df.groupby(["Branch", "Product"])["Unit Price (USD)"].mean()
    cost = df.groupby(["Branch", "Product"])["Unit Cost (USD)"].mean()
    rows = []
    for b in BRANCHES:
        for name, a, c in PAIRINGS:
            separate = price[(b, a)] + price[(b, c)]
            bundle = separate * (1 - BUNDLE_DISCOUNT)
            profit = bundle - cost[(b, a)] - cost[(b, c)]
            rows.append({"branch": b, "pairing": name, "price_separate": round(separate, 2),
                         "bundle_price": round(bundle, 2), "bundle_profit": round(profit, 2),
                         "profit_of_star_alone": round(price[(b, a)] - cost[(b, a)], 2),
                         "extra_profit_vs_star_alone": round(profit - (price[(b, a)] - cost[(b, a)]), 2)})
    return pd.DataFrame(rows)


def plot_money(money: pd.DataFrame, path: Path) -> None:
    style.apply()
    pivot = money.pivot_table(index="lever", columns="branch", values="profit_per_year_usd", aggfunc="sum").fillna(0)
    pivot = pivot.loc[pivot.sum(axis=1).sort_values().index]
    fig, ax = plt.subplots(figsize=(9, 3.8))
    left = pd.Series(0.0, index=pivot.index)
    for i, b in enumerate(BRANCHES):
        ax.barh(pivot.index, pivot[b], left=left, color=style.SERIES[i], height=0.55,
                edgecolor=style.SURFACE, linewidth=2, label=b)
        left += pivot[b]
    for lever, total in left.items():
        ax.text(total + 150, lever, f"${total:,.0f}/yr", va="center", fontsize=10, color=style.INK, weight="bold")
    ax.set_xlim(0, left.max() * 1.22)
    ax.set_title(f"Menu engineering: estimated extra gross profit, ${left.sum():,.0f} per year", pad=26)
    ax.set_xlabel("Estimated extra gross profit per year (USD)")
    ax.grid(axis="y", visible=False)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=3, fontsize=9)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v:,.0f}"))
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    df = load_clean()
    actions = item_actions()
    actions.to_csv(TABLES / "menu_actions.csv", index=False)

    money = money_estimates(df, actions)
    money.to_csv(TABLES / "money_estimates.csv", index=False)

    pairs = pairing_table(df)
    pairs.to_csv(TABLES / "designed_pairings.csv", index=False)

    plot_money(money, FIGS / "money_estimates.png")

    pd.set_option("display.width", 200)
    print(money.groupby("lever").profit_per_year_usd.sum().sort_values(ascending=False))
    print(f"TOTAL estimated extra gross profit per year: ${money.profit_per_year_usd.sum():,.0f}")
    print("\nDesigned pairings (Harbour):")
    print(pairs[pairs.branch == "Harbour"].to_string(index=False))
    print("\nNon-standard actions:")
    print(actions[actions.action.str.startswith(("KEEP", "MERGE", "REMOVE"))]
          [["branch", "product", "class", "action"]].to_string(index=False))


if __name__ == "__main__":
    main()
