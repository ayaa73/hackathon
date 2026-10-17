"""Per-branch combos and till suggestions, learned from each branch's purchase history.

Question: when a customer at branch X orders item A, what should staff suggest so the
customer buys more AND Stories earns more?

For every branch separately:
  1. Till suggestions: for each item A, rank complementary items B (drink -> food,
     food -> drink). Four ranking methods are tested (step 3); the one used for the
     till table is TILL_METHOD:
         Popular x profit: (orders containing B at this branch) x profit per unit of B
     History-based methods use P(customer also buys B | bought A, this branch), smoothed
     toward the branch's overall rate for B so a pair seen only a few times cannot
     dominate (prior strength ALPHA).
  2. Combos: the best (A, B) pairs for a branch, ranked by the profit pool they unlock:
         single-item orders of A x P(B | A) x profit of B
     with each anchor used once and each add-on at most twice, priced 5% below buying both.
  3. Validation (per branch): learn from Jan-Apr, test on May-Jun drink+food orders.
     Given the anchor, is the real add-on in the top-3 suggestions, and how much profit
     do the suggestions capture? Compared with a most-popular baseline.

Run from the repo root:  python menu_engineering/branch_combos.py
"""
import sys
from collections import Counter, defaultdict
from itertools import permutations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

from src.clean import GP, load_clean  # noqa: E402
from src import style  # noqa: E402

TABLES = ROOT / "outputs" / "tables"
FIGS = ROOT / "outputs" / "figures"
BRANCHES = ["Garden", "Harbour", "Uptown"]
DRINK_CATEGORIES = {"Hot Coffee", "Cold Coffee", "Matcha & Tea", "Cold Drinks"}
ALPHA = 50               # smoothing strength (pseudo-orders pulled toward the branch average)
MIN_PAIR_ORDERS = 15     # a combo must have been bought together at least this often
TOP_K = 3
COMBOS_PER_BRANCH = 6
MAX_ADDON_REUSE = 2
BUNDLE_DISCOUNT = 0.05
SPLIT_DATE = pd.Timestamp("2026-05-01")
N_BOOT = 1000


class BranchModel:
    """Co-purchase statistics for one branch, learned from the orders it is given."""

    def __init__(self, sales: pd.DataFrame, is_drink: pd.Series):
        self.is_drink = is_drink
        baskets = sales.groupby("Transaction ID").Product.apply(lambda s: tuple(sorted(set(s))))
        self.n_orders = len(baskets)
        self.item_orders = Counter(i for items in baskets for i in items)
        self.single_orders = Counter(items[0] for items in baskets if len(items) == 1)
        self.co = defaultdict(Counter)
        for items in baskets:
            for a, b in permutations(items, 2):
                self.co[a][b] += 1
        units = sales.groupby("Product").Quantity.sum()
        self.profit = sales.groupby("Product")[GP].sum() / units
        self.price = sales.groupby("Product")["Unit Price (USD)"].mean()
        self.cost = sales.groupby("Product")["Unit Cost (USD)"].mean()

    def complements(self, a):
        return [b for b in self.profit.index if b != a and self.is_drink[b] != self.is_drink[a]]

    def p_addon(self, a, b):
        base = self.item_orders[b] / self.n_orders
        return (self.co[a][b] + ALPHA * base) / (self.item_orders[a] + ALPHA)

    def lift(self, a, b):
        return (self.co[a][b] / self.item_orders[a]) / (self.item_orders[b] / self.n_orders) if self.item_orders[a] else np.nan

    def rank(self, a, method):
        cands = self.complements(a)
        if method == "Baseline: most popular":
            key = lambda b: self.item_orders[b]
        elif method == "History: most likely add-on":
            key = lambda b: self.p_addon(a, b)
        elif method == "Popular x profit":
            key = lambda b: self.item_orders[b] * self.profit[b]
        else:  # History x profit
            key = lambda b: self.p_addon(a, b) * self.profit[b]
        return sorted(cands, key=key, reverse=True)


TILL_METHOD = "Popular x profit"  # chosen by the May-Jun validation (see docs/menu_engineering.md)


def till_suggestions(m: BranchModel, branch: str) -> pd.DataFrame:
    rows = []
    for a in sorted(m.profit.index):
        for rank, b in enumerate(m.rank(a, TILL_METHOD)[:TOP_K], 1):
            rows.append({"branch": branch, "customer_orders": a, "rank": rank, "suggest": b,
                         "p_also_buys_pct": round(m.p_addon(a, b) * 100, 1),
                         "times_bought_together_6mo": m.co[a][b],
                         "lift": round(m.lift(a, b), 2),
                         "addon_profit_per_unit": round(m.profit[b], 2),
                         "expected_profit_per_suggestion": round(m.p_addon(a, b) * m.profit[b], 3)})
    return pd.DataFrame(rows)


def combos(m: BranchModel, branch: str) -> pd.DataFrame:
    cands = []
    for a in m.profit.index:
        for b in m.complements(a):
            if m.co[a][b] < MIN_PAIR_ORDERS:
                continue
            pool = m.single_orders[a] * m.p_addon(a, b) * m.profit[b]
            cands.append((pool, a, b))
    cands.sort(reverse=True)
    used_anchor, used_addon, rows = set(), Counter(), []
    for pool, a, b in cands:
        if a in used_anchor or b in used_anchor or used_addon[b] >= MAX_ADDON_REUSE or (b, a) in {(r["anchor"], r["add_on"]) for r in rows}:
            continue
        used_anchor.add(a)
        used_addon[b] += 1
        separate = m.price[a] + m.price[b]
        bundle = separate * (1 - BUNDLE_DISCOUNT)
        bundle_profit = bundle - m.cost[a] - m.cost[b]
        rows.append({"branch": branch, "combo": f"{a} + {b}", "anchor": a, "add_on": b,
                     "times_bought_together_6mo": m.co[a][b], "lift": round(m.lift(a, b), 2),
                     "p_add_on_pct": round(m.p_addon(a, b) * 100, 1),
                     "anchor_single_item_orders_6mo": m.single_orders[a],
                     "price_separate": round(separate, 2), "bundle_price": round(bundle, 2),
                     "bundle_profit": round(bundle_profit, 2),
                     "extra_profit_vs_anchor_alone": round(bundle_profit - m.profit[a], 2),
                     "profit_pool_6mo_usd": round(pool, 0)})
        if len(rows) == COMBOS_PER_BRANCH:
            break
    return pd.DataFrame(rows)


def validate(df: pd.DataFrame, is_drink: pd.Series) -> pd.DataFrame:
    methods = ["Baseline: most popular", "History: most likely add-on", "History x profit", "Popular x profit"]
    rows = []
    for branch in BRANCHES:
        s = df[df.Branch == branch]
        train = BranchModel(s[s.Date < SPLIT_DATE], is_drink)
        test_baskets = s[s.Date >= SPLIT_DATE].groupby("Transaction ID").Product.apply(lambda x: tuple(sorted(set(x))))
        cases = [(a, b) for items in test_baskets if len(items) == 2
                 for a, b in (items, items[::-1]) if is_drink[a] != is_drink[b]]
        # record per test order so the bootstrap keeps both directions of an order together
        hit = np.zeros((len(cases), len(methods)))
        prof = np.zeros_like(hit)
        for i, (a, b) in enumerate(cases):
            for j, meth in enumerate(methods):
                if b in train.rank(a, meth)[:TOP_K]:
                    hit[i, j] = 1
                    prof[i, j] = train.profit.get(b, 0)
        order_id = np.repeat(np.arange(len(cases) // 2), 2)
        rng = np.random.default_rng(7)
        n_orders = len(cases) // 2
        boot = []
        for _ in range(N_BOOT):
            pick = rng.integers(0, n_orders, n_orders)
            idx = (pick[:, None] * 2 + np.array([0, 1])).ravel()
            boot.append(prof[idx].mean(axis=0))
        boot = np.array(boot)
        for j, meth in enumerate(methods):
            gain = boot[:, j] - boot[:, 0]
            rows.append({"branch": branch, "method": meth, "test_drink_food_orders": n_orders,
                         "top3_hit_rate_pct": round(hit[:, j].mean() * 100, 1),
                         "profit_captured_per_suggestion_usd": round(prof[:, j].mean(), 3),
                         "gain_vs_baseline_usd": round(prof[:, j].mean() - prof[:, 0].mean(), 3),
                         "gain_ci95_low": round(np.percentile(gain, 2.5), 3),
                         "gain_ci95_high": round(np.percentile(gain, 97.5), 3)})
        assert order_id.size == len(cases)
    return pd.DataFrame(rows)


def plot_validation(res: pd.DataFrame, path: Path) -> None:
    style.apply()
    methods = list(dict.fromkeys(res.method))
    colors = [style.MUTED, style.SERIES[0], style.SERIES[1], style.SERIES[2]]
    fig, ax = plt.subplots(figsize=(10, 4.4))
    width = 0.2
    x = np.arange(len(BRANCHES))
    for j, meth in enumerate(methods):
        r = res[res.method == meth].set_index("branch").loc[BRANCHES]
        bars = ax.bar(x + (j - 1.5) * width, r.profit_captured_per_suggestion_usd, width,
                      color=colors[j], edgecolor=style.SURFACE, linewidth=2, label=meth)
        for bar, v in zip(bars, r.profit_captured_per_suggestion_usd):
            ax.text(bar.get_x() + bar.get_width() / 2, v + 0.004, f"${v:.2f}", ha="center",
                    va="bottom", fontsize=8, color=style.INK_2)
    ax.set_xticks(x, BRANCHES)
    ax.set_ylabel("Profit captured per suggestion (USD)")
    ax.set_title("Till suggestions tested on May-Jun: profit captured per suggestion, by branch", pad=26)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=4, fontsize=9)
    ax.set_ylim(0, res.profit_captured_per_suggestion_usd.max() * 1.25)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    df = load_clean()
    is_drink = df.groupby("Product").Category.first().isin(DRINK_CATEGORIES)

    sugg, combo = [], []
    for branch in BRANCHES:
        m = BranchModel(df[df.Branch == branch], is_drink)
        sugg.append(till_suggestions(m, branch))
        combo.append(combos(m, branch))
    sugg, combo = pd.concat(sugg), pd.concat(combo)
    sugg.to_csv(TABLES / "till_suggestions_by_branch.csv", index=False)
    combo.to_csv(TABLES / "branch_combos.csv", index=False)

    res = validate(df, is_drink)
    res.to_csv(TABLES / "branch_combos_validation.csv", index=False)
    plot_validation(res, FIGS / "branch_combos_validation.png")

    pd.set_option("display.width", 220)
    cols = ["combo", "times_bought_together_6mo", "lift", "p_add_on_pct", "bundle_price",
            "bundle_profit", "extra_profit_vs_anchor_alone", "profit_pool_6mo_usd"]
    for branch in BRANCHES:
        print(f"\n=== {branch}: top combos ===")
        print(combo[combo.branch == branch][cols].to_string(index=False))
    print("\n=== Validation (learn Jan-Apr, test May-Jun) ===")
    print(res.drop(columns="test_drink_food_orders").to_string(index=False))


if __name__ == "__main__":
    main()
