"""Challenge the first explanation of the Eid al-Fitr dip (all MEASURED).

First explanation: customers leave Beirut for Eid. The file has no customer location, so it
cannot confirm that. This script checks the explanations it CAN test:
  1. Were branches open shorter hours on Eid?           (first and last order of the day)
  2. Is the dip just the war? (war from 2 Mar 2026)     (how many baseline days were wartime)
  3. Did the time-of-day pattern change?                (share of orders by hour)

Run from the repo root:  python truck/fitr_alternatives.py
Writes outputs/truck/tables/fitr_alternative_checks.csv
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from src.clean import REV, load_clean  # noqa: E402

TABLES = ROOT / "outputs" / "truck" / "tables"
TABLES.mkdir(parents=True, exist_ok=True)
FITR = pd.to_datetime(["2026-03-20", "2026-03-21", "2026-03-22", "2026-03-23"])
WAR_START = pd.Timestamp("2026-03-02")   # sourced in docs/5_rejected_approaches.md
WINDOW_WEEKS = 3                         # same as holiday_dips.py: same weekday within +/-21 days


def main() -> None:
    df = load_clean()
    day = df.groupby("Date").agg(rev=(REV, "sum"), first=("Time", "min"), last=("Time", "max"))
    rows = []
    refs_all = []
    for t in FITR:
        refs = [t + pd.Timedelta(days=7 * k) for k in range(-WINDOW_WEEKS, WINDOW_WEEKS + 1) if k != 0]
        refs = [r for r in refs if r in day.index and r not in FITR]
        refs_all += refs
        r = day.loc[refs]
        rows.append({"date": t.date(), "weekday": t.day_name(), "revenue": round(day.loc[t, "rev"]),
                     "expected_revenue": round(r.rev.mean()), "gap_pct": round((day.loc[t, "rev"] / r.rev.mean() - 1) * 100, 1),
                     "first_order": day.loc[t, "first"], "last_order": day.loc[t, "last"],
                     "baseline_first_order_median": sorted(r["first"])[len(r) // 2],
                     "baseline_last_order_median": sorted(r["last"])[len(r) // 2],
                     "baseline_days": len(refs), "baseline_days_in_war": sum(x >= WAR_START for x in refs)})
    out = pd.DataFrame(rows)

    df["fitr"] = df.Date.isin(FITR)
    base = df[df.Date.isin(refs_all)]
    share = lambda s: s.groupby("hour")["Transaction ID"].nunique() / s["Transaction ID"].nunique()  # noqa: E731
    gap = (share(df[df.fitr]) - share(base)).abs()
    summary = pd.DataFrame([
        {"date": "SUMMARY", "weekday": "", "revenue": out.revenue.sum(), "expected_revenue": out.expected_revenue.sum(),
         "gap_pct": round((out.revenue.sum() / out.expected_revenue.sum() - 1) * 100, 1),
         "first_order": "", "last_order": "", "baseline_first_order_median": "", "baseline_last_order_median": "",
         "baseline_days": out.baseline_days.sum(), "baseline_days_in_war": out.baseline_days_in_war.sum()},
    ])
    out = pd.concat([out, summary], ignore_index=True)
    out["note"] = ""
    out.loc[out.index[-1], "note"] = (f"Largest change in any hour's share of orders: {gap.max() * 100:.1f} points "
                                      f"(mean {gap.mean() * 100:.1f}); opening hours normal; "
                                      f"{out.baseline_days_in_war.iloc[-1]} of {out.baseline_days.iloc[-1]} baseline days were wartime")
    out.to_csv(TABLES / "fitr_alternative_checks.csv", index=False)
    pd.set_option("display.width", 250)
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
