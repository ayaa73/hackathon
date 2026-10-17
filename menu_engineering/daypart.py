"""Time of day: the menu dimension we had not used, and why suggestions can steer customers.

1. Daypart menu matrix (morning 7-10, day 11-18, night 19-23): which items change class
   with the time of day, and is that stable between Jan-Mar and Apr-Jun?
2. Till rule by branch x daypart vs branch only: learn on Jan-Apr, test on May-Jun
   drink + food orders. Which rule captures more profit per suggestion?
3. Steerability: do members have a "usual" order? Compare how often a member's visit
   repeats an item they bought before with what random choice (weighted by item
   popularity, same visit sizes) would give. If they match, choices are not habits,
   so what the menu shows and staff suggest decides much of what is bought.

Run from the repo root (after branch_combos.py):  python menu_engineering/daypart.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

from src.clean import load_clean  # noqa: E402
from src import style  # noqa: E402
from menu_engineering.menu_matrix import CLASSES, classify  # noqa: E402
from menu_engineering.branch_combos import (BRANCHES, DRINK_CATEGORIES, SPLIT_DATE, TOP_K,  # noqa: E402
                                            BranchModel)

TABLES = ROOT / "outputs" / "tables"
FIGS = ROOT / "outputs" / "figures"
DAYPARTS = ["morning", "day", "night"]
DAYPART_LABEL = {"morning": "Morning 7-10", "day": "Day 11-18", "night": "Night 19-23"}
STABILITY_SPLIT = pd.Timestamp("2026-04-01")
N_BOOT = 1000
N_NULL_SIMS = 20


def add_daypart(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["daypart"] = pd.cut(df.hour, [6, 10, 18, 24], labels=DAYPARTS).astype(str)
    return df


def daypart_matrix(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    full, rows = {}, []
    for dp in DAYPARTS:
        s = df[df.daypart == dp]
        p, th = classify(s)
        full[dp] = p.set_index("Product")["class"]
        a, _ = classify(s[s.Date < STABILITY_SPLIT])
        b, _ = classify(s[s.Date >= STABILITY_SPLIT])
        same = (a.set_index("Product")["class"] == b.set_index("Product")["class"].reindex(a.Product)).mean()
        rows.append({"daypart": dp, "orders": s["Transaction ID"].nunique(),
                     "avg_profit_per_unit": round(th["profit_threshold_usd"], 2),
                     "same_class_jan_mar_vs_apr_jun_pct": round(same * 100, 1)})
    classes = pd.DataFrame(full)
    return classes, pd.DataFrame(rows)


def validate_rules(df: pd.DataFrame, is_drink: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Popular x profit suggestions learned per branch vs per branch x daypart."""
    out, rules = [], []
    for branch in BRANCHES:
        s = df[df.Branch == branch]
        train, test = s[s.Date < SPLIT_DATE], s[s.Date >= SPLIT_DATE]
        branch_model = BranchModel(train, is_drink)
        dp_models = {dp: BranchModel(train[train.daypart == dp], is_drink) for dp in DAYPARTS}
        test_orders = test.groupby("Transaction ID").agg(items=("Product", lambda x: tuple(sorted(set(x)))),
                                                         dp=("daypart", "first"))
        prof = []
        for items, dp in zip(test_orders["items"], test_orders.dp):
            if len(items) != 2 or is_drink[items[0]] == is_drink[items[1]]:
                continue
            row = [0.0, 0.0]
            for a, b in (items, items[::-1]):
                if b in branch_model.rank(a, "Popular x profit")[:TOP_K]:
                    row[0] += branch_model.profit.get(b, 0)
                m = dp_models[dp]
                if a in m.profit.index and b in m.rank(a, "Popular x profit")[:TOP_K]:
                    row[1] += m.profit.get(b, 0)
            prof.append(row)
        prof = np.array(prof) / 2  # per suggestion (two suggestions per order)
        rng = np.random.default_rng(3)
        boots = np.array([prof[rng.integers(0, len(prof), len(prof))].mean(axis=0) for _ in range(N_BOOT)])
        gain = boots[:, 1] - boots[:, 0]
        out.append({"branch": branch, "test_drink_food_orders": len(prof),
                    "branch_rule_profit_per_suggestion": round(prof[:, 0].mean(), 3),
                    "branch_x_daypart_rule_profit_per_suggestion": round(prof[:, 1].mean(), 3),
                    "gain_usd": round(prof[:, 1].mean() - prof[:, 0].mean(), 3),
                    "gain_ci95_low": round(np.percentile(gain, 2.5), 3),
                    "gain_ci95_high": round(np.percentile(gain, 97.5), 3)})

        # Full-period rule table: what to suggest by branch and daypart
        for dp in DAYPARTS:
            m = BranchModel(s[s.daypart == dp], is_drink)
            drinks = [p for p in m.profit.index if is_drink[p]]
            foods = [p for p in m.profit.index if not is_drink[p]]
            rules.append({"branch": branch, "daypart": DAYPART_LABEL[dp],
                          "drink_alone_suggest": ", ".join(m.rank(drinks[0], "Popular x profit")[:TOP_K]),
                          "food_alone_suggest": ", ".join(m.rank(foods[0], "Popular x profit")[:TOP_K])})
    return pd.DataFrame(out), pd.DataFrame(rules)


def steerability(df: pd.DataFrame) -> pd.DataFrame:
    m = df.dropna(subset=["Customer ID"]).sort_values(["Customer ID", "Date", "Time"])
    visits = m.groupby(["Customer ID", "Transaction ID"], sort=False).Product.apply(set)

    def repeat_rate(visit_sets):
        hit = tot = 0
        for _, sets in visit_sets.groupby(level=0, sort=False):
            seen = set()
            for items in sets.values:
                tot += 1
                hit += bool(items & seen)
                seen |= items
        return hit / tot

    observed = repeat_rate(visits)
    pop = df.groupby("Product").Quantity.sum()
    names, p = pop.index.values, (pop / pop.sum()).values
    sizes = visits.apply(len)
    rng = np.random.default_rng(5)
    sims = []
    for _ in range(N_NULL_SIMS):
        fake = pd.Series([set(rng.choice(names, size=k, replace=False, p=p)) for k in sizes.values],
                         index=sizes.index)
        sims.append(repeat_rate(fake))
    distinct = m.groupby("Customer ID").Product.nunique()
    nvis = m.groupby("Customer ID")["Transaction ID"].nunique()
    return pd.DataFrame([{
        "members": len(distinct), "median_visits": float(nvis.median()),
        "median_distinct_items": float(distinct.median()),
        "observed_repeat_rate_pct": round(observed * 100, 1),
        "random_choice_repeat_rate_pct": round(np.mean(sims) * 100, 1),
        "random_choice_range_pct": f"{min(sims) * 100:.1f}-{max(sims) * 100:.1f}",
        "conclusion": ("no habit beyond popularity: choices are steerable"
                       if min(sims) - 0.005 <= observed <= max(sims) + 0.005 else "habits exist")}])


def plot_changes(classes: pd.DataFrame, path: Path) -> None:
    changed = classes[classes.nunique(axis=1) > 1]
    order = changed.apply(lambda r: CLASSES.index(r["morning"]), axis=1).sort_values().index
    changed = changed.loc[order]
    style.apply()
    fig, ax = plt.subplots(figsize=(8.5, 0.42 * len(changed) + 1.6))
    for i, (prod, r) in enumerate(changed.iterrows()):
        for j, dp in enumerate(DAYPARTS):
            st = style.CLASS_STYLE[r[dp]]
            ax.add_patch(plt.Rectangle((j + 0.04, i + 0.08), 0.92, 0.84, color=st["color"], lw=0))
            ax.text(j + 0.5, i + 0.5, st["label"], ha="center", va="center", fontsize=8.5,
                    color="white" if r[dp] in ("STAR", "PLOWHORSE") else style.INK, weight="bold")
    ax.set_xlim(0, 3)
    ax.set_ylim(len(changed), 0)
    ax.set_xticks([0.5, 1.5, 2.5], [DAYPART_LABEL[d] for d in DAYPARTS])
    ax.xaxis.tick_top()
    ax.set_yticks(np.arange(len(changed)) + 0.5, changed.index)
    ax.grid(False)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.tick_params(length=0)
    ax.set_title(f"{len(changed)} items change class with the time of day", pad=28)
    ax.legend(handles=[Patch(color=style.CLASS_STYLE[c]["color"], label=style.CLASS_STYLE[c]["label"]) for c in CLASSES],
              loc="upper center", bbox_to_anchor=(0.5, -0.01), ncol=4, fontsize=9)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    df = add_daypart(load_clean())
    is_drink = df.groupby("Product").Category.first().isin(DRINK_CATEGORIES)

    classes, stability = daypart_matrix(df)
    classes.to_csv(TABLES / "daypart_classes.csv")
    stability.to_csv(TABLES / "daypart_stability.csv", index=False)
    plot_changes(classes, FIGS / "daypart_class_changes.png")

    validation, rules = validate_rules(df, is_drink)
    validation.to_csv(TABLES / "daypart_rule_validation.csv", index=False)
    rules.to_csv(TABLES / "daypart_till_rules.csv", index=False)

    steer = steerability(df)
    steer.to_csv(TABLES / "steerability.csv", index=False)

    pd.set_option("display.width", 220)
    changed = classes[classes.nunique(axis=1) > 1]
    print(f"Items changing class by daypart: {len(changed)}\n{changed}\n")
    print(stability.to_string(index=False), "\n")
    print(validation.to_string(index=False), "\n")
    print(rules.to_string(index=False), "\n")
    print(steer.T.to_string(header=False))


if __name__ == "__main__":
    main()
