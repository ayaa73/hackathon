"""Load and clean the Stories transaction data.

Usage:
    python src/clean.py          # writes data/processed/clean.csv and prints checks

From other scripts:
    from src.clean import load_clean
    df = load_clean()
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "stories_transactions.csv"
PROCESSED = ROOT / "data" / "processed" / "clean.csv"

REV = "Line Revenue (USD)"
GP = "Line Gross Profit (USD)"


def _clean(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.drop_duplicates().copy()  # 132 exact duplicate rows in the raw export
    df["Date"] = pd.to_datetime(df["Date"])
    df["hour"] = df["Time"].str[:2].astype(int)
    df["line_cost"] = df["Quantity"] * df["Unit Cost (USD)"]
    return df.reset_index(drop=True)


def load_clean() -> pd.DataFrame:
    """Return the cleaned DataFrame (duplicates removed, Date parsed, hour added)."""
    return _clean(pd.read_csv(RAW))


def check(df: pd.DataFrame) -> None:
    """Assert the arithmetic in the file is internally consistent."""
    rev = df["Quantity"] * df["Unit Price (USD)"] * (1 - df["Discount Rate"])
    assert (rev.round(2) - df[REV]).abs().max() <= 0.011, "Revenue formula mismatch"
    gp = df[REV] - df["line_cost"]
    assert (gp.round(2) - df[GP]).abs().max() <= 0.011, "Gross profit formula mismatch"


if __name__ == "__main__":
    raw = pd.read_csv(RAW)
    df = _clean(raw)
    check(df)
    PROCESSED.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(PROCESSED, index=False)
    print(f"Raw rows:            {len(raw):,}")
    print(f"Duplicates removed:  {len(raw) - len(df):,}")
    print(f"Clean rows:          {len(df):,}")
    print(f"Transactions:        {df['Transaction ID'].nunique():,}")
    print(f"Date range:          {df['Date'].min().date()} -> {df['Date'].max().date()}")
    print(f"Revenue:             ${df[REV].sum():,.0f}")
    print(f"Gross profit:        ${df[GP].sum():,.0f}")
    print("Integrity checks passed (revenue and gross-profit formulas).")
    print(f"Saved -> {PROCESSED.relative_to(ROOT)}")
