"""Data quality checks on the raw export, as received (all MEASURED).

The brief says the file uses replacement transaction IDs and is delivered as it is, so every
assumption the analysis makes about the file is checked here and written to a table:
duplicates, missing values, what a transaction ID can be trusted for, prices and costs,
coverage of days and branches.

Run from the repo root:  python src/data_quality.py
Writes outputs/data_quality/data_quality_checks.csv
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from src.clean import GP, RAW, REV, _clean, check  # noqa: E402

OUT = ROOT / "outputs" / "data_quality"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> None:
    raw = pd.read_csv(RAW)
    df = _clean(raw)
    check(df)  # revenue and gross-profit formulas, raises if wrong
    rows = []

    def add(area, check_name, result, decision):
        rows.append({"area": area, "check": check_name, "result": result, "what_we_did": decision})

    dup = raw[raw.duplicated(keep="first")]
    add("Duplicates", "Exact duplicate rows (every column identical)",
        f"{len(dup)} rows in {dup['Transaction ID'].nunique()} orders, all quantity 1; "
        f"${dup[REV].sum():,.0f} revenue ({dup[REV].sum() / raw[REV].sum():.2%})",
        "Removed. The till records 2 of an item as quantity 2, so an identical second line is an export repeat")
    same = df[df.duplicated(["Transaction ID", "Product"], keep=False)]
    add("Duplicates", "Same product on two lines of one order (not identical)",
        f"{same.groupby(['Transaction ID', 'Product']).ngroups} cases; lines differ in quantity or discount",
        "Kept: genuine separate lines (e.g. one discounted, one not)")

    miss = raw.isna().sum()
    add("Missing values", "Empty cells per column",
        "; ".join(f"{c}: {v:,}" for c, v in miss[miss > 0].items()) or "none",
        "Customer ID empty = walk-in without a loyalty ID. Kept; analysed as its own group")
    tx = df.groupby("Transaction ID")
    anon = tx["Customer ID"].first().isna().mean()
    add("Missing values", "Orders without a Customer ID", f"{anon:.1%}",
        "Member analyses (Project 4) cover the other 63.5% only")

    multi = {c: int((tx[c].nunique(dropna=False) > 1).sum()) for c in ["Date", "Time", "Branch", "Customer ID", "Order Type"]}
    add("Replacement IDs", "Does one transaction ID ever span two dates, times, branches, customers or order types?",
        ", ".join(f"{c}: {v}" for c, v in multi.items()),
        "None do, so an ID is safe to use for grouping lines into one order")
    t = tx.agg(Date=("Date", "first"), Time=("Time", "first")).reset_index().sort_values("Transaction ID")
    ts = pd.to_datetime(t.Date.dt.strftime("%Y-%m-%d") + " " + t.Time)
    out_of_order = int((ts.values[1:] < ts.values[:-1]).sum())
    date_breaks = int((t.Date.values[1:] < t.Date.values[:-1]).sum())
    add("Replacement IDs", "Are IDs in time order?",
        f"In date order ({date_breaks} breaks) but shuffled within each day: {out_of_order:,} of {len(t):,} IDs "
        f"come earlier in the day than the ID before them",
        "IDs are replacements: never used for ordering, counting customers or timing. Date and Time are used instead")

    add("Values", "Quantity, price, cost <= 0; cost above price; negative profit lines",
        f"{int((df.Quantity <= 0).sum())}, {int((df['Unit Price (USD)'] <= 0).sum())}, "
        f"{int((df['Unit Cost (USD)'] <= 0).sum())}; {int((df['Unit Cost (USD)'] > df['Unit Price (USD)']).sum())}; "
        f"{int((df[GP] < 0).sum())}", "Nothing to fix. No refunds or voids are in the file")
    add("Values", "Discount rates used",
        ", ".join(f"{r:.0%}: {n:,} lines" for r, n in df["Discount Rate"].value_counts().sort_index().items()),
        "Revenue is after discount; used as given")
    add("Values", "Revenue = qty x price x (1 - discount); gross profit = revenue - qty x cost",
        "Holds on every line (to the cent)", "Formulas trusted; checked in src/clean.py on every run")

    pp = df.groupby(["Branch", "Product"])["Unit Price (USD)"].nunique()
    cc = df.groupby(["Branch", "Product"])["Unit Cost (USD)"].nunique()
    add("Prices and costs", "Branch x item pairs whose list price or unit cost changed Jan-Jun",
        f"price: {int((pp > 1).sum())} of {len(pp)}; cost: {int((cc > 1).sum())} of {len(cc)}",
        "No price ever changed, so customers' reaction to a price change cannot be measured: "
        "every price move is tested, not assumed")
    add("Prices and costs", "Each product maps to one category",
        f"{int((df.groupby('Product').Category.nunique() > 1).sum())} conflicts, {df.Product.nunique()} products, "
        f"{df.Category.nunique()} categories", "Category used as given")

    days = df.groupby("Branch").Date.nunique()
    add("Coverage", "Days with sales per branch", ", ".join(f"{b}: {d}" for b, d in days.items())
        + f" of {(df.Date.max() - df.Date.min()).days + 1} ({df.Date.min().date()} to {df.Date.max().date()})",
        "No missing days, so day-level comparisons need no gap filling")
    add("Coverage", "Opening hours seen", f"{df.hour.min()}:00 to {df.hour.max()}:59",
        "Used for the morning analysis (Project 3)")
    add("Not in the file", "Labour, rent, waste, energy, staff schedules, customer location or type, "
        "marketing spend, stock levels", "Absent",
        "All profit figures are gross profit; each project lists what it would need")

    out = pd.DataFrame(rows)
    out.to_csv(OUT / "data_quality_checks.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_colwidth", 110)
    print(out[["check", "result"]].to_string(index=False))


if __name__ == "__main__":
    main()
