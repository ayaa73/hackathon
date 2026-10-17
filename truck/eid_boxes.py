"""Eid boxes from pastries the branches already sell, plus a limited edition.

Box contents are chosen from measured popularity and profit. Limited-edition
prices are analogies to measured items and are labelled ESTIMATE.

Run from the repo root, after truck/holiday_dips.py:
    python truck/eid_boxes.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from src.clean import GP, REV, load_clean  # noqa: E402
from src import style  # noqa: E402

_ = style.SERIES  # same palette as the charts; this script writes tables

TABLES = ROOT / "outputs" / "tables"
DIPS = TABLES / "eid_holiday_dips.csv"

# Ambient pastries already on the menu. No new SKU in the box itself.
BOX_ITEMS = [
    "Butter Croissant",
    "Chocolate Croissant",
    "Almond Croissant",
    "Cinnamon Roll",
    "Banana Bread",
    "Brownie",
    "Chocolate Cookie",
    "Pistachio Cookie",
]
BOX_SIZES = {"Box of 6": 6, "Family box of 12": 12}

# ESTIMATE. A box discount, not observed in the file.
BOX_DISCOUNT = 0.10
# ESTIMATE. One-time bags, cards, and a week of Instagram/WhatsApp posts.
PACKAGING_AND_PROMOTION = 500

# Limited edition is not in the file. Price each like a measured item.
# Ma'amoul tradition: see docs/truck_sources.md (L'Orient Today).
LIMITED = [
    ("Ma'amoul (date / pistachio / walnut)", "Pistachio Cookie"),
    ("Pistachio baklava", "Cinnamon Roll"),
    ("Rose-pistachio latte", "Spanish Latte"),
]

# Retail benchmarks. Not Stories prices. See docs/truck_sources.md.
# Hallab international shop, box of 12 large pieces.
HALLAB_LARGE_12 = {"pistachio": 36.0, "walnut": 28.0, "dates": 24.0}
# Beirut.com phone survey, 28 Mar 2024, Hallab per kilo.
HALLAB_2024_PER_KG = {"pistachio": 22.0, "walnut": 17.0, "dates": 15.0}


def item_economics(df: pd.DataFrame) -> pd.DataFrame:
    rows = (
        df[df["Product"].isin(BOX_ITEMS)]
        .groupby(["Branch", "Product"], as_index=False)
        .agg(
            units=("Quantity", "sum"),
            list_price=("Unit Price (USD)", "mean"),
            unit_cost=("Unit Cost (USD)", "mean"),
        )
    )
    rows["profit_per_unit"] = rows["list_price"] - rows["unit_cost"]
    return rows


def chain_scores(df: pd.DataFrame) -> pd.Series:
    """Popularity x profit, both scaled 0-1, so neither one dominates the mix."""
    chain = (
        df[df["Product"].isin(BOX_ITEMS)]
        .groupby("Product")
        .agg(units=("Quantity", "sum"), price=("Unit Price (USD)", "mean"), cost=("Unit Cost (USD)", "mean"))
    )
    profit = chain["price"] - chain["cost"]
    score = (chain["units"] / chain["units"].max()) * (profit / profit.max())
    return score.sort_values(ascending=False)


def allocate(score: pd.Series, pieces: int) -> dict[str, int]:
    """Largest-remainder allocation. Every item with a positive score can appear."""
    raw = pieces * score / score.sum()
    counts = {item: int(raw[item]) for item in raw.index}
    left = pieces - sum(counts.values())
    remainder = sorted(raw.index, key=lambda item: raw[item] - counts[item], reverse=True)
    for item in remainder[:left]:
        counts[item] += 1
    return {item: count for item, count in counts.items() if count > 0}


def mix_label(counts: dict[str, int]) -> str:
    return "; ".join(f"{count} {item}" for item, count in counts.items())


def build_boxes(econ: pd.DataFrame, mixes: dict[str, dict[str, int]]) -> pd.DataFrame:
    rows = []
    for box, counts in mixes.items():
        for branch, part in econ.groupby("Branch"):
            part = part.set_index("Product")
            price = 0.0
            cost = 0.0
            for item, count in counts.items():
                price += count * float(part.loc[item, "list_price"])
                cost += count * float(part.loc[item, "unit_cost"])
            sell = price * (1 - BOX_DISCOUNT)
            profit = sell - cost
            rows.append({
                "item": box,
                "kind": "MEASURED mix, ESTIMATE 10% box discount",
                "branch": branch,
                "mix": mix_label(counts),
                "list_price": price,
                "box_price": sell,
                "box_cost": cost,
                "box_profit": profit,
                "margin_pct": profit / sell * 100,
            })
    return pd.DataFrame(rows)


def limited_edition(df: pd.DataFrame) -> pd.DataFrame:
    """Chain-level analogy. Cost ratio copied from the measured reference item."""
    chain = (
        df.groupby("Product")
        .agg(price=("Unit Price (USD)", "mean"), cost=("Unit Cost (USD)", "mean"))
    )
    rows = []
    for name, reference in LIMITED:
        price = float(chain.loc[reference, "price"])
        ratio = float(chain.loc[reference, "cost"] / chain.loc[reference, "price"])
        cost = price * ratio
        rows.append({
            "item": name,
            "kind": "ESTIMATE",
            "branch": "Chain analogy",
            "mix": f"priced like {reference}; cost ratio copied from that item ({ratio:.3f})",
            "list_price": price,
            "box_price": price,
            "box_cost": cost,
            "box_profit": price - cost,
            "margin_pct": (price - cost) / price * 100,
        })
    return pd.DataFrame(rows)


def targets(df: pd.DataFrame, boxes: pd.DataFrame) -> pd.DataFrame:
    dips = pd.read_csv(DIPS)
    fitr = dips[(dips["holiday"] == "Eid al-Fitr") & (dips["branch"] == "Chain") & (dips["date"] == "TOTAL")].iloc[0]
    revenue_gap = float(fitr["revenue_gap"])  # negative when sales fell
    lost_revenue = -revenue_gap
    chain_margin = df[GP].sum() / df[REV].sum()
    lost_profit = lost_revenue * chain_margin

    # Assemble where the box earns the most. Garden's costs are higher.
    harbour = boxes[boxes["branch"] == "Harbour"].set_index("item")
    rows = [
        {
            "metric": "fitr_revenue_gap",
            "value": revenue_gap,
            "kind": "MEASURED",
            "note": "Chain Eid al-Fitr revenue minus the local same-weekday baseline. From holiday_dips.py.",
        },
        {
            "metric": "chain_gross_margin",
            "value": chain_margin,
            "kind": "MEASURED",
            "note": "Chain gross profit / chain revenue, all items.",
        },
        {
            "metric": "fitr_gross_profit_lost",
            "value": lost_profit,
            "kind": "ESTIMATE",
            "note": "ASSUMPTION: the lost revenue would have earned the chain's measured gross margin.",
        },
        {
            "metric": "packaging_and_promotion",
            "value": PACKAGING_AND_PROMOTION,
            "kind": "ESTIMATE",
            "note": "ASSUMPTION - verify locally. One-time bags, cards, and a week of posts.",
        },
    ]
    for box in BOX_SIZES:
        profit = float(harbour.loc[box, "box_profit"])
        rows.append({
            "metric": f"harbour_{box}_profit",
            "value": profit,
            "kind": "MEASURED costs, ESTIMATE 10% discount",
            "note": "Harbour assembly. Garden costs more; see eid_boxes.csv.",
        })
        rows.append({
            "metric": f"boxes_to_replace_fitr_profit_{box}",
            "value": lost_profit / profit,
            "kind": "ESTIMATE",
            "note": "Fitr gross-profit gap / Harbour box profit. A target, not a forecast.",
        })
        rows.append({
            "metric": f"boxes_to_cover_packaging_{box}",
            "value": PACKAGING_AND_PROMOTION / profit,
            "kind": "ESTIMATE",
            "note": "ASSUMPTION $500 packaging / Harbour box profit.",
        })
    return pd.DataFrame(rows)


def main() -> None:
    if not DIPS.exists():
        raise SystemExit("Missing eid_holiday_dips.csv. Run python truck/holiday_dips.py first.")
    df = load_clean()
    econ = item_economics(df)
    score = chain_scores(df)
    mixes = {name: allocate(score, pieces) for name, pieces in BOX_SIZES.items()}
    boxes = build_boxes(econ, mixes)
    limited = limited_edition(df)
    benchmarks = []
    for filling, box_price in HALLAB_LARGE_12.items():
        benchmarks.append({
            "item": f"Hallab large {filling} ma'amoul, 12-piece box",
            "kind": "RETAIL BENCHMARK",
            "branch": "Hallab international shop",
            "mix": f"${box_price / 12:.2f} per piece. Not a Stories cost.",
            "list_price": box_price,
            "box_price": box_price / 12,
            "box_cost": pd.NA,
            "box_profit": pd.NA,
            "margin_pct": pd.NA,
        })
    for filling, kilo in HALLAB_2024_PER_KG.items():
        benchmarks.append({
            "item": f"Hallab {filling} ma'amoul, per kilo, Mar 2024",
            "kind": "RETAIL BENCHMARK",
            "branch": "Beirut.com phone survey",
            "mix": "Per kilo, not per piece. Size is not the cookie analogy.",
            "list_price": kilo,
            "box_price": kilo,
            "box_cost": pd.NA,
            "box_profit": pd.NA,
            "margin_pct": pd.NA,
        })
    table = pd.concat([boxes, limited, pd.DataFrame(benchmarks)], ignore_index=True)
    goal = targets(df, boxes)

    # Where a box earns less. Measured, not typed in.
    wide = boxes.pivot(index="item", columns="branch", values="box_profit")
    garden_vs_harbour = wide["Garden"] / wide["Harbour"] - 1

    TABLES.mkdir(parents=True, exist_ok=True)
    table.to_csv(TABLES / "eid_boxes.csv", index=False, float_format="%.4f")
    goal.to_csv(TABLES / "eid_box_targets.csv", index=False, float_format="%.4f")

    print("Box mixes (popularity x profit per unit):")
    for name, counts in mixes.items():
        print(f"  {name}: {mix_label(counts)}")
    print("Box profit by branch:")
    for row in boxes.itertuples():
        print(f"  {row.branch} {row.item}: price ${row.box_price:.2f} cost ${row.box_cost:.2f} profit ${row.box_profit:.2f} margin {row.margin_pct:.1f}%")
    print("Garden profit vs Harbour:")
    for box, gap in garden_vs_harbour.items():
        print(f"  {box}: {gap * 100:.1f}%")
    print("Targets:")
    for row in goal.itertuples():
        print(f"  {row.metric}: {row.value:.2f} ({row.kind})")
    print("Saved -> outputs/tables/eid_boxes.csv")
    print("Saved -> outputs/tables/eid_box_targets.csv")


if __name__ == "__main__":
    main()
