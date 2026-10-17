"""Garden branch profit case: the least profitable branch, and what to do about it.

Measured:
  - Garden's unit cost vs Harbour's for the SAME items (the "cost leak").
  - Where the leak sits (by category) and which items it pushes into thin margins.
  - Which items still earn the most dollars per sale at Garden.
Estimated (assumption stated in the output):
  - Sourcing fix (full / half), repricing to Harbour price level under three
    price-sensitivity assumptions, targeted repricing of thin-margin items only.

Run from the repo root:  python menu_engineering/garden_case.py
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
ANNUALIZE = 2
THIN_MARGIN = 0.40                 # below this margin an item is "thin" at Garden
ELASTICITIES = [0.0, -0.5, -1.0]   # % change in units for each +1% price (0 = volume holds)
DRINKS = {"Hot Coffee", "Cold Coffee", "Matcha & Tea", "Cold Drinks"}


def item_table(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby(["Branch", "Product", "Category"]).agg(
        units=("Quantity", "sum"), revenue=(REV, "sum"), gross_profit=(GP, "sum"),
        price=("Unit Price (USD)", "mean"), cost=("Unit Cost (USD)", "mean")).reset_index()
    w = g.pivot_table(index=["Product", "Category"], columns="Branch",
                      values=["units", "revenue", "gross_profit", "price", "cost"])
    t = pd.DataFrame({
        "units": w["units"]["Garden"], "price": w["price"]["Garden"], "cost": w["cost"]["Garden"],
        "revenue": w["revenue"]["Garden"], "gross_profit": w["gross_profit"]["Garden"],
        "harbour_price": w["price"]["Harbour"], "harbour_cost": w["cost"]["Harbour"],
        "uptown_cost": w["cost"]["Uptown"],
    }).reset_index()
    t["profit_per_unit"] = t.gross_profit / t.units
    t["margin_pct"] = t.gross_profit / t.revenue * 100
    t["cost_vs_harbour_pct"] = (t.cost / t.harbour_cost - 1) * 100
    t["cost_vs_uptown_pct"] = (t.cost / t.uptown_cost - 1) * 100
    t["extra_cost_vs_harbour_6mo"] = (t.cost - t.harbour_cost) * t.units
    t["profit_per_unit_at_harbour_cost"] = t.price - t.harbour_cost
    t["thin_margin"] = t.margin_pct < THIN_MARGIN * 100
    return t


def garden_action(r) -> str:
    if r.Product == "Sparkling Water":
        return "REPRICE to Harbour price (+$0.14) or drop; earns only $0.80 at Garden"
    if r.thin_margin and r.Category in ("Desserts", "Sandwiches", "Meals", "Breakfast"):
        return "FIX SOURCING FIRST; reprice to Harbour price; sell only in combos with high-margin drinks"
    if r.thin_margin:
        return "Reprice to Harbour price; pair with a high-margin drink"
    if r.Category in DRINKS and r.margin_pct >= 55:
        return "PUSH at Garden: high margin survives the cost premium; lead every combo"
    return "Keep; follow chain menu-engineering action"


def scenarios(t: pd.DataFrame) -> pd.DataFrame:
    rows = []
    leak = t.extra_cost_vs_harbour_6mo.sum()
    rows.append({"scenario": "A. Fix sourcing to Harbour's cost level", "type": "ESTIMATE",
                 "measured_input": f"Garden pays ${leak:,.0f} more than Harbour for the same units (6 months)",
                 "assumption": "Garden buys at Harbour's unit costs; prices and volume unchanged",
                 "profit_per_year_usd": round(leak * ANNUALIZE)})
    rows.append({"scenario": "B. Fix half the sourcing gap", "type": "ESTIMATE",
                 "measured_input": "same as A", "assumption": "half of the cost gap is closed",
                 "profit_per_year_usd": round(leak / 2 * ANNUALIZE)})
    for e in ELASTICITIES:
        dp = t.harbour_price / t.price - 1
        new_units = t.units * (1 + e * dp)
        new_gp = new_units * (t.harbour_price - t.cost)
        gain = (new_gp - t.units * (t.price - t.cost)).sum()
        rows.append({"scenario": f"C. Reprice all items to Harbour price (sensitivity {e:+.1f})", "type": "ESTIMATE",
                     "measured_input": f"Garden prices are {(1 - (t.price / t.harbour_price).mean()) * 100:.1f}% below Harbour on average",
                     "assumption": f"each +1% price changes units by {e:+.1f}%",
                     "profit_per_year_usd": round(gain * ANNUALIZE)})
    thin = t[t.thin_margin]
    for e in (0.0, -1.0):
        dp = thin.harbour_price / thin.price - 1
        new_gp = thin.units * (1 + e * dp) * (thin.harbour_price - thin.cost)
        gain = (new_gp - thin.units * (thin.price - thin.cost)).sum()
        rows.append({"scenario": f"D. Reprice only the {len(thin)} thin-margin items to Harbour price (sensitivity {e:+.1f})",
                     "type": "ESTIMATE", "measured_input": f"{len(thin)} items below {THIN_MARGIN:.0%} margin at Garden",
                     "assumption": f"each +1% price changes units by {e:+.1f}%",
                     "profit_per_year_usd": round(gain * ANNUALIZE)})
    return pd.DataFrame(rows)


def plot_leak(t: pd.DataFrame, path: Path) -> None:
    style.apply()
    c = t.groupby("Category").agg(leak=("extra_cost_vs_harbour_6mo", "sum"),
                                  gp=("gross_profit", "sum"), rev=("revenue", "sum"))
    c["margin"] = c.gp / c.rev * 100
    c = c.sort_values("margin")
    fig, ax = plt.subplots(figsize=(9, 4.4))
    colors = [style.SERIES[1] if m < THIN_MARGIN * 100 else style.SERIES[0] for m in c.margin]
    ax.barh(c.index, c.margin, color=colors, height=0.6, edgecolor=style.SURFACE, linewidth=2)
    for cat, r in c.iterrows():
        ax.text(r.margin + 0.8, cat, f"{r.margin:.0f}%   (extra cost vs Harbour: ${r.leak:,.0f})",
                va="center", fontsize=9, color=style.INK_2)
    ax.axvline(THIN_MARGIN * 100, color=style.MUTED, ls="--", lw=1)
    ax.text(THIN_MARGIN * 100 + 0.5, -0.75, "40% thin-margin line", fontsize=8, color=style.MUTED, va="center")
    ax.set_ylim(-1.1, len(c) - 0.5)
    ax.set_xlim(0, 95)
    ax.set_xlabel("Gross margin at Garden (%)")
    leak = t.extra_cost_vs_harbour_6mo.sum()
    ax.set_title(f"Garden pays ${leak:,.0f} more than Harbour for the same items (6 months)\n"
                 "The premium is flat; it hurts food the most, drinks keep their margin", fontsize=12)
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def plot_scenarios(s: pd.DataFrame, path: Path) -> None:
    style.apply()
    s = s.iloc[::-1]
    fig, ax = plt.subplots(figsize=(10, 4.6))
    colors = [style.SERIES[0] if x.startswith(("A", "B")) else style.SERIES[2] for x in s.scenario]
    ax.barh(s.scenario, s.profit_per_year_usd, color=colors, height=0.6, edgecolor=style.SURFACE, linewidth=2)
    for name, v in zip(s.scenario, s.profit_per_year_usd):
        ax.text(v + 300, name, f"${v:,.0f}/yr", va="center", fontsize=9, color=style.INK, weight="bold")
    ax.set_xlim(0, s.profit_per_year_usd.max() * 1.18)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v:,.0f}"))
    ax.set_xlabel("Estimated extra gross profit per year at Garden (USD)")
    ax.set_title("Garden: sourcing is the big lever; repricing alone is small")
    ax.grid(axis="y", visible=False)
    ax.tick_params(axis="y", labelsize=8.5)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    df = load_clean()
    t = item_table(df)
    t["garden_action"] = t.apply(garden_action, axis=1)
    out = t.sort_values("profit_per_unit", ascending=False).round(2)
    out.to_csv(TABLES / "garden_items.csv", index=False)

    s = scenarios(t)
    s.to_csv(TABLES / "garden_scenarios.csv", index=False)

    tx = df.groupby("Transaction ID").agg(branch=("Branch", "first"), gp=(GP, "sum"), rev=(REV, "sum"))
    kpi = tx.groupby("branch").agg(orders=("gp", "size"), profit_per_order=("gp", "mean"))
    kpi["revenue"] = df.groupby("Branch")[REV].sum()
    kpi["gross_profit"] = df.groupby("Branch")[GP].sum()
    kpi["margin_pct"] = kpi.gross_profit / kpi.revenue * 100
    kpi["product_cost"] = df.groupby("Branch").line_cost.sum()
    kpi.round(2).to_csv(TABLES / "branch_kpis.csv")

    plot_leak(t, FIGS / "garden_cost_leak.png")
    plot_scenarios(s, FIGS / "garden_scenarios.png")

    pd.set_option("display.width", 220)
    print(kpi.round(2))
    print(f"\nGarden cost vs Harbour (same items): +{t.cost_vs_harbour_pct.mean():.1f}% on average "
          f"(range {t.cost_vs_harbour_pct.min():.1f}% to {t.cost_vs_harbour_pct.max():.1f}%)")
    print(f"Extra cost vs Harbour, 6 months: ${t.extra_cost_vs_harbour_6mo.sum():,.0f}")
    print("\nScenarios:\n", s[["scenario", "profit_per_year_usd"]].to_string(index=False))
    print("\nTop Garden earners per sale:\n",
          out.head(8)[["Product", "profit_per_unit", "margin_pct", "units"]].to_string(index=False))


if __name__ == "__main__":
    main()
