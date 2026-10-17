"""Garden menu v2: the reorganized menu board for the least profitable branch.

Built only from Garden's own measured numbers (its classes, its unit costs, its combos).

Board rules
  FEATURED   Garden Stars whose margin survives Garden's cost premium (>= 40%), top 6 by
             gross profit per sale. These get the hero spots on the board.
  COMBOS     Garden's history-backed combos (outputs/tables/branch_combos.csv).
  SWEETS     Thin-margin desserts and pastries (< 40% margin): placed next to the combos
             ("best with a drink"), priced up to Harbour's price.
  LUNCH      High-profit Puzzles (bowls, Tuna Sandwich, Soup, Granola): own section with
             photos; thin-margin ones priced up to Harbour's price.
  MAIN       Everything else, by category. Plowhorses priced up to Harbour's price
             (Garden is ~5% below Harbour today, about +$0.15-0.25 per item).
  CHANGES    Mint Tea + English Breakfast Tea merged into one "Tea selection".
             Sparkling Water dropped (earns $0.80, 29% margin at Garden).
             Espresso kept (core coffee item).

Profit impact (ESTIMATE): three scenarios so no single assumption carries the result.
  price      units change by ELASTICITY x % price change
  featuring  a share of Plowhorse units moves to Featured items of the same kind
             (drink -> drink, food -> food); supported by the steerability test
             (members choose like random-by-popularity, so placement matters)
  upsell     share of single-item orders that add a second item (combos + till rule)
  sparkling  Sparkling Water buyers switch to Still Water / Lemonade or are lost
The sourcing fix (garden_case.py) is reported separately; it is not a menu change.

Run from the repo root (after menu_matrix.py, branch_combos.py, garden_case.py):
    python menu_engineering/garden_menu.py
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
ANNUALIZE = 2
THIN_MARGIN_PCT = 40
N_FEATURED = 6
DRINKS = {"Hot Coffee", "Cold Coffee", "Matcha & Tea", "Cold Drinks"}
MERGE_TEAS = ["Mint Tea", "English Breakfast Tea"]
DROP = ["Sparkling Water"]
KEEP_CORE = ["Espresso"]
SCENARIOS = {  # (elasticity, featuring shift, upsell conversion, sparkling switch to still, to lemonade)
    "Conservative": (-1.0, 0.03, 0.05, 0.40, 0.10),
    "Central": (-0.5, 0.05, 0.10, 0.50, 0.25),
    "Optimistic": (0.0, 0.08, 0.15, 0.60, 0.30),
}
SECTION_ORDER = ["FEATURED", "COMBOS", "SWEETS", "LUNCH", "MAIN", "CHANGES"]


def build_menu() -> pd.DataFrame:
    g = pd.read_csv(TABLES / "garden_items.csv")
    cls = pd.read_csv(TABLES / "menu_matrix_garden.csv")[["Product", "class"]]
    g = g.merge(cls, on="Product")
    g["is_drink"] = g.Category.isin(DRINKS)
    g["thin"] = g.margin_pct < THIN_MARGIN_PCT

    featured = (g[(g["class"] == "STAR") & ~g.thin]
                .nlargest(N_FEATURED, "profit_per_unit").Product.tolist())

    def section(r):
        if r.Product in DROP or r.Product in MERGE_TEAS:
            return "CHANGES"
        if r.Product in featured:
            return "FEATURED"
        if r.thin and r.Category in ("Desserts", "Bakery"):
            return "SWEETS"
        if r["class"] == "PUZZLE" or r.Category == "Meals":
            return "LUNCH"
        return "MAIN"

    def new_price(r):
        if r.Product in DROP:
            return None
        if r.thin or r["class"] == "PLOWHORSE":
            return r.harbour_price
        return r.price

    def reason(r):
        if r.Product in DROP:
            return f"Drop: earns ${r.profit_per_unit:.2f} per sale ({r.margin_pct:.0f}% margin) at Garden"
        if r.Product in MERGE_TEAS:
            return "Merge into one 'Tea selection'; suggest Chai Latte (+$0.40-0.50 profit)"
        if r.Product in KEEP_CORE:
            return "Keep (core coffee); offer a double shot"
        if r.Product in featured:
            return f"Star with {r.margin_pct:.0f}% margin and ${r.profit_per_unit:.2f} per sale: hero spot"
        if r.thin:
            return f"Thin margin ({r.margin_pct:.0f}%): Harbour price; sell with a drink"
        if r["class"] == "PLOWHORSE":
            return "Popular, low profit per sale: Harbour price; pair with a Star"
        if r["class"] == "PUZZLE":
            return "High profit per sale, rarely ordered: photo + lunch section"
        return "Keep"

    g["section"] = g.apply(section, axis=1)
    g["new_price"] = g.apply(new_price, axis=1)
    g["price_change"] = g.new_price - g.price
    g["new_profit_per_unit"] = g.new_price - g.cost
    g["new_margin_pct"] = g.new_profit_per_unit / g.new_price * 100
    g["reason"] = g.apply(reason, axis=1)
    g["section_rank"] = g.section.map(SECTION_ORDER.index)
    return g.sort_values(["section_rank", "profit_per_unit"], ascending=[True, False])


def impact(menu: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
    tx = df[df.Branch == "Garden"].groupby("Transaction ID").agg(lines=("Product", "size"), gp=(GP, "sum"))
    single = (tx.lines == 1).sum()
    gp_gain_second = tx[tx.lines == 2].gp.mean() - tx[tx.lines == 1].gp.mean()

    rows = []
    keep = menu[~menu.Product.isin(DROP)]
    feat = keep[keep.section == "FEATURED"]
    plow = keep[(keep["class"] == "PLOWHORSE")]
    still = menu.set_index("Product").loc["Still Water"]
    lemon = menu.set_index("Product").loc["Lemonade"]
    spark = menu.set_index("Product").loc["Sparkling Water"]

    for name, (e, shift, conv, to_still, to_lemon) in SCENARIOS.items():
        pct = keep.price_change / keep.price
        units_after_price = keep.units * (1 + e * pct)
        price_gain = (units_after_price * keep.new_profit_per_unit - keep.units * keep.profit_per_unit).sum()

        feat_gain = 0.0
        for drink in (True, False):
            f = feat[feat.is_drink == drink]
            p = plow[plow.is_drink == drink]
            if len(f) and len(p):
                f_ppu = (f.new_profit_per_unit * f.units).sum() / f.units.sum()
                p_ppu = (p.new_profit_per_unit * p.units).sum() / p.units.sum()
                feat_gain += shift * p.units.sum() * (f_ppu - p_ppu)

        upsell_gain = single * conv * gp_gain_second
        sparkling_gain = spark.units * (to_still * still.new_profit_per_unit
                                        + to_lemon * lemon.new_profit_per_unit - spark.profit_per_unit)
        parts = {"price_changes": price_gain, "featuring": feat_gain, "combos_and_till_upsell": upsell_gain,
                 "drop_sparkling_water": sparkling_gain}
        for lever, v in parts.items():
            rows.append({"scenario": name, "lever": lever, "profit_per_year_usd": round(v * ANNUALIZE)})
        rows.append({"scenario": name, "lever": "TOTAL menu v2", "profit_per_year_usd": round(sum(parts.values()) * ANNUALIZE)})
        rows.append({"scenario": name, "lever": "assumptions",
                     "profit_per_year_usd": None,
                     "note": (f"elasticity {e:+.1f}; {shift:.0%} of Plowhorse units move to Featured; "
                              f"{conv:.0%} of single-item orders add an item; Sparkling buyers: "
                              f"{to_still:.0%} to Still Water, {to_lemon:.0%} to Lemonade, rest lost")})
    out = pd.DataFrame(rows)
    gp_now = df[df.Branch == "Garden"][GP].sum() * ANNUALIZE
    out["pct_of_garden_gross_profit"] = (out.profit_per_year_usd / gp_now * 100).round(1)
    return out


def plot_board(menu: pd.DataFrame, path: Path) -> None:
    style.apply()
    combos = pd.read_csv(TABLES / "branch_combos.csv").query("branch == 'Garden'").head(4)
    fig = plt.figure(figsize=(13, 8.8))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 3)
    ax.set_ylim(-0.02, 1)
    ax.axis("off")

    def header(x, y, text, color):
        ax.add_patch(plt.Rectangle((x + 0.03, y - 0.012), 0.94, 0.045, color=color, lw=0))
        ax.text(x + 0.06, y + 0.011, text, fontsize=12, weight="bold", color="white", va="center")

    def item(x, y, name, price, old, note=None, bold=False):
        ax.text(x + 0.06, y, name, fontsize=10, color=style.INK, va="center", weight="bold" if bold else "normal")
        label = f"${price:.2f}"
        ax.text(x + 0.94, y, label, fontsize=10, color=style.INK, va="center", ha="right", weight="bold")
        if old is not None and abs(price - old) > 0.005:
            ax.text(x + 0.80, y, f"${old:.2f}", fontsize=8, color=style.MUTED, va="center", ha="right")
        if note:
            ax.text(x + 0.06, y - 0.022, note, fontsize=7.5, color=style.INK_2, va="center")

    ax.text(0.03, 0.965, "Stories Garden - menu v2", fontsize=17, weight="bold", color=style.INK, va="center")
    ax.text(0.03, 0.93, "Grey = today's price. Profit shown at list price and Garden's unit costs. Featured items keep their margin despite Garden's cost premium.",
            fontsize=9, color=style.INK_2, va="center")

    # Column 1: featured + combos
    y = 0.87
    header(0, y, "FEATURED", style.SERIES[0])
    y -= 0.06
    for _, r in menu[menu.section == "FEATURED"].iterrows():
        item(0, y, r.Product, r.new_price, r.price, f"${r.new_profit_per_unit:.2f} profit per sale, {r.new_margin_pct:.0f}% margin", bold=True)
        y -= 0.058
    y -= 0.035
    header(0, y, "GARDEN COMBOS", style.SERIES[2])
    y -= 0.06
    for _, c in combos.iterrows():
        item(0, y, c.combo, c.bundle_price, c.price_separate, f"${c.bundle_profit:.2f} profit per combo")
        y -= 0.058

    # Column 2: sweets + lunch
    y = 0.87
    header(1, y, "SWEETS - BEST WITH A DRINK", style.SERIES[1])
    y -= 0.055
    for _, r in menu[menu.section == "SWEETS"].iterrows():
        item(1, y, r.Product, r.new_price, r.price)
        y -= 0.04
    y -= 0.035
    header(1, y, "LUNCH: BOWLS & MORE", style.SERIES[2])
    y -= 0.055
    for _, r in menu[menu.section == "LUNCH"].iterrows():
        item(1, y, r.Product, r.new_price, r.price)
        y -= 0.04

    # Column 3: main menu + changes
    y = 0.87
    header(2, y, "COFFEE, TEA & DRINKS", style.MUTED)
    y -= 0.05
    main = menu[menu.section == "MAIN"]
    for _, r in main[main.is_drink].iterrows():
        item(2, y, r.Product, r.new_price, r.price)
        y -= 0.029
    tea = menu[menu.Product.isin(MERGE_TEAS)]
    item(2, y, "Tea selection (mint / English breakfast)", tea.price.max(), None)
    y -= 0.029
    y -= 0.035
    header(2, y, "BAKERY & FOOD", style.MUTED)
    y -= 0.05
    for _, r in main[~main.is_drink].iterrows():
        item(2, y, r.Product, r.new_price, r.price)
        y -= 0.029
    y -= 0.012
    ax.text(2.06, y, "Changes: Mint + English Breakfast Tea -> 'Tea selection'. Sparkling Water removed.",
            fontsize=8, color=style.INK_2, va="center")
    fig.savefig(path, bbox_inches="tight", dpi=110)
    plt.close(fig)


def main() -> None:
    df = load_clean()
    menu = build_menu()
    cols = ["section", "Product", "Category", "class", "units", "price", "new_price", "price_change",
            "cost", "profit_per_unit", "new_profit_per_unit", "margin_pct", "new_margin_pct", "reason"]
    menu[cols].round(2).to_csv(TABLES / "garden_menu_v2.csv", index=False)
    imp = impact(menu, df)
    imp.to_csv(TABLES / "garden_menu_impact.csv", index=False)
    plot_board(menu, FIGS / "garden_menu_v2.png")

    pd.set_option("display.width", 220)
    for s in SECTION_ORDER:
        part = menu[menu.section == s]
        print(f"\n{s} ({len(part)}): " + ", ".join(
            f"{p} ${o:.2f}->{'drop' if pd.isna(n) else f'${n:.2f}'}" for p, o, n in zip(part.Product, part.price, part.new_price)))
    print("\n", imp.pivot_table(index="lever", columns="scenario", values="profit_per_year_usd").round(0))
    tot = imp[imp.lever == "TOTAL menu v2"].set_index("scenario")
    print("\nAs % of Garden gross profit:", tot.pct_of_garden_gross_profit.to_dict())


if __name__ == "__main__":
    main()
