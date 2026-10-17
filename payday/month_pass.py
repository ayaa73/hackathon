"""Stories Month Pass: sold right after payday, used through the month.

1. Who would buy it (MEASURED): member visit frequency, the regulars to target.
2. Pass design priced from the data: 4 drinks for the price of 3.5 (DESIGN), sold only
   on the 28th-7th, with a free pastry when a pass drink is redeemed on the 14th-27th.
3. Break-even: extra visits per pass needed to cover the discount and the pastry.
4. Profit scenarios (ESTIMATE): buyers per month x extra visits per buyer.
5. Randomized test sized from the data: offer the pass to a random half of members.

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

TABLES = ROOT / "outputs" / "tables"
FIGS = ROOT / "outputs" / "figures"
DRINKS = ["Hot Coffee", "Cold Coffee", "Matcha & Tea", "Cold Drinks"]

# ---- Design choices and assumptions -------------------------------------------------
PASS_DRINKS = 4                  # DESIGN: drinks in the pass
PASS_PAID_DRINKS = 3.5           # DESIGN: price of 3.5 drinks (12.5% off)
REGULAR_THRESHOLD = 1.5          # DESIGN: "regulars" = members with >= 1.5 visits a month on average
SCENARIOS = {                    # ASSUMPTIONS: (share of regulars buying, share of other active
                                 #  members buying, extra visits per buyer per month)
    "Conservative": (0.10, 0.00, 0.5),
    "Central": (0.20, 0.03, 1.0),
    "Optimistic": (0.30, 0.05, 1.5),
}
TEST_MONTHS = 3
Z = 1.96 + 0.84                  # 5% two-sided, 80% power


def member_frequency(tx: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    m = tx.dropna(subset=["customer"])
    months = m.Date.dt.to_period("M").nunique()
    per = m.groupby("customer").agg(visits=("gp", "size"), gp=("gp", "sum"))
    per["visits_per_month"] = per.visits / months
    active_month = m.groupby([m.Date.dt.to_period("M"), "customer"]).size()
    dist = active_month.value_counts().sort_index().rename("member_months").to_frame()
    dist.index.name = "visits_in_a_month"
    regular = per[per.visits_per_month >= REGULAR_THRESHOLD]
    summary = pd.DataFrame([
        {"metric": "Members (customer IDs)", "value": len(per)},
        {"metric": "Active members per month (average)", "value": round(active_month.groupby(level=0).size().mean())},
        {"metric": "Median visits per member per month", "value": round(per.visits_per_month.median(), 2)},
        {"metric": "90th percentile visits per member per month", "value": round(per.visits_per_month.quantile(0.9), 2)},
        {"metric": f"Regulars (>= {REGULAR_THRESHOLD} visits a month)", "value": len(regular)},
        {"metric": "Regulars' average visits per month", "value": round(regular.visits_per_month.mean(), 2)},
        {"metric": "Members with >= 2 visits a month", "value": int((per.visits_per_month >= 2).sum())},
        {"metric": "Gross profit per member order (USD)", "value": round(m.gp.mean(), 2)},
    ])
    return summary, dist


def pass_design(df: pd.DataFrame, gp_per_visit: float) -> pd.DataFrame:
    d = df[df.Category.isin(DRINKS)]
    drink_price = (d["Unit Price (USD)"] * d.Quantity).sum() / d.Quantity.sum()
    drink_cost = (d["Unit Cost (USD)"] * d.Quantity).sum() / d.Quantity.sum()
    b = df[df.Category == "Bakery"]
    pastry_cost = (b["Unit Cost (USD)"] * b.Quantity).sum() / b.Quantity.sum()
    price = PASS_PAID_DRINKS * drink_price
    discount = (PASS_DRINKS - PASS_PAID_DRINKS) * drink_price
    pass_profit_if_fully_used = price - PASS_DRINKS * drink_cost
    breakeven_extra_visits = (discount + pastry_cost) / gp_per_visit
    return pd.DataFrame([{
        "avg_drink_price_usd": round(drink_price, 2), "avg_drink_cost_usd": round(drink_cost, 2),
        "pass_price_usd": round(price, 2), "discount_per_pass_usd": round(discount, 2),
        "mid_month_pastry_cost_usd": round(pastry_cost, 2),
        "pass_gross_profit_if_all_4_drinks_used_usd": round(pass_profit_if_fully_used, 2),
        "gross_profit_per_extra_visit_usd": round(gp_per_visit, 2),
        "breakeven_extra_visits_per_pass": round(breakeven_extra_visits, 2)}])


def scenarios(summary: pd.DataFrame, design: pd.Series) -> pd.DataFrame:
    s = summary.set_index("metric").value
    regulars = s[f"Regulars (>= {REGULAR_THRESHOLD} visits a month)"]
    others = s["Active members per month (average)"] - regulars
    cost_per_pass = design.discount_per_pass_usd + design.mid_month_pastry_cost_usd
    rows = []
    for name, (reg_share, other_share, extra) in SCENARIOS.items():
        buyers = regulars * reg_share + others * other_share
        per_buyer = extra * design.gross_profit_per_extra_visit_usd - cost_per_pass
        rows.append({"scenario": name, "regulars_buying_pct": reg_share * 100, "other_active_buying_pct": other_share * 100,
                     "extra_visits_per_buyer_per_month": extra, "buyers_per_month": round(buyers),
                     "profit_per_buyer_per_month_usd": round(per_buyer, 2),
                     "gross_profit_per_year_usd": round(buyers * per_buyer * 12),
                     "passes_sold_per_year": round(buyers * 12),
                     "prepaid_cash_per_year_usd": round(buyers * 12 * design.pass_price_usd)})
    return pd.DataFrame(rows)


def test_design(tx: pd.DataFrame, sc: pd.DataFrame) -> pd.DataFrame:
    m = tx.dropna(subset=["customer"])
    last = m[m.Date >= m.Date.max() - pd.DateOffset(months=TEST_MONTHS) + pd.Timedelta(days=1)]
    members = m.customer.unique()
    v = last.groupby("customer").size().reindex(members).fillna(0) / TEST_MONTHS  # visits per month
    n_arm = len(members) // 2
    mde = Z * v.std(ddof=1) * np.sqrt(2 / n_arm)
    rows = [{"metric": "members per arm (random half each)", "value": n_arm},
            {"metric": "visits per member per month (last 3 months, mean)", "value": round(v.mean(), 3)},
            {"metric": "standard deviation", "value": round(v.std(ddof=1), 3)},
            {"metric": f"smallest detectable difference in visits per member per month ({TEST_MONTHS} months)",
             "value": round(mde, 3)},
            {"metric": "as % of current visits", "value": round(mde / v.mean() * 100, 1)}]
    for _, r in sc.iterrows():
        regs_and_others = r.buyers_per_month
        itt = regs_and_others * r.extra_visits_per_buyer_per_month / len(members)
        rows.append({"metric": f"ALL MEMBERS: expected effect per offered member, {r.scenario} (visits/month)",
                     "value": round(itt, 3)})

    # Regulars-only test: the effect is concentrated where buyers are
    per = m.groupby("customer").size() / m.Date.dt.to_period("M").nunique()
    regs = per[per >= REGULAR_THRESHOLD].index
    vr = v.reindex(regs)
    n_reg = len(regs) // 2
    mde_r = Z * vr.std(ddof=1) * np.sqrt(2 / n_reg)
    rows += [{"metric": "REGULARS ONLY: members per arm", "value": n_reg},
             {"metric": "REGULARS ONLY: visits per member per month (mean)", "value": round(vr.mean(), 3)},
             {"metric": "REGULARS ONLY: smallest detectable difference (visits/month)", "value": round(mde_r, 3)}]
    for _, r in sc.iterrows():
        share = SCENARIOS[r.scenario][0]
        rows.append({"metric": f"REGULARS ONLY: expected effect per offered regular, {r.scenario} (visits/month)",
                     "value": round(share * r.extra_visits_per_buyer_per_month, 3)})
    return pd.DataFrame(rows)


def plot(sc: pd.DataFrame, design: pd.Series, dip_ceiling: float, path: Path) -> None:
    style.apply()
    fig, ax = plt.subplots(figsize=(9, 4.2))
    x = np.arange(len(sc))
    bars = ax.bar(x, sc.gross_profit_per_year_usd, color=[style.SERIES[i] for i in range(len(sc))], width=0.55,
                  edgecolor=style.SURFACE, linewidth=2)
    for bar, v, n in zip(bars, sc.gross_profit_per_year_usd, sc.buyers_per_month):
        money = f"-${abs(v):,.0f}" if v < 0 else f"${v:,.0f}"
        ax.text(bar.get_x() + bar.get_width() / 2, max(v, 0) + 250, f"{money}/yr\n{n:.0f} buyers/month",
                ha="center", va="bottom", fontsize=9, color=style.INK)
    ax.axhline(dip_ceiling, color=style.MUTED, ls="--", lw=1)
    ax.text(-0.45, dip_ceiling + 250, f"Whole mid-month dip: ${dip_ceiling:,.0f}/yr", ha="left",
            fontsize=8.5, color=style.INK_2)
    ax.set_xticks(x, [f"{r.scenario}\n+{r.extra_visits_per_buyer_per_month:g} visits per buyer a month"
                      for _, r in sc.iterrows()])
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"-${abs(v):,.0f}" if v < 0 else f"${v:,.0f}"))
    ax.set_ylim(min(0, sc.gross_profit_per_year_usd.min()) * 1.2, max(sc.gross_profit_per_year_usd.max(), dip_ceiling) * 1.3)
    ax.set_title(f"Month Pass: extra gross profit per year (break-even {design.breakeven_extra_visits_per_pass:.2f} "
                 "extra visits per pass)", fontsize=11.5)
    ax.grid(axis="x", visible=False)
    fig.text(0.01, -0.03, "ESTIMATE. Prices, costs, member counts and profit per visit MEASURED; pass design and "
             "uptake/extra visits are assumptions (top of payday/month_pass.py).", fontsize=8, color=style.MUTED)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    df = load_clean()
    tx = df.groupby("Transaction ID").agg(Date=("Date", "first"), customer=("Customer ID", "first"),
                                          gp=(GP, "sum"), rev=(REV, "sum"))
    summary, dist = member_frequency(tx)
    summary.to_csv(TABLES / "month_pass_members.csv", index=False)
    dist.to_csv(TABLES / "month_pass_visit_distribution.csv")
    gp_visit = float(summary.set_index("metric").value["Gross profit per member order (USD)"])
    design = pass_design(df, gp_visit)
    design.to_csv(TABLES / "month_pass_design.csv", index=False)
    sc = scenarios(summary, design.iloc[0])
    sc.to_csv(TABLES / "month_pass_scenarios.csv", index=False)
    td = test_design(tx, sc)
    td.to_csv(TABLES / "month_pass_test_design.csv", index=False)
    dip = -float(pd.read_csv(TABLES / "payday_dip_value.csv").dip_gross_profit_gap_per_year_usd.iloc[0])
    plot(sc, design.iloc[0], dip, FIGS / "month_pass_scenarios.png")

    pd.set_option("display.width", 220)
    print(summary.to_string(index=False), "\n")
    print(dist.T.to_string(), "\n")
    print(design.T.to_string(header=False), "\n")
    print(sc.to_string(index=False), "\n")
    print(td.to_string(index=False))


if __name__ == "__main__":
    main()
