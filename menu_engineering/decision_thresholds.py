"""Which assumptions would change the Project 1 recommendation, and at what value.

For each estimated lever, compute the break-even value of the assumption it rests on, from
the measured tables the other Project 1 scripts write. If reality lands on the wrong side of
that value, the action should change. These are the numbers the Harbour test checks.

Run from the repo root (after actions.py, ab_test_power.py and garden_case.py):
    python menu_engineering/decision_thresholds.py
Writes outputs/menu_engineering/tables/decision_thresholds.csv
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

TABLES = ROOT / "outputs" / "menu_engineering" / "tables"
TABLES.mkdir(parents=True, exist_ok=True)
BRANCHES = ["Garden", "Harbour", "Uptown"]
PRICE_RISE = 0.20       # same as actions.py
BOWL_BRANCHES = ["Harbour", "Uptown"]


def main() -> None:
    rows = []

    def add(lever, assumption, today, threshold, flips_to):
        rows.append({"lever": lever, "assumption_in_estimate": assumption, "value_used": today,
                     "break_even_value": threshold, "if_worse_than_break_even": flips_to})

    # 1. Plowhorse +$0.20: how many units can be lost before the rise loses money?
    for b in BRANCHES:
        m = pd.read_csv(TABLES / f"menu_matrix_{b.lower()}.csv")
        ph = m[m["class"] == "PLOWHORSE"]
        p = ph.gross_profit.sum() / ph.units.sum()
        add(f"Plowhorse +$0.20 ({b})", "Units sold do not fall", "0% fewer units",
            f"{PRICE_RISE / (p + PRICE_RISE):.1%} fewer units (profit/unit ${p:.2f} -> ${p + PRICE_RISE:.2f})",
            "Drop the price rise; keep pairing them with Stars")

    # 2. Bundles: what share of bundle buyers would have bought both items anyway?
    dp = pd.read_csv(TABLES / "designed_pairings.csv")
    dp["discount"] = dp.price_separate - dp.bundle_price
    dp["c_star"] = dp.extra_profit_vs_star_alone / (dp.extra_profit_vs_star_alone + dp.discount)
    add("Bundles (5% off)", "Bundle buyers would otherwise have bought the Star alone",
        "All of them", f"{dp.c_star.min():.0%}-{dp.c_star.max():.0%} of buyers already buying both "
        f"(average discount ${dp.discount.mean():.2f} vs average extra profit ${dp.extra_profit_vs_star_alone.mean():.2f})",
        "Stop the discount; keep the till suggestion without a price cut")

    # 3. Bowls: added sales, or customers switching from a sandwich?
    for b in BOWL_BRANCHES:
        m = pd.read_csv(TABLES / f"menu_matrix_{b.lower()}.csv")
        bowl = m[m.Product.str.contains("Bowl")]
        sand = m[m.Category == "Sandwiches"]
        pb = bowl.gross_profit.sum() / bowl.units.sum()
        ps = sand.gross_profit.sum() / sand.units.sum()
        add(f"Bowl push ({b})", "+2 bowls a day are extra sales", f"${pb:.2f} gained per bowl",
            f"${pb - ps:.2f} per bowl if every bowl replaces a sandwich (${ps:.2f}); still positive",
            "Smaller gain, same action")

    # 4. Total: is the expected effect big enough for the Harbour test to see it?
    me = pd.read_csv(TABLES / "money_estimates.csv")
    k = pd.read_csv(TABLES / "branch_kpis.csv").set_index("branch")
    harbour_year = me[me.branch == "Harbour"].profit_per_year_usd.sum()
    per_order = harbour_year / (k.loc["Harbour", "orders"] * 2)
    lift = per_order / k.loc["Harbour", "profit_per_order"]
    pw = pd.read_csv(TABLES / "ab_test_power.csv")
    mde = pw[pw.design.str.startswith("Switchback") & (pw.test_weeks == 12)].minimum_detectable_effect_pct.iloc[0]
    add("Harbour switchback test", "Estimated effect at Harbour", f"+{lift:.1%} profit per order (+${per_order:.2f})",
        f"+{mde:.1f}% is the smallest effect 12 weeks can detect",
        f"If the real effect is under {mde / (lift * 100):.0%} of our estimate, the test shows nothing: "
        "stop the till rule, keep the menu layout")

    # 5. Garden: is the 43% premium real cash?
    g = pd.read_csv(TABLES / "garden_scenarios.csv")
    a = g[g.iloc[:, 0].astype(str).str.startswith("A")].iloc[0, -1]
    add("Garden sourcing", "The 43% premium is a supplier price Stories can renegotiate",
        f"${a:,.0f} a year recovered",
        "$0 cash if the premium is overhead or a transfer price loaded into unit cost",
        "Not a saving: report true product cost and re-run Garden's menu matrix on it")

    out = pd.DataFrame(rows)
    out.to_csv(TABLES / "decision_thresholds.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_colwidth", 120)
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
