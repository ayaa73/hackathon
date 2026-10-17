"""Truck menu economics from the chain's measured sales mix.

Run from the repo root:
    python truck/truck_menu.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from src.clean import GP, REV, load_clean  # noqa: E402
from src import style  # noqa: E402

# Chart style is applied by the scenario script. Touch the palette here so this
# file uses the same module the brief requires.
_ = style.SERIES

TABLES = ROOT / "outputs" / "tables"

# Planning multiple. The measured chain ratio is printed beside it.
# 1.59 is that ratio rounded to two decimals (quantity / orders).
ITEMS_PER_ORDER = 1.59

# Easy to carry, no hot kitchen. Order here is the menu order, not popularity.
DRINKS = [
    "Cold Brew",
    "Iced Latte",
    "Iced Matcha",
    "Classic Matcha",
    "Iced Americano",
    "Americano",
    "Cappuccino",
    "Spanish Latte",
    "Lemonade",
    "Peach Iced Tea",
    "Still Water",
]
FOOD = [
    "Butter Croissant",
    "Chocolate Cookie",
    "Pistachio Cookie",
    "Brownie",
    "Banana Bread",
]

# prep is one of batch-brewed / espresso / packaged.
# "espresso" means made to order on the bar, including matcha whisked per cup.
# storage is ambient or chilled (milk and ice count as chilled).
PREP = {
    "Cold Brew": "batch-brewed",
    "Iced Latte": "espresso",
    "Iced Matcha": "espresso",
    "Classic Matcha": "espresso",
    "Iced Americano": "espresso",
    "Americano": "espresso",
    "Cappuccino": "espresso",
    "Spanish Latte": "espresso",
    "Lemonade": "batch-brewed",
    "Peach Iced Tea": "batch-brewed",
    "Still Water": "packaged",
    "Butter Croissant": "packaged",
    "Chocolate Cookie": "packaged",
    "Pistachio Cookie": "packaged",
    "Brownie": "packaged",
    "Banana Bread": "packaged",
}
STORAGE = {
    "Cold Brew": "chilled",
    "Iced Latte": "chilled",
    "Iced Matcha": "chilled",
    "Classic Matcha": "chilled",
    "Iced Americano": "chilled",
    "Americano": "ambient",
    "Cappuccino": "chilled",
    "Spanish Latte": "chilled",
    "Lemonade": "chilled",
    "Peach Iced Tea": "chilled",
    "Still Water": "ambient",
    "Butter Croissant": "ambient",
    "Chocolate Cookie": "ambient",
    "Pistachio Cookie": "ambient",
    "Brownie": "ambient",
    "Banana Bread": "ambient",
}

# Left off the truck. Reasons are operational, not a sales judgement.
EXCLUDED = [
    ("Chicken Pesto Sandwich", "sandwich", "Needs assembly and a protein cold chain. Spoils on a truck with no kitchen."),
    ("Tuna Sandwich", "sandwich", "Needs assembly and a protein cold chain. Spoils on a truck with no kitchen."),
    ("Turkey & Cheese Sandwich", "sandwich", "Needs assembly and a protein cold chain. Spoils on a truck with no kitchen."),
    ("Halloumi Wrap", "wrap", "Needs a grill or assembly and does not travel as ambient stock."),
    ("Chicken Salad Bowl", "bowl", "Cold kitchen and a short shelf life. Not a pre-packed ambient item."),
    ("Quinoa Bowl", "bowl", "Cold kitchen and a short shelf life. Not a pre-packed ambient item."),
    ("Soup of the Day", "soup", "Needs a hot kitchen and a hot hold. The truck has neither."),
    ("Avocado Toast", "breakfast", "Made to order. Avocado spoils and needs a kitchen."),
    ("Egg Sandwich", "breakfast", "Needs a hot kitchen and a protein cold chain."),
    ("Granola Yoghurt", "breakfast", "Needs a cold chain all day. Not ambient stock."),
    ("Cheesecake Slice", "dessert", "Needs a cold chain and spoils. Cut cakes do not travel well."),
    ("Tiramisu Cup", "dessert", "Needs a cold chain and spoils."),
    ("Frozen Yoghurt Cup", "dessert", "Needs a freezer, not a cooler box."),
]


def build(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Sales-mix-weighted unit economics for the truck items. All MEASURED."""
    names = DRINKS + FOOD
    missing = [name for name in names if name not in set(df["Product"])]
    if missing:
        raise SystemExit(f"Truck items missing from the data: {missing}")

    chain_units = df["Quantity"].sum()
    rows = (
        df[df["Product"].isin(names)]
        .groupby("Product", as_index=False)
        .agg(
            units=("Quantity", "sum"),
            revenue=(REV, "sum"),
            gross_profit=(GP, "sum"),
            avg_price=("Unit Price (USD)", "mean"),
            avg_unit_cost=("Unit Cost (USD)", "mean"),
        )
    )
    rows["group"] = rows["Product"].map(lambda name: "drink" if name in DRINKS else "food")
    rows["prep"] = rows["Product"].map(PREP)
    rows["storage"] = rows["Product"].map(STORAGE)
    # List price minus list cost. Discounts are not in this unit figure.
    rows["profit_per_unit"] = rows["avg_price"] - rows["avg_unit_cost"]
    rows["margin_pct"] = rows["profit_per_unit"] / rows["avg_price"] * 100
    rows["chain_sales_mix_share"] = rows["units"] / chain_units
    rows["menu_order"] = rows["Product"].map({name: i for i, name in enumerate(names)})
    rows = rows.sort_values("menu_order").drop(columns="menu_order")

    weight = rows["units"]
    price = (rows["avg_price"] * weight).sum() / weight.sum()
    cost = (rows["avg_unit_cost"] * weight).sum() / weight.sum()
    profit = price - cost
    margin = profit / price * 100
    measured_items = df["Quantity"].sum() / df["Transaction ID"].nunique()

    summary = pd.DataFrame(
        [
            {
                "metric": "items_per_order",
                "value": ITEMS_PER_ORDER,
                "kind": "MEASURED",
                "note": (
                    f"Chain quantity / orders = {measured_items:.4f}, "
                    f"rounded to {ITEMS_PER_ORDER:.2f} for the ticket."
                ),
            },
            {
                "metric": "weighted_avg_price",
                "value": price,
                "kind": "MEASURED",
                "note": "Mean list price of each truck item, weighted by units sold.",
            },
            {
                "metric": "weighted_avg_cost",
                "value": cost,
                "kind": "MEASURED",
                "note": "Mean unit cost of each truck item, weighted by units sold.",
            },
            {
                "metric": "weighted_profit_per_item",
                "value": profit,
                "kind": "MEASURED",
                "note": "Weighted list price minus weighted unit cost. Discounts excluded.",
            },
            {
                "metric": "weighted_margin_pct",
                "value": margin,
                "kind": "MEASURED",
                "note": "Weighted profit per item / weighted price.",
            },
            {
                "metric": "ticket_per_order",
                "value": price * ITEMS_PER_ORDER,
                "kind": "ESTIMATE",
                "note": "ASSUMPTION: a truck order contains 1.59 items, same as the chain, at this mix.",
            },
            {
                "metric": "product_profit_per_order",
                "value": profit * ITEMS_PER_ORDER,
                "kind": "ESTIMATE",
                "note": "ASSUMPTION: same 1.59 items/order. This is product margin only, before labour and fees.",
            },
        ]
    )
    columns = [
        "Product", "group", "prep", "storage", "avg_price", "avg_unit_cost",
        "profit_per_unit", "margin_pct", "units", "chain_sales_mix_share",
    ]
    return rows[columns], summary


def main() -> None:
    menu, summary = build(load_clean())
    TABLES.mkdir(parents=True, exist_ok=True)
    menu_path = TABLES / "truck_menu.csv"
    summary_path = TABLES / "truck_menu_summary.csv"
    menu.to_csv(menu_path, index=False, float_format="%.4f")
    summary.to_csv(summary_path, index=False, float_format="%.4f")

    by_name = {row.metric: row.value for row in summary.itertuples()}
    print("Truck menu (MEASURED unit economics, weighted by chain units)")
    print(f"  Price per item:     ${by_name['weighted_avg_price']:.2f}")
    print(f"  Cost per item:      ${by_name['weighted_avg_cost']:.2f}")
    print(f"  Profit per item:    ${by_name['weighted_profit_per_item']:.2f}")
    print(f"  Margin:             {by_name['weighted_margin_pct']:.1f}%")
    print(f"  Ticket / order:     ${by_name['ticket_per_order']:.2f}  (ESTIMATE, x {ITEMS_PER_ORDER})")
    print(f"  Product profit:     ${by_name['product_profit_per_order']:.2f}  (ESTIMATE, x {ITEMS_PER_ORDER})")
    print("Excluded (not on the truck):")
    for product, kind, reason in EXCLUDED:
        print(f"  - {product} ({kind}): {reason}")
    print(f"Saved -> {menu_path.relative_to(ROOT)}")
    print(f"Saved -> {summary_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
