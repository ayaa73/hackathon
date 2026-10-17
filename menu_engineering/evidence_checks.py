"""Evidence checks: every supporting fact quoted in the write-ups that is not already an
output of another script is computed here, so no number in the docs comes from nowhere.

Writes outputs/tables/evidence_checks.csv (claim, value, how it was computed).

Run from the repo root:  python menu_engineering/evidence_checks.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from src.clean import GP, load_clean  # noqa: E402

TABLES = ROOT / "outputs" / "tables"
PROMO_START, PROMO_END = pd.Timestamp("2026-03-12"), pd.Timestamp("2026-05-19")


def main() -> None:
    df = load_clean()
    rows = []

    def add(claim, value, method):
        rows.append({"claim": claim, "value": value, "method": method})

    # 1. Anonymous orders
    tx = df.groupby("Transaction ID").agg(cust=("Customer ID", "first"))
    add("Orders without a Customer ID (%)", round(tx.cust.isna().mean() * 100, 1),
        "share of transactions whose Customer ID is empty")

    # 2. Price and cost level by branch vs Uptown (same items)
    pc = df.groupby(["Product", "Branch"])[["Unit Price (USD)", "Unit Cost (USD)"]].mean().unstack()
    for col, label in [("Unit Price (USD)", "price"), ("Unit Cost (USD)", "unit cost")]:
        x = pc[col]
        for b in ("Garden", "Harbour"):
            add(f"{b} {label} vs Uptown, same items (%)", round(((x[b] / x["Uptown"]).mean() - 1) * 100, 1),
                "mean over 45 items of (branch average / Uptown average) - 1")
    add("Garden price vs Harbour, same items (%)",
        round(((pc["Unit Price (USD)"]["Garden"] / pc["Unit Price (USD)"]["Harbour"]).mean() - 1) * 100, 1),
        "mean over 45 items of (Garden / Harbour) - 1")

    # 3. Category over-index by branch (units share vs chain share)
    units = df.groupby(["Branch", "Product"]).Quantity.sum().unstack(0)
    share = units / units.sum()
    chain = units.sum(axis=1) / units.sum().sum()
    idx = share.div(chain, axis=0)
    cat = df.groupby("Product").Category.first()
    for b, c in [("Uptown", "Sandwiches"), ("Garden", "Desserts")]:
        items = cat[cat == c].index
        add(f"{b}: {c} sales index vs chain (range across items)",
            f"{idx.loc[items, b].min():.2f}-{idx.loc[items, b].max():.2f}",
            "item's share of the branch's units / item's share of chain units (1.00 = chain average)")

    # 4. Harbour 15% promo (Mar 12 - May 19): growth of promo categories vs Garden (no promo)
    promo_cats = {"Cold Coffee", "Desserts"}
    discounted = df[(df["Discount Rate"] == 0.15)]
    add("15% discount lines: branches, categories, dates",
        f"{sorted(discounted.Branch.unique())}; {sorted(discounted.Category.unique())}; "
        f"{discounted.Date.min().date()} to {discounted.Date.max().date()}",
        "all rows with Discount Rate = 0.15")
    add("Discount given in the 15% promo (USD)",
        round((discounted.Quantity * discounted["Unit Price (USD)"] * 0.15).sum(), 0),
        "quantity x list price x 15% over promo rows")
    pre = df[df.Date < PROMO_START]
    win = df[(df.Date >= PROMO_START) & (df.Date <= PROMO_END)]
    for b in ("Harbour", "Garden", "Uptown"):
        def per_day(s):
            s = s[(s.Branch == b) & s.Category.isin(promo_cats)]
            return s[GP].sum() / s.Date.nunique()
        add(f"{b}: iced coffee + dessert gross profit per day, promo window vs before (%)",
            round((per_day(win) / per_day(pre) - 1) * 100, 1),
            "gross profit per trading day in Mar 12-May 19 vs Jan 1-Mar 11, same categories")

    out = pd.DataFrame(rows)
    out.to_csv(TABLES / "evidence_checks.csv", index=False)
    pd.set_option("display.width", 220)
    pd.set_option("display.max_colwidth", 80)
    print(out[["claim", "value"]].to_string(index=False))


if __name__ == "__main__":
    main()
