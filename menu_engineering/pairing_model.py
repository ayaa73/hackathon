"""Can the data tell us which pairings to push?

1. Lift: how much more often two items/categories are bought together than chance.
2. A small recommender, trained on Jan-Apr and tested on May-Jun (unseen),
   compared with a simple baseline:
     task: in a 2-item order, given item A, is item B in our top-3 suggestions?
     - Baseline : the 3 most popular items (excluding A)
     - Model 1  : items most often bought with A
     - Model 2  : items most often bought with A's category
   A bootstrap gives 95% intervals so we don't over-read small gaps.

Run from the repo root:  python menu_engineering/pairing_model.py
"""
import sys
from collections import Counter, defaultdict
from itertools import combinations, permutations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

from src.clean import load_clean  # noqa: E402
from src import style  # noqa: E402

TABLES = ROOT / "outputs" / "tables"
FIGS = ROOT / "outputs" / "figures"
SPLIT_DATE = pd.Timestamp("2026-05-01")
TOP_K = 3
MIN_PAIR_COUNT = 30
N_BOOT = 1000


def baskets(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby("Transaction ID").agg(items=("Product", lambda s: tuple(sorted(set(s)))),
                                            Date=("Date", "first")).reset_index()


def lift_table(b: pd.DataFrame, cat: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame]:
    n = len(b)
    single, pair, csingle, cpair = Counter(), Counter(), Counter(), Counter()
    for items in b["items"]:
        single.update(items)
        pair.update(combinations(items, 2))
        cats = sorted({cat[i] for i in items})
        csingle.update(cats)
        cpair.update(combinations(cats, 2))

    def table(s, p, min_n):
        rows = [(a, c, k, (k / n) / ((s[a] / n) * (s[c] / n))) for (a, c), k in p.items() if k >= min_n]
        return pd.DataFrame(rows, columns=["a", "b", "orders_together", "lift"]).sort_values("lift", ascending=False)

    return table(single, pair, MIN_PAIR_COUNT).round(3), table(csingle, cpair, 1).round(3)


def evaluate(train: pd.DataFrame, test: pd.DataFrame, cat: pd.Series) -> pd.DataFrame:
    pop = Counter(i for items in train["items"] for i in items)
    co, cat_co = defaultdict(Counter), defaultdict(Counter)
    for items in train["items"]:
        for a, c in permutations(items, 2):
            co[a][c] += 1
            cat_co[cat[a]][c] += 1

    def top(counter, exclude):
        return [x for x, _ in counter.most_common(TOP_K + 1) if x != exclude][:TOP_K]

    names = ["Baseline: most popular", "Model 1: co-purchase", "Model 2: category co-purchase"]
    # One row per test order: hits (0, 1 or 2) when predicting each item from the other.
    hits = []
    for items in test["items"]:
        if len(items) != 2:
            continue
        row = [0, 0, 0]
        for a, c in (items, items[::-1]):
            row[0] += c in top(pop, a)
            row[1] += c in top(co[a], a)
            row[2] += c in top(cat_co[cat[a]], a)
        hits.append(row)
    hits = np.array(hits)
    n = len(hits)

    # Bootstrap by ORDER (both predictions from one order stay together, so the
    # interval is not artificially narrow).
    rng = np.random.default_rng(42)
    boots = np.array([hits[rng.integers(0, n, n)].sum(axis=0) / (2 * n) for _ in range(N_BOOT)])
    rate = hits.sum(axis=0) / (2 * n)
    rows = []
    for i, name in enumerate(names):
        gain = (boots[:, i] - boots[:, 0]) * 100
        rows.append({"method": name, "test_orders": n, "test_predictions": 2 * n,
                     "top3_hit_rate_pct": round(rate[i] * 100, 1),
                     "ci95_low_pct": round(np.percentile(boots[:, i], 2.5) * 100, 1),
                     "ci95_high_pct": round(np.percentile(boots[:, i], 97.5) * 100, 1),
                     "gain_vs_baseline_pts": round((rate[i] - rate[0]) * 100, 2),
                     "gain_ci95_low_pts": round(np.percentile(gain, 2.5), 2),
                     "gain_ci95_high_pts": round(np.percentile(gain, 97.5), 2)})
    out = pd.DataFrame(rows)
    out["relative_gain_vs_baseline_pct"] = ((out.top3_hit_rate_pct / out.loc[0, "top3_hit_rate_pct"] - 1) * 100).round(1)
    return out


def plot(res: pd.DataFrame, path: Path) -> None:
    style.apply()
    fig, ax = plt.subplots(figsize=(8.5, 3.6))
    colors = [style.MUTED, style.SERIES[0], style.SERIES[0]]
    y = np.arange(len(res))[::-1]
    ax.barh(y, res.top3_hit_rate_pct, color=colors, height=0.5, edgecolor=style.SURFACE, linewidth=2)
    ax.errorbar(res.top3_hit_rate_pct, y,
                xerr=[res.top3_hit_rate_pct - res.ci95_low_pct, res.ci95_high_pct - res.top3_hit_rate_pct],
                fmt="none", ecolor=style.INK_2, capsize=4, lw=1)
    for yi, (_, r) in zip(y, res.iterrows()):
        ax.text(r.ci95_high_pct + 0.3, yi, f"{r.top3_hit_rate_pct:.1f}%", va="center", fontsize=10,
                weight="bold", color=style.INK)
    ax.set_yticks(y, res.method)
    ax.set_xlim(0, res.ci95_high_pct.max() * 1.25)
    ax.set_xlabel("Correct second item in top-3 suggestions (May-Jun test orders, %)")
    ax.set_title("Pairing model vs baseline: a small gain, so test pairings in-store")
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    df = load_clean()
    cat = df.groupby("Product").Category.first()
    b = baskets(df)

    prod_lift, cat_lift = lift_table(b, cat)
    prod_lift.to_csv(TABLES / "pair_lift_products.csv", index=False)
    cat_lift.to_csv(TABLES / "pair_lift_categories.csv", index=False)

    multi = b[b["items"].str.len() >= 2]
    train, test = multi[multi.Date < SPLIT_DATE], multi[multi.Date >= SPLIT_DATE]
    res = evaluate(train, test, cat)
    res.to_csv(TABLES / "pairing_model_results.csv", index=False)
    plot(res, FIGS / "pairing_model.png")

    print(f"Orders: {len(b):,} | multi-item: {len(multi):,} | train {len(train):,} (Jan-Apr) | test {len(test):,} (May-Jun)")
    print(f"Strongest product pair lift: {prod_lift.lift.max():.2f} | weakest: {prod_lift.lift.min():.2f}")
    print("Top category pairs:\n", cat_lift.head(5).to_string(index=False))
    print("\n", res.to_string(index=False))


if __name__ == "__main__":
    main()
