# Stories Coffee: Four Ways to Grow Profit

EECE490 hackathon project on Stories Coffee's Jan-Jun 2026 transaction data: 3 branches
(Garden, Harbour, Uptown), 45 menu items, 33,887 orders. Not a sales summary: four business
problems, each with an action, the money it is worth, the explanations we ruled out, the
assumptions that would change the decision, and a test Stories can run before wider use.

## What we recommend

| # | Action | Extra gross profit a year | Basis | The decision changes if | Next step |
|---|---|---|---|---|---|
| 1a | **Fix Garden's sourcing**: it pays 43% more than Harbour for the same items, on all 45 | **~$31.8k** | $15.9k extra cost in 6 months (measured) | The premium is a markup in the export or overhead, not a supplier price: then $0 cash | Compare one Garden and one Harbour invoice for the same item, this week |
| 1b | **Menu engineering per branch**: push Stars, pair Plowhorses with Stars, per-branch till rule | **~$32.8k** if the three levers don't overlap | Estimate on measured item profit | Plowhorse sales fall 7-9% after the +$0.20 rise; the test shows under +4.9% | 12-week switchback test at Harbour |
| 1c | **Garden menu v2**: reorganized board and prices | **$6.1k-$13.6k** | Estimate | Same as 1b | After 1a is answered |
| 2 | **Eid boxes, then one pop-up stand**; rent a truck only if the pop-up proves 80+ orders a day; don't buy one | Boxes ~break-even; pop-up **$1.6k-$3.4k** | Estimate at branch-level demand | Fewer than 37 box pre-orders; pop-up under 80 orders a day (no truck) | Eid box pre-orders |
| 3 | **Morning "coffee + any pastry" bundle** with a loyalty card | **$2.9k-$9.2k** (at +5 orders a day per branch) | Estimate; costs sourced | It needs an extra staff shift (+18 orders a day to pay one); under 11% of users are new | 12-week test at Harbour with today's team |
| 4 | **Move promotions to the mid-month dip** (14th-27th); test a 10%-off comeback reward | Promotions: no cost; reward: up to **~$3.3k** | Cycle measured; reward estimated | The reward lifts mid-month return by less than 4-8 points | 3-month randomized test (max cost $557) |

**Gross profit only:** the data has product costs but no labour, rent or energy, so net gains
will be smaller. **Measured** = computed from the data. **Estimate** = a measured input times
a stated assumption, written next to it. Ideas we tested and dropped (strikes, exams, expats,
football, and options inside each project) are in
[docs/5_rejected_approaches.md](docs/5_rejected_approaches.md).

## How this answers the brief

| The brief asks us to | Where |
|---|---|
| Choose a business problem that matters, with a clear action | [What we recommend](#what-we-recommend); section 1 of each write-up |
| Check data quality | [Data quality](#data-quality): `src/data_quality.py`, including what the replacement transaction IDs can and can't be used for |
| Challenge the first explanation; test alternative explanations | "Challenging the conclusion" in every write-up ([1](docs/1_menu_engineering.md#9-challenging-the-conclusion), [2](docs/2_holiday_truck.md#11-challenging-the-conclusion), [3](docs/3_morning_offer.md#9-challenging-the-conclusion), [4](docs/4_payday_cycle.md#7-challenging-the-conclusion)) and [outside events](docs/5_rejected_approaches.md) |
| Estimate business value, costs and tradeoffs | Money sections of each write-up; every estimate names its assumption |
| Say which assumptions could change the recommended action | "Assumptions that would change the decision" tables, computed by `*/decision_thresholds.py` and the break-even columns |
| Compare any model with a simple baseline, on unseen data | Project 1: pairing model and till rules trained on Jan-Apr, tested on May-Jun against "suggest the most popular" ([section 5](docs/1_menu_engineering.md#5-can-the-data-pick-the-pairings-for-us-model-vs-baseline)); leakage checked by `validate.py` |
| Explain weak areas, uncertainty, possible failures, missing information | "What could go wrong" and "Limits and missing information" in each write-up |
| A practical test before wider use | Project 1: 12-week switchback at Harbour (5.9% false alarms on history). Project 2: box pre-orders, then one pop-up. Project 3: 12 weeks at Harbour. Project 4: randomized test on members, worst case $557 |
| Don't present correlation as proof of cause | Causes are labelled as hypotheses (payday, Eid travel, Garden's cost premium); actions are built on what is measured and confirmed by a test |
| Keep measured results separate from estimated benefits | Every write-up labels each number MEASURED / SOURCED / ESTIMATE / ASSUMPTION; evidence tables in Projects 2-4 |
| Explain important choices and rejected approaches | Method sections; [docs/5_rejected_approaches.md](docs/5_rejected_approaches.md) |

## The four projects

1. **Menu engineering per branch** ([write-up](docs/1_menu_engineering.md)).
   53.8% of orders contain a single item, and profit per item varies more than 5x. Every item
   is classified per branch (Star / Plowhorse / Puzzle / Dog); 8 items change class between
   branches and 12 between morning and night. Each branch gets its own combos and till rule
   (Uptown: drink alone → suggest a Chicken Pesto Sandwich; Garden: a Butter Croissant).
   Members repeat items no more often than chance (15.1% vs 15.3%): their choices are not
   habits, so the menu board and the till likely have room to shape them (the test measures it). On unseen months, purchase-history models beat simple baselines only slightly
   (15.5% vs 13.4% hit rate), so changes are proven with a **switchback test** (checked on
   history: 5.9% false alarms vs 40% for before/after). **Garden** pays 43% more than Harbour
   for the same items; repricing alone can't fix that, sourcing can.
2. **Reaching customers outside the branches** ([write-up](docs/2_holiday_truck.md),
   [sources](docs/2_truck_sources.md)). Revenue dipped **15.7% over Eid al-Fitr** (-$923 vs the
   same weekday in nearby weeks): fewer orders, not smaller baskets, and not proof that customers
   left Beirut. Options are compared from cheapest to dearest: Eid boxes with
   a limited-edition ma'amoul, a pop-up stand, renting a truck, buying one. At the demand
   Stories' branches actually reach (35-90 orders a day, best day ever 193), renting only
   breaks even at Harbour-like demand and **buying does not pay back within two years**, even
   less if Lebanese permits cost near the $17,000 top of the US range. Test days are logged in
   `truck/pilot_log.csv` and scored by `truck/score_pilot.py`.
3. **Filling the idle mornings** ([write-up](docs/3_morning_offer.md),
   [sources](docs/3_morning_sources.md)). Every branch opens at 7:00, yet weekday mornings run
   at about **40% of the night pace**, and **65% of morning hot-coffee orders have no food**.
   A flexible "coffee + any pastry" bundle needs only +16-43% bakery stock (a fixed croissant
   bundle would need +78-231%). A loyalty card pays if 11% of users are new; free delivery
   only works for office packs via an own courier ($2-6 a trip, sourced).
4. **The payday cycle** ([write-up](docs/4_payday_cycle.md)). Orders run **+5.1% from the
   28th to the 7th** and **-4.1% from the 14th to the 27th**, in all 6 months, all 3 branches,
   members and walk-ins (p < 0.001); ticket size doesn't change. A Month Pass was sized on real
   members and **dropped**: only 52 members buy 3+ drinks in half the months, so about 13
   buyers a month and -$0.5k to +$0.4k a year.

## Data quality

Checked by `src/data_quality.py` ([`data_quality_checks.csv`](outputs/data_quality/data_quality_checks.csv)):

- **132 exact duplicate rows removed** (51,177 → 51,045). Each is a second identical line in one
  order with quantity 1; the till records two of an item as quantity 2, so these are export
  repeats ($741, 0.24% of revenue). 34 other repeated products in one order differ in quantity
  or discount and are kept.
- **Replacement transaction IDs:** an ID never spans two dates, times, branches or customers,
  so it is safe for grouping lines into orders. IDs follow the date but are shuffled within each
  day, so they are never used for ordering or timing; Date and Time are.
- Revenue and gross-profit formulas hold on every line; no zero or negative quantities, prices,
  costs or profits; no refunds.
- 36.5% of orders have no Customer ID (walk-ins), steady at 35.9-36.9% every month.
- **No price or unit cost changed** in six months at any branch, so price sensitivity can't be
  measured from this file. Every price move we suggest is tested, not assumed.
- All 3 branches have sales on all 181 days, 7:00-23:59.
- Product costs only: no labour, rent, waste or energy, so all profit figures are **gross**.

## How to run

```bash
pip install -r requirements.txt
python run_all.py
```

Tested with Python 3.13 (pandas 3.0, numpy 2.5, scipy 1.18, matplotlib 3.11).

`run_all.py` runs all 29 scripts in order (about a minute) and stops if any fails, including
if the leakage and stability checks in `menu_engineering/validate.py` don't pass. Each script
can also be run on its own from the repository root, for example
`python payday/payday_cycle.py`.

## Repository structure

```
README.md                     start here
run_all.py                    rebuilds every table and chart
requirements.txt
data/raw/                     stories_transactions.csv (raw export)
src/                          clean.py (shared cleaning), data_quality.py (checks → outputs/data_quality), style.py

menu_engineering/             Project 1 scripts      → outputs/menu_engineering/{tables,figures}
truck/                        Project 2 scripts      → outputs/truck/{tables,figures}
morning/                      Project 3 scripts      → outputs/morning/{tables,figures}
payday/                       Project 4 scripts      → outputs/payday/{tables,figures}
rejected_approaches/          tests of dropped ideas → outputs/rejected_approaches/tables

docs/1_menu_engineering.md    Project 1 write-up for the CEO
docs/2_holiday_truck.md       Project 2 write-up
docs/2_truck_sources.md       Project 2 sources (holidays, security, costs, ma'amoul)
docs/3_morning_offer.md       Project 3 write-up
docs/3_morning_sources.md     Project 3 sources (opening hours, office days, delivery costs)
docs/4_payday_cycle.md        Project 4 write-up
docs/5_rejected_approaches.md everything we tried and dropped, with the evidence
```

## Where each result lives

<details>
<summary><b>Project 1: Menu engineering</b> (<code>outputs/menu_engineering/</code>)</summary>

| Result | Script | Tables / figures |
|---|---|---|
| Menu matrix per branch and chain | `menu_matrix.py` | `menu_matrix_{chain,garden,harbour,uptown}.csv`, `menu_matrix_summary.csv`, `class_differences.csv`, `matrix_*.png` |
| Action per item, designed pairings, money estimates | `actions.py` | `menu_actions.csv`, `designed_pairings.csv`, `money_estimates.csv`, `money_estimates.png` |
| Pairing lift, model vs baseline on unseen months | `pairing_model.py` | `pair_lift_categories.csv`, `pair_lift_products.csv`, `pairing_model_results.csv`, `pairing_model.png` |
| Per-branch combos and till rule, tested on May-Jun | `branch_combos.py` | `branch_combos.csv`, `till_suggestions_by_branch.csv`, `branch_combos_validation.csv`, `branch_combos_validation.png` |
| Time-of-day menu and steerability | `daypart.py` | `daypart_classes.csv`, `daypart_till_rules.csv`, `daypart_rule_validation.csv`, `daypart_stability.csv`, `steerability.csv`, `daypart_class_changes.png` |
| Garden cost leak and options | `garden_case.py` | `garden_items.csv`, `garden_scenarios.csv`, `branch_kpis.csv`, `garden_cost_leak.png`, `garden_scenarios.png` |
| Garden menu v2 | `garden_menu.py` | `garden_menu_v2.csv`, `garden_menu_impact.csv`, `garden_menu_v2.png` |
| Test design checked on history | `ab_test_power.py` | `ab_test_power.csv`, `ab_test_placebo.csv` |
| Every supporting fact quoted in the docs | `evidence_checks.py` | `evidence_checks.csv` |
| Leakage and stability validation | `validate.py` | `matrix_stability.csv` |
| Assumptions that would change the decision | `decision_thresholds.py` | `decision_thresholds.csv` |

</details>

<details>
<summary><b>Project 2: Holiday truck</b> (<code>outputs/truck/</code>)</summary>

| Result | Script | Tables / figures |
|---|---|---|
| Holiday dips vs a local same-weekday baseline | `holiday_dips.py` | `eid_holiday_dips.csv`, `eid_holiday_dips.png` |
| Other explanations for the Eid al-Fitr dip (hours, war) | `fitr_alternatives.py` | `fitr_alternative_checks.csv` |
| Truck menu economics | `truck_menu.py` | `truck_menu.csv`, `truck_menu_summary.csv` |
| Eid boxes, limited edition, targets | `eid_boxes.py` | `eid_boxes.csv`, `eid_box_targets.csv` |
| Rent / buy at measured branch demand | `truck_model.py` | `truck_scenarios.csv`, `truck_breakeven.csv`, `truck_profit_per_day.png`, `truck_breakeven.png`, `truck_payback.png` |
| What the Fitr gap is made of (orders vs basket, named customers) | `dip_mechanism.py` | `eid_dip_mechanism.csv`, `eid_dip_mechanism.png` |
| What an 8-hour shift can hold; permit stress test | `service_capacity.py` | `truck_capacity.csv`, `truck_permit_stress.csv`, `truck_capacity.png` |
| Boxes vs pop-up vs rent vs buy | `channel_comparison.py` | `truck_channel_comparison.csv`, `truck_channel_comparison.png` |
| Score a real pilot against the go numbers | `score_pilot.py` | reads `truck/pilot_log.csv` (empty until a test) |
| Holiday calendar input | `truck/holiday_calendar.csv` | |

</details>

<details>
<summary><b>Project 3: Morning offer</b> (<code>outputs/morning/</code>)</summary>

| Result | Script | Tables / figures |
|---|---|---|
| Orders per hour, morning facts | `morning_demand.py` | `morning_orders_per_hour.csv`, `morning_facts.csv`, `morning_idle_hours.png` |
| Opening times, office days, stock needed, cost stability | `morning_supply.py` | `morning_opening_evidence.csv`, `morning_office_days.csv`, `morning_supply_check.csv`, `morning_cost_stability.csv`, `morning_supply_check.png` |
| Morning menu, bundles, loyalty vs delivery, scenarios, test | `morning_offer.py` | `morning_menu_matrix.csv`, `morning_bundles.csv`, `morning_channel_economics.csv`, `morning_scenarios.csv`, `morning_upsell_ceiling.csv`, `morning_test_design.csv`, `morning_offer_economics.png` |
| Assumptions that would change the decision | `decision_thresholds.py` | `decision_thresholds.csv` |

</details>

<details>
<summary><b>Project 4: Payday cycle</b> (<code>outputs/payday/</code>)</summary>

| Result | Script | Tables / figures |
|---|---|---|
| Day-of-month cycle, robustness, value of the dip | `payday_cycle.py` | `payday_by_day_of_month.csv`, `payday_robustness.csv`, `payday_dip_value.csv`, `payday_cycle.png` |
| Month Pass and comeback reward sized on real members, test design | `month_pass.py` | `month_pass_members.csv`, `month_pass_unit_economics.csv`, `month_pass_option_a.csv`, `comeback_base.csv`, `comeback_option_b.csv`, `payday_offer_tests.csv`, `month_pass_scenarios.png` |

</details>

<details>
<summary><b>Rejected ideas</b> (<code>outputs/rejected_approaches/</code>)</summary>

| Result | Script | Tables / figures |
|---|---|---|
| Strikes, exam periods, expat travel, football nights vs daily sales | `event_tests.py` | `rejected_event_tests.csv` |

</details>

![Garden cost leak](outputs/menu_engineering/figures/garden_cost_leak.png)
![Payday cycle](outputs/payday/figures/payday_cycle.png)
