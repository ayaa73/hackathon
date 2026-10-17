"""Tests for the event-driven ideas we explored and did not continue with.

Ideas tested (see docs/approaches_considered_and_rejected.md):
  1. Israeli strikes on Beirut vs daily sales
  2. University and high-school exam periods
  3. Lebanese expatriate travel windows
  4. Football match nights

Method (same for every idea):
  * Daily series per scope (chain + each branch), metric = log(revenue), log(orders),
    log(evening orders, 20:00-23:59) or logit(evening share of orders).
  * Baseline model: day-of-week effects + a smooth trend. Sales grow strongly over the
    six months, and Tuesdays are a large recurring spike, so both must be removed first.
  * Single event day: leave-one-out residual (fit without the day, predict it), compared with
    the leave-one-out residuals of all 181 days (empirical two-sided p-value).
  * Multi-day window: coefficient of a window indicator added to the model, compared with the
    same coefficient for placebo windows of the same length placed at every other start date.
  * p-values are Bonferroni-adjusted within each family of tests (K tests in the family).

Run from the repository root:  python rejected_approaches/event_tests.py
Writes outputs/tables/rejected_event_tests.csv
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.clean import load_clean, REV  # noqa: E402

OUT = ROOT / "outputs" / "tables" / "rejected_event_tests.csv"
EVENING_FROM = 20  # hour of day; the data peak is 20:00-22:00

# ---------------------------------------------------------------- event calendars
# Dates and sources are listed in docs/approaches_considered_and_rejected.md.
STRIKE_DAYS = ["2026-03-04", "2026-03-08", "2026-03-12", "2026-03-18",
               "2026-04-01", "2026-04-08", "2026-05-06", "2026-06-07"]
FOOTBALL_NIGHTS = ["2026-04-28", "2026-04-29", "2026-05-05", "2026-05-06", "2026-05-30"]
WINDOWS = {
    "university": [
        ("AUB in-person classes + finals (20 Apr-17 May)", "2026-04-20", "2026-05-17"),
        ("AUB final exams only (8-17 May)", "2026-05-08", "2026-05-17"),
    ],
    "school": [
        ("School exam season as hypothesised (1 May-30 Jun)", "2026-05-01", "2026-06-30"),
        ("School exam season, late part (1-28 Jun)", "2026-06-01", "2026-06-28"),
    ],
    "expat": [
        ("Easter weekend 1 (3-6 Apr)", "2026-04-03", "2026-04-06"),
        ("Orthodox Easter weekend (10-13 Apr)", "2026-04-10", "2026-04-13"),
        ("Late June arrival ramp (15-30 Jun)", "2026-06-15", "2026-06-30"),
    ],
    "football": [
        ("World Cup first 20 days (11-30 Jun)", "2026-06-11", "2026-06-30"),
    ],
}


# ---------------------------------------------------------------- data
def daily_table(df: pd.DataFrame, branch=None) -> pd.DataFrame:
    d = df if branch is None else df[df["Branch"] == branch]
    tx = d.drop_duplicates("Transaction ID")
    g = d.groupby("Date")[REV].sum().rename("revenue").to_frame()
    g["orders"] = tx.groupby("Date")["Transaction ID"].nunique()
    g["evening_orders"] = tx[tx["hour"] >= EVENING_FROM].groupby("Date")["Transaction ID"].nunique()
    g = g.fillna(0)
    g["evening_share"] = (g["evening_orders"] / g["orders"]).clip(1e-3, 1 - 1e-3)
    return g


def make_y(g: pd.DataFrame, metric: str) -> np.ndarray:
    if metric == "evening_share":
        p = g["evening_share"].to_numpy()
        return np.log(p / (1 - p))
    return np.log(g[metric].clip(lower=1).to_numpy())


def design(index: pd.DatetimeIndex, trend: str) -> np.ndarray:
    t = np.arange(len(index), dtype=float) / len(index)
    cols = [(index.dayofweek.to_numpy() == k).astype(float) for k in range(7)]
    if trend == "quadratic":
        cols += [t, t ** 2]
    else:  # monthly-knot linear spline
        cols.append(t)
        for m in range(2, 7):
            knot = (pd.Timestamp(2026, m, 1) - index[0]).days / len(index)
            cols.append(np.maximum(0, t - knot))
    return np.column_stack(cols)


def fit(X, y, mask=None):
    if mask is None:
        mask = np.ones(len(y), bool)
    beta, *_ = np.linalg.lstsq(X[mask], y[mask], rcond=None)
    return beta


# ---------------------------------------------------------------- tests
def loo_residuals(X, y):
    n = len(y)
    r = np.empty(n)
    for i in range(n):
        m = np.ones(n, bool)
        m[i] = False
        r[i] = y[i] - X[i] @ fit(X, y, m)
    return r


def single_day_tests(g, metric, days, family, scope, trend="spline"):
    y = make_y(g, metric)
    X = design(g.index, trend)
    r = loo_residuals(X, y)
    rows = []
    K = len(days)
    for day in days:
        i = g.index.get_loc(pd.Timestamp(day))
        p = (1 + np.sum(np.abs(r) >= abs(r[i]))) / (len(r) + 1)
        rows.append(dict(family=family, event=day, scope=scope, metric=metric,
                         effect_pct=(np.exp(r[i]) - 1) * 100, p_empirical=p,
                         p_bonferroni=min(1.0, p * K), n_tests_in_family=K,
                         method=f"leave-one-out residual vs {len(r)} days ({trend} trend)"))
    return rows


def window_test(g, metric, label, start, end, family, scope, trend):
    y = make_y(g, metric)
    idx = g.index
    base = design(idx, trend)
    n = len(idx)
    L = (pd.Timestamp(end) - pd.Timestamp(start)).days + 1
    s0 = idx.get_loc(pd.Timestamp(start))

    def coef(s):
        ind = np.zeros(n)
        ind[s:s + L] = 1.0
        return fit(np.column_stack([base, ind]), y)[-1]

    real = coef(s0)
    placebo = np.array([coef(s) for s in range(0, n - L + 1)])
    p = (1 + np.sum(np.abs(placebo) >= abs(real))) / (len(placebo) + 1)
    lo, hi = np.percentile(placebo, [2.5, 97.5])
    return dict(family=family, event=label, scope=scope, metric=metric, trend=trend,
                effect_pct=(np.exp(real) - 1) * 100, p_empirical=p, p_bonferroni=np.nan,
                n_tests_in_family=np.nan,
                placebo_95_low_pct=(np.exp(lo) - 1) * 100, placebo_95_high_pct=(np.exp(hi) - 1) * 100,
                method=f"window indicator vs {len(placebo)} placebo windows ({trend} trend)")


def main():
    df = load_clean()
    scopes = {"Chain": daily_table(df)}
    for b in sorted(df["Branch"].unique()):
        scopes[b] = daily_table(df, b)

    rows = []
    # 1. strikes: revenue + orders, chain and every branch
    for scope, g in scopes.items():
        for metric in ("revenue", "orders"):
            rows += single_day_tests(g, metric, STRIKE_DAYS, "strikes", scope)
    # 4. football nights: evening orders and evening share, chain only
    for metric in ("evening_orders", "evening_share"):
        rows += single_day_tests(scopes["Chain"], metric, FOOTBALL_NIGHTS, "football", "Chain", )
    # windows: chain, both trend specifications
    for fam, items in WINDOWS.items():
        metrics = ("evening_orders", "evening_share") if fam == "football" else ("revenue", "orders")
        for label, s, e in items:
            for metric in metrics:
                for trend in ("spline", "quadratic"):
                    rows.append(window_test(scopes["Chain"], metric, label, s, e, fam, "Chain", trend))

    out = pd.DataFrame(rows)
    # Bonferroni for windows: within family and metric/trend, K = number of windows tested
    mask = out["method"].str.startswith("window")
    k = out[mask].groupby(["family", "metric", "trend"])["event"].transform("count")
    out.loc[mask, "n_tests_in_family"] = k
    out.loc[mask, "p_bonferroni"] = np.minimum(1.0, out.loc[mask, "p_empirical"] * k)
    out = out.round({"effect_pct": 1, "p_empirical": 4, "p_bonferroni": 4,
                     "placebo_95_low_pct": 1, "placebo_95_high_pct": 1})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False)
    pd.set_option("display.width", 250, "display.max_rows", 500, "display.max_colwidth", 60)
    print(out.drop(columns=["method"]).to_string(index=False))
    st = out[out["family"] == "strikes"]
    print(f"\nStrike tests: {len(st)}, raw p<0.05: {(st.p_empirical < 0.05).sum()}, "
          f"expected by chance alone: {0.05 * len(st):.1f}")
    print(f"\nSaved -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
