# Project 4: The payday cycle and a Stories Month Pass

**Conclusion for the CEO:** Stories' sales follow the monthly pay cycle. Orders run **5% above
normal from the 28th to the 7th** and **4% below normal from the 14th to the 27th**, in every
month, every branch, and for members and walk-ins alike. Two actions follow:

1. **Move promotion money into the mid-month dip** (14th-27th) and stop spending it at the start
   of the month, when customers come anyway. No new product needed.
2. **Test a "Month Pass"** (4 drinks for the price of 3.5), sold only right after payday and
   rewarding mid-month visits. It pays only if it creates **0.80 extra visits per pass**: the
   estimates range from **-$1.2k to +$11.7k gross profit a year**, so it must be proven with a
   randomized test on regular members before rollout.

> **MEASURED** = computed from the Jan-Jun 2026 transaction file. **DESIGN** = a choice we make.
> **ASSUMPTION** = an unknown shown as a range. Evidence table in section 6.

---

## 1. The finding: a monthly cycle in visits (measured)

Code: [`payday/payday_cycle.py`](../payday/payday_cycle.py). Each day is compared with the same
weekday within ±21 days (so weekdays and the growth trend cancel), public holidays excluded.

![Payday cycle](../outputs/figures/payday_cycle.png)

| Part of the month | Orders vs a normal day |
|---|---|
| **28th-7th** (just paid) | **+5.1%** |
| 8th-13th | about normal |
| **14th-27th** (before payday) | **-4.1%** |

**It holds everywhere** ([`payday_robustness.csv`](../outputs/tables/payday_robustness.csv)):

| Scope | Gap between the busy and quiet parts of the month |
|---|---|
| Each month, Jan-Jun | +5.1, +16.8, +14.9, +9.9, +6.3, +1.4 points (positive in all 6) |
| Garden / Harbour / Uptown | +8.5 / +10.6 / +6.9 points |
| Members / walk-ins | +9.7 / +8.1 points |
| Statistical check | p < 0.001 (5,000 random reshuffles of the days) |

**Ticket size does not change** ($8.98 vs $9.04, p = 0.84): the cycle is in **how many people
come**, not how much they spend.

**Why "payday":** the timing matches salaries paid around the end of the month. I found no
official source for Lebanese pay dates, so payday is the most likely explanation, not a proven
one. The cycle itself is measured.

**How much money the dip represents:** the 14th-27th days earn **$36.8 less gross profit per
day** than normal; over a year that is **about $5.5k**
([`payday_dip_value.csv`](../outputs/tables/payday_dip_value.csv)). That is the ceiling for
"filling the dip", so the larger prize is raising how often members come (section 3).

## 2. Action 1: time promotions to the dip (no new product)

The Harbour 15% promo of March-May changed nothing (Project 1, `evidence_checks.csv`), and
promotions at the start of the month reward customers who come anyway. So:

- Put **loyalty double points, combos and the Project 3 morning bundle pushes on the 14th-27th**.
- Plan **staff and stock for the 28th-7th**, when visits run 5% above normal.
- Cost: none beyond the promotions Stories would run anyway.

## 3. Action 2: the Stories Month Pass

Code: [`payday/month_pass.py`](../payday/month_pass.py).

### Who would buy it (measured)

| | |
|---|---|
| Members (customer IDs) | 3,494; about 2,237 active in a given month |
| Median member | **1.0 visit a month** (90th percentile: 1.5) |
| **Regulars** (1.5+ visits a month) | **607 members**, 1.67 visits a month on average |
| Members with 2+ visits a month | only 79 |
| Gross profit per member visit | $5.28 |

An "unlimited coffee" subscription would interest a few dozen people. The pass must be small
and aimed at the 607 regulars.

### The design

| | |
|---|---|
| **What** | 4 drinks for the price of 3.5, valid until the end of the month (DESIGN) |
| **Price** | **$18.05** (average drink $5.16, MEASURED) |
| **When sold** | Only the **28th-7th**, when customers have just been paid |
| **Mid-month hook** | A **free pastry** when a pass drink is redeemed on the **14th-27th** |
| **Cost per pass** | $2.58 discount + $1.64 pastry cost = **$4.22** |
| **Break-even** | **0.80 extra visits per pass** ($4.22 / $5.28 profit per visit) |

Table: [`month_pass_design.csv`](../outputs/tables/month_pass_design.csv).

### What it could earn (estimate)

![Month Pass scenarios](../outputs/figures/month_pass_scenarios.png)

| Scenario | Regulars buying | Other active members buying | Extra visits per buyer a month | Buyers a month | **Gross profit a year** | Cash collected up front a year |
|---|---|---|---|---|---|---|
| Conservative | 10% | 0% | 0.5 | 61 | **-$1,151** | $13,148 |
| Central | 20% | 3% | 1.0 | 170 | **+$2,166** | $36,887 |
| Optimistic | 30% | 5% | 1.5 | 264 | **+$11,704** | $57,096 |

([`month_pass_scenarios.csv`](../outputs/tables/month_pass_scenarios.csv)). Unused pass drinks
would add profit; they are left out, so these figures are cautious on that point.

**Honest read:** the pass is **not a sure win**. If buyers only add half a visit a month it
loses money; at one extra visit it earns a little; it pays well only if it really changes
habits. Its other benefits are real but not profit: **cash paid up front** ($13k-$57k a year,
useful given Lebanon's banking situation) and **more identified customers**.

## 4. How to test it: a randomized trial on regulars

Members have IDs, so Stories can do what most cafés cannot: **offer the pass to a random half
of the 607 regulars** and compare both halves for 3 months. Because the split is random, any
difference is caused by the pass.

| | Offer to all members | **Offer to regulars only** |
|---|---|---|
| Members per half | 1,747 | **303** |
| Smallest detectable difference (visits per member a month) | 0.059 | **0.134** |
| Expected effect, central scenario | 0.049 (too small to see) | **0.200 (detectable)** |
| Expected effect, conservative scenario | 0.009 | 0.050 (not detectable) |

([`month_pass_test_design.csv`](../outputs/tables/month_pass_test_design.csv)). Testing on
regulars is the design that works: the central case would show clearly, and if the effect is
as small as the conservative case, the pass loses money anyway, so "no visible effect, stop" is
the right call.

**Decision after 3 months:** offered regulars earn more gross profit per member than the
others after discounts and pastries → roll out. Otherwise → stop and keep only Action 1.

## 5. Limits

- **No official pay dates found**: the cycle is measured, the payday explanation is not.
- **June is the weakest month for the cycle** (+1.4 points); watch whether it fades.
- **Uptake and extra visits are unknown**; that is what the test measures.
- **Unused pass drinks** (customers who pay and don't come back) are not counted.
- **Gross profit only**: no labour or overhead in the data.

## 6. Evidence table

| Claim | Type | Source |
|---|---|---|
| +5.1% on the 28th-7th, -4.1% on the 14th-27th | MEASURED | `payday_by_day_of_month.csv`, `payday_robustness.csv` |
| Holds in all 6 months, 3 branches, members and walk-ins | MEASURED | `payday_robustness.csv` |
| Ticket size unchanged | MEASURED | `payday_robustness.csv` |
| Dip worth ~$5.5k gross profit a year | MEASURED | `payday_dip_value.csv` |
| Holidays excluded | SOURCED | HolidayDB 2026 (see `docs/morning_sources.md`) |
| Member frequency, 607 regulars, $5.28 per visit | MEASURED | `month_pass_members.csv`, `month_pass_visit_distribution.csv` |
| Average drink price and cost, pastry cost | MEASURED | `month_pass_design.csv` |
| 4-for-3.5 pass, sold 28th-7th, mid-month pastry | DESIGN | `payday/month_pass.py` |
| Uptake and extra visits | ASSUMPTION (3 scenarios) | `month_pass_scenarios.csv` |
| Test can detect 0.134 extra visits among regulars | MEASURED from history | `month_pass_test_design.csv` |

## 7. Approaches rejected

- **Unlimited monthly coffee subscription:** only 79 members visit 2+ times a month.
- **Discounts at the start of the month:** they reward visits that happen anyway.
- **Offering the pass to all members as the test:** the effect would be too diluted to detect.
