"""How should Stories test the menu changes so the result can be trusted?

We use Jan-Jun 2026 history, when nothing was changed, so any "effect" a method finds there
is a false alarm. A good test design should raise false alarms only ~5% of the time.

Metric: gross profit per order at Harbour, relative to Garden + Uptown (control), on the
log scale, so chain-wide swings (Tuesdays, Eid, growth) largely cancel.

Design 1 (rejected): 8 weeks before vs 8 weeks after, at the weekly level.
Design 2 (recommended): switchback. Inside the same test window, combos and till
    suggestions are switched ON at Harbour on randomly chosen days (half the days, balanced
    across weekdays) and OFF on the others. Trends and holidays hit ON and OFF days equally.

For each design: placebo false-alarm rate on history, and the minimum detectable effect
(80% power, 5% two-sided) by test length.

Note: price changes cannot be switched on and off daily. They need a separate, longer
branch-level test and should be read with the caution shown by Design 1.

Run from the repo root:  python menu_engineering/ab_test_power.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

from src.clean import GP, load_clean  # noqa: E402

TABLES = ROOT / "outputs" / "tables"
TARGET_EFFECT = 0.05
Z = 1.96 + 0.84                 # 5% two-sided, 80% power
N_RANDOM_PLACEBOS = 2000
SEED = 11


def gap_series(df: pd.DataFrame, freq: str) -> pd.Series:
    """log(Harbour profit per order) - log(control profit per order) per period."""
    tx = df.groupby("Transaction ID").agg(Date=("Date", "first"), branch=("Branch", "first"), gp=(GP, "sum"))
    tx["group"] = np.where(tx.branch == "Harbour", "test", "control")
    tx["period"] = tx.Date.dt.to_period(freq)
    w = tx.groupby(["period", "group"]).gp.mean().unstack()
    if freq.startswith("W"):
        full = tx.groupby("period").Date.nunique() == 7   # drop partial weeks
        w = w[full.reindex(w.index)]
    return np.log(w["test"]) - np.log(w["control"])


def mde(se: float) -> float:
    return (np.exp(Z * se) - 1) * 100


def design_before_after(weekly: pd.Series) -> tuple[pd.DataFrame, dict]:
    sd = weekly.std(ddof=1)
    power = pd.DataFrame([{"design": "Before vs after (weekly)", "test_weeks": w,
                           "minimum_detectable_effect_pct": round(mde(sd * np.sqrt(2 / w)), 2)}
                          for w in (4, 6, 8, 10, 12)])
    v, alarms, n = weekly.values, 0, 0
    for s in range(8, len(v) - 8 + 1):
        alarms += stats.ttest_ind(v[s:s + 8], v[s - 8:s], equal_var=False).pvalue < 0.05
        n += 1
    trend = np.polyfit(np.arange(len(v)), v, 1)[0] * 100
    return power, {"design": "Before vs after (weekly)", "placebo_tests": n,
                   "false_alarms": int(alarms), "false_alarm_rate_pct": round(alarms / n * 100, 1),
                   "note": f"Harbour already drifts {trend:+.2f}% per week vs control; Eid week is an outlier"}


def balanced_assignment(dates: pd.DatetimeIndex, rng) -> np.ndarray:
    """Randomly switch half the days ON, balanced within each weekday."""
    on = np.zeros(len(dates), dtype=bool)
    dow = dates.dayofweek
    for d in range(7):
        idx = np.flatnonzero(dow == d)
        rng.shuffle(idx)
        on[idx[: len(idx) // 2]] = True
    return on


def design_switchback(daily: pd.Series) -> tuple[pd.DataFrame, dict]:
    rng = np.random.default_rng(SEED)
    dates = daily.index.to_timestamp()
    values = daily.values
    # remove day-of-week pattern in the gap so it does not inflate noise (assignment is weekday-balanced)
    resid = values - pd.Series(values).groupby(dates.dayofweek).transform("mean").values
    sd = resid.std(ddof=1)
    # w weeks = 7w days, half ON and half OFF -> SE = sd * sqrt(1/(3.5w) + 1/(3.5w))
    power = pd.DataFrame([{"design": "Switchback (random ON/OFF days)", "test_weeks": w,
                           "minimum_detectable_effect_pct": round(mde(sd * np.sqrt(2 / (3.5 * w))), 2)}
                          for w in (4, 6, 8, 10, 12)])
    alarms = 0
    window = 56  # 8-week test
    for _ in range(N_RANDOM_PLACEBOS):
        start = rng.integers(0, len(values) - window + 1)
        v, d = values[start:start + window], dates[start:start + window]
        v = v - pd.Series(v).groupby(d.dayofweek).transform("mean").values  # same weekday adjustment as the analysis
        on = balanced_assignment(d, rng)
        alarms += stats.ttest_ind(v[on], v[~on], equal_var=False).pvalue < 0.05
    return power, {"design": "Switchback (random ON/OFF days)", "placebo_tests": N_RANDOM_PLACEBOS,
                   "false_alarms": int(alarms), "false_alarm_rate_pct": round(alarms / N_RANDOM_PLACEBOS * 100, 1),
                   "note": "ON and OFF days share the same weeks, so trends and holidays cancel"}


def main() -> None:
    df = load_clean()
    p1, s1 = design_before_after(gap_series(df, "W-SUN"))
    p2, s2 = design_switchback(gap_series(df, "D"))
    power = pd.concat([p1, p2], ignore_index=True)
    power["can_detect_5pct"] = power.minimum_detectable_effect_pct <= TARGET_EFFECT * 100
    placebo = pd.DataFrame([s1, s2])
    power.to_csv(TABLES / "ab_test_power.csv", index=False)
    placebo.to_csv(TABLES / "ab_test_placebo.csv", index=False)
    pd.set_option("display.width", 200)
    print(power.to_string(index=False))
    print()
    print(placebo.to_string(index=False))


if __name__ == "__main__":
    main()
