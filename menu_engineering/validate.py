"""Validation checks for Project 1. Fails loudly if any check breaks.

1. No data leakage in the pairing model:
   - train orders all before the split date, test orders all on/after it
   - no transaction appears in both sets; no transaction spans two dates
   - the model's counts are built from train orders only (checked by rebuilding
     them after deleting the test period and getting identical predictions)
2. Stability of the menu matrix: classify items on Jan-Mar, re-classify on Apr-Jun,
   and report how many items keep their class (are the actions robust over time?).
3. Reproducibility: the cleaned data still passes the revenue/profit formula checks.

Run from the repo root:  python menu_engineering/validate.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from src.clean import check, load_clean  # noqa: E402
from menu_engineering.menu_matrix import classify  # noqa: E402
from menu_engineering.pairing_model import SPLIT_DATE, baskets, evaluate  # noqa: E402

TABLES = ROOT / "outputs" / "tables"
STABILITY_SPLIT = pd.Timestamp("2026-04-01")


def main() -> None:
    df = load_clean()
    check(df)
    print("[ok] revenue and gross-profit formulas hold on every row")

    cat = df.groupby("Product").Category.first()  # static product metadata, not a learned value
    b = baskets(df)
    multi = b[b["items"].str.len() >= 2]
    train, test = multi[multi.Date < SPLIT_DATE], multi[multi.Date >= SPLIT_DATE]

    assert train.Date.max() < SPLIT_DATE <= test.Date.min(), "train/test dates overlap"
    assert not set(train["Transaction ID"]) & set(test["Transaction ID"]), "a transaction is in both sets"
    assert (df.groupby("Transaction ID").Date.nunique() == 1).all(), "a transaction spans two dates"
    print(f"[ok] time split: train {train.Date.min().date()}..{train.Date.max().date()} "
          f"({len(train):,} orders) | test {test.Date.min().date()}..{test.Date.max().date()} ({len(test):,} orders)")
    print("[ok] no transaction shared between train and test")

    # Leakage test: results must be identical when the model is built from a dataset
    # in which the test period never existed.
    df_train_only = df[df.Date < SPLIT_DATE]
    b_train_only = baskets(df_train_only)
    train_only = b_train_only[b_train_only["items"].str.len() >= 2]
    full = evaluate(train, test, cat)
    blind = evaluate(train_only, test, cat)
    pd.testing.assert_frame_equal(full, blind)
    print("[ok] model built without ever seeing May-Jun gives identical test results (no leakage)")

    rows = []
    for name, s in [("Chain", df)] + list(df.groupby("Branch")):
        first, _ = classify(s[s.Date < STABILITY_SPLIT])
        second, _ = classify(s[s.Date >= STABILITY_SPLIT])
        m = first.set_index("Product")["class"].to_frame("jan_mar").join(
            second.set_index("Product")["class"].rename("apr_jun"))
        changed = m[m.jan_mar != m.apr_jun]
        rows.append({"scope": name, "items": len(m),
                     "same_class_pct": round((m.jan_mar == m.apr_jun).mean() * 100, 1),
                     "items_that_changed": "; ".join(f"{p} ({r.jan_mar}->{r.apr_jun})" for p, r in changed.iterrows()) or "none"})
    stab = pd.DataFrame(rows)
    stab.to_csv(TABLES / "matrix_stability.csv", index=False)
    print("[ok] menu matrix stability, Jan-Mar vs Apr-Jun:")
    print(stab.to_string(index=False))

    gain = full.iloc[2]
    print(f"\nPairing model 2 vs baseline: +{gain.gain_vs_baseline_pts} pts "
          f"(95% CI {gain.gain_ci95_low_pts} to {gain.gain_ci95_high_pts}, bootstrapped by order)")
    print("All checks passed.")


if __name__ == "__main__":
    main()
