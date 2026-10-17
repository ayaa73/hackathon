# Approaches considered and rejected

The brief asks us to explain what we tried and dropped. This page collects every rejected idea
in one place, with the evidence that killed it. Each project write-up has the full detail.

**Evidence labels:** *Measured* = a table in `outputs/` that `run_all.py` rebuilds.
*Exploratory* = an early check run on this data during the hackathon and not kept as a script
in this repo; treat these as leads that were closed, not as results.

---

## A. Explanations for the sales pattern that the data did not support

Before choosing projects, we tested outside events that might drive Stories' sales. Most of
them turned out to be noise, a holiday, or a weekday effect in disguise. Only the pay cycle
survived, and it became Project 4.

| Idea | What we found | Evidence |
|---|---|---|
| **Pay cycle** (kept) | +5.1% orders on the 28th-7th, -4.1% on the 14th-27th, in all 6 months and 3 branches, p < 0.001 | Measured: [`payday_robustness.csv`](../outputs/payday/tables/payday_robustness.csv) |
| **Eid** (kept, in Project 2) | Eid al-Fitr dip -15.7% (-$923); Adha only -3.2% | Measured: [`eid_holiday_dips.csv`](../outputs/truck/tables/eid_holiday_dips.csv) |
| War news, fuel prices, elections, World Cup, weather and season | No effect beyond normal weekday and trend variation | Exploratory |
| One-off strike night in central Beirut | A real -34% drop, but it happened on a single night and can't be planned around | Exploratory |
| University exams (AUB finals timetable, May 8-17) | No effect on weekend, 8 am or reading-day exam slots. Uptown's late-night "finals" spike was two chain-wide Tuesday nights | Exploratory |
| TikTok-driven item trends | No item spike lasted. The item mix did not change between Jan-Feb and May-Jun (p = 0.17) | Measured: [`evidence_checks.csv`](../outputs/menu_engineering/tables/evidence_checks.csv) |
| Summer expats and tourists | The anonymous-order share stayed flat at 35.9-36.9% every month while airport arrivals rose in May-June | Measured (monthly share from the raw file); arrivals exploratory |
| Champions League and El Clásico nights | No effect overall. El Clásico (May 10) cut late-night sales 27%, but it was one night and also a holiday | Exploratory |
| Ramadan opening hours | Only small shifts in the time of day people come | Exploratory |

## B. Project 1: menu engineering

Full detail: [`1_menu_engineering.md`](1_menu_engineering.md).

| Rejected | Why | Evidence |
|---|---|---|
| Removing every low-profit, low-popularity item ("Dogs") | They are 1.5-3.3% of profit, and Espresso is core to the brand | [`menu_matrix_summary.csv`](../outputs/menu_engineering/tables/menu_matrix_summary.csv) |
| One classification for the whole chain | It misclassifies 8 items for at least one branch | [`class_differences.csv`](../outputs/menu_engineering/tables/class_differences.csv) |
| A complex ML recommender | The simple co-purchase model shows the ceiling is low: 15.5% vs a 13.4% baseline | [`pairing_model_results.csv`](../outputs/menu_engineering/tables/pairing_model_results.csv) |
| Item-to-item suggestions from purchase history | They did not beat the popular baseline on May-Jun | [`branch_combos_validation.csv`](../outputs/menu_engineering/tables/branch_combos_validation.csv) |
| Discount-led promos | Harbour's 15% promo grew +18.9%, the same as Garden with no promo | [`evidence_checks.csv`](../outputs/menu_engineering/tables/evidence_checks.csv) |
| A time-of-day till rule at every branch | It made Garden's suggestions worse (-$0.043 each), so it is used at Harbour only | [`daypart_rule_validation.csv`](../outputs/menu_engineering/tables/daypart_rule_validation.csv) |
| Separate takeaway and dine-in menus | Profit per order is $5.27 vs $5.29 | [`evidence_checks.csv`](../outputs/menu_engineering/tables/evidence_checks.csv) |
| A simple before-vs-after test | It raised false alarms 40% of the time on untouched history; the switchback design raises 5.9% | [`ab_test_placebo.csv`](../outputs/menu_engineering/tables/ab_test_placebo.csv) |
| Fixing Garden by raising prices alone | It would need +20-40% price rises; the root cause is a 43% cost premium | [`garden_items.csv`](../outputs/menu_engineering/tables/garden_items.csv) |

## C. Project 2: holiday truck

Full detail: [`2_holiday_truck.md`](2_holiday_truck.md).

| Rejected | Why | Evidence |
|---|---|---|
| Buying a truck now | -$4.5k to -$10.6k a year at demand the branches have actually seen | [`truck_channel_comparison.csv`](../outputs/truck/tables/truck_channel_comparison.csv) |
| Pitching the truck as the fix for Eid | The Fitr hole is $923; a trailer costs $51,300 | [`eid_holiday_dips.csv`](../outputs/truck/tables/eid_holiday_dips.csv) |
| Planning on 100-300 orders a day | No branch-day has been that high; the best was 193, once | [`truck_scenarios.csv`](../outputs/truck/tables/truck_scenarios.csv) |
| The old six-month weekday baseline | It hid the Adha dip and flattered late spring | [`eid_holiday_dips.csv`](../outputs/truck/tables/eid_holiday_dips.csv) |
| Deep-south and Baalbek stops, Ehden and Beiteddine festivals, Easter 2026, Ashoura | Security, postponed festivals, or dates that fell inside the war | [`2_truck_sources.md`](2_truck_sources.md) |

## D. Project 3: morning offer

Full detail: [`3_morning_offer.md`](3_morning_offer.md).

| Rejected | Why | Evidence |
|---|---|---|
| Fixed-item bundles (e.g. always a croissant) | They need +78-231% stock of one item; an "any pastry" bundle needs +16-43% | [`morning_supply_check.csv`](../outputs/morning/tables/morning_supply_check.csv) |
| Free delivery on single bundles | At a $4 courier cost it needs 87% new customers; at $6 it never pays | [`morning_channel_economics.csv`](../outputs/morning/tables/morning_channel_economics.csv) |
| Delivery apps for the morning offer | 22-30% commission needs 37-51% new customers | [`morning_channel_economics.csv`](../outputs/morning/tables/morning_channel_economics.csv) |
| Treating offices as a proven segment | The data shows no office pattern, so it must be tested | [`morning_facts.csv`](../outputs/morning/tables/morning_facts.csv) |
| Bundles only for existing morning customers | Worth just $300-900 a year | [`morning_upsell_ceiling.csv`](../outputs/morning/tables/morning_upsell_ceiling.csv) |

## E. Project 4: payday cycle

Full detail: [`4_payday_cycle.md`](4_payday_cycle.md).

| Rejected | Why | Evidence |
|---|---|---|
| Month Pass (4 drinks for the price of 3.5) | Only 52 members buy 3+ drinks in half the months, so about 13 buyers a month and -$0.5k to +$0.4k a year | [`month_pass_option_a.csv`](../outputs/payday/tables/month_pass_option_a.csv) |
| Our own first sizing of that pass (61-264 buyers, up to +$11.7k) | The buyer counts were assumed rather than measured; replaced by the measured pool above | [`month_pass_members.csv`](../outputs/payday/tables/month_pass_members.csv) |
| Unlimited coffee subscription | Only 2 members average 3+ drinks a month | [`month_pass_members.csv`](../outputs/payday/tables/month_pass_members.csv) |
| Free-pastry comeback reward | Needs +17.5 points of extra mid-month return to break even | [`comeback_option_b.csv`](../outputs/payday/tables/comeback_option_b.csv) |
| Discounts at the start of the month | They reward visits that happen anyway (+5.1% without any offer) | [`payday_robustness.csv`](../outputs/payday/tables/payday_robustness.csv) |
