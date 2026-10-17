"""Turning the payday cycle into profit, sized on who actually exists in the data.

The first version assumed 170 Month Pass buyers a month. The data does not support that:
members visit about once a month and almost nobody buys 3+ drinks month after month.
This version sizes every option on MEASURED pools and keeps only the unknown behaviour
(uptake, uplift) as stated assumptions.

Option A - Month Pass (4 drinks for the price of 3.5, sold 28th-7th, valid to month end).
  Pool = members who already buy 3+ drinks in at least half of the months (the only people
  for whom the pass is a good deal without changing habits). They are counted as buyers only in
  the months they really bought 3+ drinks. Profit per buyer is computed from THEIR OWN monthly
  drink counts, so the discount on drinks they would have bought anyway (cannibalization) is
  measured; unused pass drinks are NOT counted as profit (all 4 assumed used, cautious).

Option B - Mid-month comeback reward. Every member who visits on the 28th-7th gets a reward
  valid on the 14th-27th. Base and the share who come back anyway are MEASURED; the reward is
  a cost on those natural returners, so the break-even uplift is computed.

Plus: a randomized test sized from the data for each option.

Run from the repo root (after payday_cycle.py):  python payday/month_pass.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

from src.clean import GP, REV, load_clean  # noqa: E402
from src import style  # noqa: E402

TABLES = ROOT / "outputs" / "payday" / "tables"
FIGS = ROOT / "outputs" / "payday" / "figures"
TABLES.mkdir(parents=True, exist_ok=True)
FIGS.mkdir(parents=True, exist_ok=True)
DRINKS = ["Hot Coffee", "Cold Coffee", "Matcha & Tea", "Cold Drinks"]

# ---- Design choices (DESIGN) and unknowns (ASSUMPTION) -----------------------------
PASS_DRINKS = 4                    # DESIGN
PASS_PAID_DRINKS = 3.5             # DESIGN: 12.5% off
POOL_MIN_DRINKS = 3                # DESIGN: pool = members with >= 3 drinks ...
POOL_MIN_SHARE_OF_MONTHS = 0.5     # ... in at least half of the months
PASS_UPTAKE = [0.25, 0.50, 0.75]   # ASSUMPTION: share of the pool buying each month
PASS_EXTRA_VISITS = [0.0, 0.5, 1.0]  # ASSUMPTION: extra visits per buyer per month
REWARD_SMALL_PCT = 0.10            # DESIGN: "10% off your order" (cost = 10% of the average member ticket)
NATURAL_REDEEM = [1.0, 0.5]        # ASSUMPTION: share of natural returners who use the reward
UPLIFT_PTS = [2, 5, 10]            # ASSUMPTION: extra percentage points who come back mid-month
TEST_CYCLES = 3
Z = 1.96 + 0.84                    # 5% two-sided, 80% power


def build(df: pd.DataFrame):
    tx = df.groupby("Transaction ID").agg(Date=("Date", "first"), customer=("Customer ID", "first"),
                                          gp=(GP, "sum"), rev=(REV, "sum"))
    m = tx.dropna(subset=["customer"]).copy()
    m["month"] = m.Date.dt.to_period("M")
    d = df[df.Category.isin(DRINKS)]
    unit = {
        "drink_price": (d["Unit Price (USD)"] * d.Quantity).sum() / d.Quantity.sum(),
        "drink_cost": (d["Unit Cost (USD)"] * d.Quantity).sum() / d.Quantity.sum(),
        "pastry_cost": ((df.Category == "Bakery") * df["Unit Cost (USD)"] * df.Quantity).sum()
                       / df[df.Category == "Bakery"].Quantity.sum(),
        "gp_per_member_visit": m.gp.mean(),
        "member_ticket": m.rev.mean(),
    }
    # gross profit per member visit that does NOT come from drinks (food add-ons)
    md = df[df["Customer ID"].notna()]
    drink_gp = md[md.Category.isin(DRINKS)][GP].sum()
    unit["food_gp_per_member_visit"] = (md[GP].sum() - drink_gp) / md["Transaction ID"].nunique()
    unit["pass_price"] = PASS_PAID_DRINKS * unit["drink_price"]
    return tx, m, unit


def member_facts(df: pd.DataFrame, m: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    members = m.customer.unique()
    months = sorted(m.month.unique())
    md = df[df["Customer ID"].notna() & df.Category.isin(DRINKS)].copy()
    md["month"] = md.Date.dt.to_period("M")
    drinks = (md.groupby(["Customer ID", "month"]).Quantity.sum()
              .reindex(pd.MultiIndex.from_product([members, months], names=["customer", "month"])).fillna(0))
    share = (drinks >= POOL_MIN_DRINKS).groupby(level=0).mean()
    pool = share[share >= POOL_MIN_SHARE_OF_MONTHS].index
    per_month_3plus = (drinks >= POOL_MIN_DRINKS).groupby(level="month").sum()
    visits = m.groupby("customer").size() / len(months)
    facts = pd.DataFrame([
        {"metric": "Members (customer IDs)", "value": len(members)},
        {"metric": "Median visits per member per month", "value": round(visits.median(), 2)},
        {"metric": "Member-months with 0 / 1 / 2 / 3 / 4+ drinks (%)",
         "value": " / ".join(f"{v:.1f}" for v in [
             (drinks == 0).mean() * 100, (drinks == 1).mean() * 100, (drinks == 2).mean() * 100,
             (drinks == 3).mean() * 100, (drinks >= 4).mean() * 100])},
        {"metric": f"Members with {POOL_MIN_DRINKS}+ drinks in a given month (range Jan-Jun)",
         "value": f"{per_month_3plus.min():.0f}-{per_month_3plus.max():.0f}"},
        {"metric": f"Members with {POOL_MIN_DRINKS}+ drinks in at least half of the months (PASS POOL)",
         "value": len(pool)},
        {"metric": f"Members averaging {POOL_MIN_DRINKS}+ drinks a month", "value": int((drinks.groupby(level=0).mean() >= POOL_MIN_DRINKS).sum())},
    ])
    return facts, drinks.loc[pool]


def pass_delta(d: np.ndarray, e: float, unit: dict) -> np.ndarray:
    """Gross-profit change for one buyer-month. d = drinks they buy anyway (MEASURED), e = extra visits.

    Cautious on purpose: all 4 pass drinks are assumed used (no profit from unused drinks), and the
    mid-month pastry is always given. Drinks beyond 4 are paid at the normal price; extra visits also
    bring the measured food gross profit per member visit.
    """
    p, c, P = unit["drink_price"], unit["drink_cost"], unit["pass_price"]
    with_pass = (P + np.maximum(d + e - PASS_DRINKS, 0) * p - np.maximum(d + e, PASS_DRINKS) * c
                 - unit["pastry_cost"] + e * unit["food_gp_per_member_visit"])
    return with_pass - d * (p - c)


def option_a_pass(pool_drinks: pd.Series, unit: dict) -> tuple[pd.DataFrame, dict]:
    """Buyers = pool members in the months they actually buy 3+ drinks (people buy a pass only
    when they expect to use it). Their real drink counts give the cannibalization."""
    n_pool = pool_drinks.index.get_level_values(0).nunique()
    n_months = pool_drinks.index.get_level_values(1).nunique()
    eligible = pool_drinks[pool_drinks >= POOL_MIN_DRINKS]
    eligible_per_month = len(eligible) / n_months
    d = eligible.values
    rows = []
    for e in PASS_EXTRA_VISITS:
        delta = pass_delta(d, e, unit).mean()
        for u in PASS_UPTAKE:
            buyers = eligible_per_month * u
            rows.append({"option": "A. Month Pass", "pool_members": n_pool,
                         "pool_members_eligible_per_month": round(eligible_per_month, 1), "uptake_pct": u * 100,
                         "extra_visits_per_buyer_month": e, "buyers_per_month": round(buyers, 1),
                         "gp_change_per_buyer_month_usd": round(delta, 2),
                         "gross_profit_per_year_usd": round(buyers * delta * 12)})
    grid = np.linspace(0, 3, 301)
    be = next(x for x in grid if pass_delta(d, x, unit).mean() >= 0)
    info = {"avg_drinks_eligible_month": round(d.mean(), 2), "share_eligible_months_with_4plus_drinks_pct":
            round((d >= PASS_DRINKS).mean() * 100, 1), "breakeven_extra_visits": round(be, 2),
            "gp_change_no_new_visits_usd": round(pass_delta(d, 0, unit).mean(), 2)}
    return pd.DataFrame(rows), info


def comeback_base(m: pd.DataFrame) -> pd.DataFrame:
    t = m.copy()
    t["dom"] = t.Date.dt.day
    cyc = t.Date.dt.to_period("M")
    t["cycle"] = np.where(t.dom >= 28, (cyc + 1).astype(str), cyc.astype(str))
    cycles = sorted(t.cycle.unique())[1:-1]  # full cycles only
    rows = []
    for cy in cycles:
        s = t[t.cycle == cy]
        peak = set(s[(s.dom >= 28) | (s.dom <= 7)].customer)
        dip = set(s[s.dom.between(14, 27)].customer)
        rows.append({"cycle": cy, "members_visiting_28th_7th": len(peak), "also_back_14th_27th": len(peak & dip),
                     "natural_return_rate_pct": round(len(peak & dip) / len(peak) * 100, 1)})
    return pd.DataFrame(rows)


def option_b_comeback(base: pd.DataFrame, unit: dict) -> pd.DataFrame:
    n = base.members_visiting_28th_7th.mean()
    r0 = base.also_back_14th_27th.sum() / base.members_visiting_28th_7th.sum()
    gpv = unit["gp_per_member_visit"]
    rewards = {"Free pastry": unit["pastry_cost"], f"{REWARD_SMALL_PCT:.0%} off the order": REWARD_SMALL_PCT * unit["member_ticket"]}
    rows = []
    for rname, rc in rewards.items():
        for redeem in NATURAL_REDEEM:
            be = r0 * redeem * rc / (gpv - rc) * 100
            for up in UPLIFT_PTS:
                per_cycle = n * (up / 100 * (gpv - rc) - r0 * redeem * rc)
                rows.append({"option": "B. Mid-month comeback reward", "reward": rname, "reward_cost_usd": round(rc, 2),
                             "members_given_reward_per_month": round(n), "natural_return_rate_pct": round(r0 * 100, 1),
                             "natural_returners_using_reward_pct": redeem * 100, "uplift_pts": up,
                             "breakeven_uplift_pts": round(be, 1),
                             "gross_profit_per_year_usd": round(per_cycle * 12)})
    return pd.DataFrame(rows)


def tests(base: pd.DataFrame, pool_n: int, unit: dict) -> pd.DataFrame:
    n = base.members_visiting_28th_7th.mean()
    r0 = base.also_back_14th_27th.sum() / base.members_visiting_28th_7th.sum()
    rc = REWARD_SMALL_PCT * unit["member_ticket"]
    rows = []
    for cycles in (1, TEST_CYCLES):
        arm = n / 2 * cycles
        mde = Z * np.sqrt(2 * r0 * (1 - r0) / arm) * 100
        rows.append({"test": f"B. Reward to a random half of 28th-7th visitors, {cycles} cycle(s)",
                     "per_arm": round(arm), "smallest_detectable_uplift_pts": round(mde, 1),
                     # worst case: nobody new comes back, every natural returner uses the 10%-off reward
                     "worst_case_cost_usd": round(arm * r0 * rc)})
    rows.append({"test": "A. Month Pass", "per_arm": pool_n // 2, "smallest_detectable_uplift_pts": None,
                 "worst_case_cost_usd": None})
    out = pd.DataFrame(rows)
    out["note"] = ["", "Compares the mid-month return rate of members who got the reward vs not",
                   f"Pool of {pool_n} is too small for a randomized test: run as a pilot and track redemptions"]
    return out


def plot(a: pd.DataFrame, b: pd.DataFrame, path: Path) -> None:
    style.apply()
    fig, (ax2, ax1) = plt.subplots(1, 2, figsize=(12.5, 4.6), gridspec_kw={"width_ratios": [1, 1.15]})
    fmt = plt.FuncFormatter(lambda v, _: f"-${abs(v):,.0f}" if v < 0 else f"${v:,.0f}")

    bb = b[b.natural_returners_using_reward_pct == 100]
    for i, (rname, g) in enumerate(bb.groupby("reward", sort=False)):
        ax1.plot(g.uplift_pts, g.gross_profit_per_year_usd, marker="o", lw=2, color=style.SERIES[i],
                 label=f"{rname} (${g.reward_cost_usd.iloc[0]:.2f}): break-even +{g.breakeven_uplift_pts.iloc[0]:.1f} pts")
        for x, y in zip(g.uplift_pts, g.gross_profit_per_year_usd):
            ax1.annotate(f"-${abs(y)/1000:.1f}k" if y < 0 else f"${y/1000:.1f}k", (x, y), xytext=(0, 7),
                         textcoords="offset points", ha="center", fontsize=8, color=style.INK_2)
    ax1.axhline(0, color=style.INK_2, lw=0.8)
    ax1.set_xticks(UPLIFT_PTS, [f"+{u} pts" for u in UPLIFT_PTS])
    ax1.set_xlabel("Extra share of members who come back on the 14th-27th")
    ax1.yaxis.set_major_formatter(fmt)
    ax1.set_title(f"B. Comeback reward: {bb.members_given_reward_per_month.iloc[0]:,} members a month,\n"
                  f"{bb.natural_return_rate_pct.iloc[0]:.1f}% already come back mid-month", fontsize=11, pad=34)
    ax1.legend(loc="lower left", bbox_to_anchor=(0, 1.0), fontsize=7.8, ncol=1)

    aa = a[a.uptake_pct == 50]
    x = np.arange(len(aa))
    bars = ax2.bar(x, aa.gross_profit_per_year_usd, color=style.SERIES[2], width=0.55, edgecolor=style.SURFACE, linewidth=2)
    for bar, v, d in zip(bars, aa.gross_profit_per_year_usd, aa.gp_change_per_buyer_month_usd):
        ax2.text(bar.get_x() + bar.get_width() / 2, max(v, 0) + 15,
                 (f"-${abs(v):,.0f}" if v < 0 else f"${v:,.0f}") + f"/yr\n({d:+.2f} per buyer-month)",
                 ha="center", fontsize=8.5, color=style.INK)
    ax2.axhline(0, color=style.INK_2, lw=0.8)
    ax2.set_xticks(x, [f"+{e:g} extra visits" for e in aa.extra_visits_per_buyer_month])
    ax2.yaxis.set_major_formatter(fmt)
    lo, hi = aa.gross_profit_per_year_usd.min(), aa.gross_profit_per_year_usd.max()
    ax2.set_ylim(min(lo, 0) * 1.4 - 50, max(hi, 0) * 1.5 + 100)
    ax2.set_title(f"A. Month Pass: {a.pool_members.iloc[0]} members buy 3+ drinks in half the months;\n"
                  f"if half of those eligible buy: {aa.buyers_per_month.iloc[0]:.0f} buyers a month", fontsize=11, pad=34)
    ax2.grid(axis="x", visible=False)
    for ax in (ax1, ax2):
        ax.set_ylabel("Extra gross profit per year (USD)")
    fig.text(0.01, -0.06, "ESTIMATE on MEASURED pools: members, natural return rate, drink counts, prices and costs from "
             "the data; uptake and uplift are assumptions (top of payday/month_pass.py).\nB is shown for the worst case: every member "
             "who would have come back anyway also uses the reward.", fontsize=8, color=style.MUTED)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    df = load_clean()
    tx, m, unit = build(df)
    facts, pool_drinks = member_facts(df, m)
    facts.to_csv(TABLES / "month_pass_members.csv", index=False)
    a, a_info = option_a_pass(pool_drinks, unit)
    a.to_csv(TABLES / "month_pass_option_a.csv", index=False)
    unit_row = {k: round(v, 2) for k, v in unit.items()} | {f"pass_{k}": v for k, v in a_info.items()}
    pd.DataFrame([unit_row]).to_csv(TABLES / "month_pass_unit_economics.csv", index=False)
    base = comeback_base(m)
    base.to_csv(TABLES / "comeback_base.csv", index=False)
    b = option_b_comeback(base, unit)
    b.to_csv(TABLES / "comeback_option_b.csv", index=False)
    t = tests(base, pool_drinks.index.get_level_values(0).nunique(), unit)
    t.to_csv(TABLES / "payday_offer_tests.csv", index=False)
    plot(a, b, FIGS / "month_pass_scenarios.png")

    pd.set_option("display.width", 230)
    pd.set_option("display.max_colwidth", 90)
    print(facts.to_string(index=False), "\n")
    print(unit_row, "\n")
    print(a.to_string(index=False), "\n")
    print(base.to_string(index=False), "\n")
    print(b.to_string(index=False), "\n")
    print(t.to_string(index=False))


if __name__ == "__main__":
    main()
