"""Menu engineering matrix (Kasavana-Smith) per branch and for the whole chain.

Each item is scored on two measured numbers:
  - Popularity: share of units sold at that branch. Popular if
    share >= 70% x (1 / number of items)  -> 1.56% for 45 items.
  - Profitability: gross profit per unit sold. Profitable if it is at least the
    branch's sales-weighted average profit per unit.

    popular + profitable      -> STAR       (protect & push)
    popular + not profitable  -> PLOWHORSE  (pair / reprice)
    not popular + profitable  -> PUZZLE     (rebrand / reposition)
    neither                   -> DOG        (merge / replace)

Run from the repo root:  python menu_engineering/menu_matrix.py
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

TABLES = ROOT / "outputs" / "menu_engineering" / "tables"
FIGS = ROOT / "outputs" / "menu_engineering" / "figures"
POPULARITY_FACTOR = 0.70
CLASSES = ["STAR", "PLOWHORSE", "PUZZLE", "DOG"]


def classify(sales: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Classify every product in `sales` (rows of one branch or the whole chain)."""
    p = (
        sales.groupby(["Product", "Category"])
        .agg(units=("Quantity", "sum"), revenue=(REV, "sum"), gross_profit=(GP, "sum"),
             avg_price=("Unit Price (USD)", "mean"), avg_cost=("Unit Cost (USD)", "mean"))
        .reset_index()
    )
    p["profit_per_unit"] = p.gross_profit / p.units
    p["margin_pct"] = p.gross_profit / p.revenue * 100
    p["popularity_share_pct"] = p.units / p.units.sum() * 100
    p["profit_share_pct"] = p.gross_profit / p.gross_profit.sum() * 100

    pop_threshold = POPULARITY_FACTOR * 100 / len(p)
    profit_threshold = p.gross_profit.sum() / p.units.sum()

    popular = p.popularity_share_pct >= pop_threshold
    profitable = p.profit_per_unit >= profit_threshold
    p["class"] = np.select(
        [popular & profitable, popular & ~profitable, ~popular & profitable],
        ["STAR", "PLOWHORSE", "PUZZLE"], default="DOG")
    p = p.sort_values(["class", "gross_profit"], key=lambda s: s.map(CLASSES.index) if s.name == "class" else -s)
    return p.round(3), {"popularity_threshold_pct": pop_threshold, "profit_threshold_usd": profit_threshold}


def plot(p: pd.DataFrame, th: dict, title: str, path: Path) -> None:
    style.apply()
    fig, ax = plt.subplots(figsize=(9, 6.2))
    for cls in CLASSES:
        s = p[p["class"] == cls]
        st = style.CLASS_STYLE[cls]
        ax.scatter(s.popularity_share_pct, s.profit_per_unit, s=st["size"], c=st["color"],
                   marker=st["marker"], edgecolors=style.SURFACE, linewidths=1.5,
                   label=f"{st['label']} ({len(s)} items, {s.profit_share_pct.sum():.0f}% of profit)", zorder=3)
    ax.axvline(th["popularity_threshold_pct"], color=style.MUTED, ls="--", lw=1)
    ax.axhline(th["profit_threshold_usd"], color=style.MUTED, ls="--", lw=1)

    # Label the items a manager would act on: top Stars, all Puzzles and Dogs.
    to_label = pd.concat([
        p[p["class"] == "STAR"].nlargest(4, "gross_profit"),
        p[p["class"].isin(["PUZZLE", "DOG"])],
        p[p["class"] == "PLOWHORSE"].nlargest(2, "units"),
    ])
    # Simple collision avoidance: nudge a label down when it would sit on top of one already placed.
    ax.set_ylim(ax.get_ylim()[0] - 0.3, ax.get_ylim()[1] + 0.5)
    x_span = np.ptp(ax.get_xlim())
    y_span = np.ptp(ax.get_ylim())
    placed = []
    for _, r in to_label.sort_values("profit_per_unit", ascending=False).iterrows():
        x, y, dy = r.popularity_share_pct, r.profit_per_unit, 4
        for px, py in placed:
            if abs(px - x) < 0.18 * x_span and abs(py - y) < 0.04 * y_span:
                dy -= 11
        placed.append((x, y + dy / 72 * y_span / 5))
        ax.annotate(r.Product, (x, y), xytext=(6, dy), textcoords="offset points",
                    fontsize=8, color=style.INK_2)

    corner = dict(fontsize=9, color=style.MUTED, weight="bold", transform=ax.transAxes)
    ax.text(0.99, 0.99, "STARS: push", ha="right", va="top", **corner)
    ax.text(0.01, 0.99, "PUZZLES: rebrand", ha="left", va="top", **corner)
    ax.text(0.99, 0.01, "PLOWHORSES: pair / reprice", ha="right", va="bottom", **corner)
    ax.text(0.01, 0.01, "DOGS: merge / replace", ha="left", va="bottom", **corner)

    ax.set_title(title)
    ax.set_xlabel("Popularity: share of units sold (%)")
    ax.set_ylabel("Gross profit per unit sold (USD)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.11), ncol=2, fontsize=9)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    FIGS.mkdir(parents=True, exist_ok=True)
    df = load_clean()

    results, summary_rows = {}, []
    for name, sales in [("chain", df)] + list(df.groupby("Branch")):
        key = name.lower()
        p, th = classify(sales)
        results[key] = p
        p.to_csv(TABLES / f"menu_matrix_{key}.csv", index=False)
        label = "All branches" if key == "chain" else f"{name} branch"
        plot(p, th, f"Menu engineering matrix: {label}", FIGS / f"matrix_{key}.png")
        for cls in CLASSES:
            s = p[p["class"] == cls]
            summary_rows.append({"scope": name, "class": cls, "items": len(s),
                                 "profit_usd": round(s.gross_profit.sum(), 2),
                                 "profit_share_pct": round(s.profit_share_pct.sum(), 1),
                                 "profit_threshold_usd": round(th["profit_threshold_usd"], 2),
                                 "popularity_threshold_pct": round(th["popularity_threshold_pct"], 2)})

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(TABLES / "menu_matrix_summary.csv", index=False)

    branches = ["garden", "harbour", "uptown"]
    classes = pd.DataFrame({b.title(): results[b].set_index("Product")["class"] for b in branches})
    diff = classes[classes.nunique(axis=1) > 1].sort_index()
    diff.to_csv(TABLES / "class_differences.csv")

    print(summary.pivot(index="class", columns="scope", values="profit_share_pct").loc[CLASSES])
    print("\nAverage profit per unit (profitability threshold):")
    print(summary.groupby("scope").profit_threshold_usd.first())
    print(f"\nItems classified differently across branches: {len(diff)}")
    print(diff)


if __name__ == "__main__":
    main()
