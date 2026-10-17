# Stories Coffee: Two Ways to Grow Profit

Hackathon project on Stories Coffee's Jan-Jun 2026 transaction data (3 branches: Garden,
Harbour, Uptown; 45 menu items; 33,887 orders).

## Executive summary

1. **Menu engineering per branch** ([full write-up](docs/menu_engineering.md)).
   53.8% of orders contain a single item, and profit per item varies more than 5x across the
   menu. Classifying every item per branch (Star / Plowhorse / Puzzle / Dog) and acting on it
   (push Stars, pair Plowhorses with Stars, rebrand Puzzles, merge Dogs) is worth an
   **estimated ~$32.8k of extra gross profit a year**, with no new customers. Each branch gets
   its own combos and a till rule built from its own sales (e.g. Uptown: drink alone →
   suggest a Chicken Pesto Sandwich; Garden: suggest a Butter Croissant), and a menu board
   that changes with the time of day (12 items change class between morning and night).
   Members repeat items exactly as often as random choice would (15.1% vs 15.3%), so their
   choices are not habits and can be steered by the menu and the till. Tested on
   unseen months, purchase-history models beat simple baselines only slightly, so the changes
   are proven with a **12-week switchback test at Harbour** (a design we checked on history:
   5.9% false alarms vs 40% for a simple before/after test).
   **Garden, the least profitable branch**, pays **43% more than Harbour for the same items**
   ($15.9k extra in six months, measured). Fixing its sourcing is worth an estimated
   **~$31.8k a year**; repricing alone can't fix it. A reorganized **Garden menu v2**
   (featured items that keep their margin, combos, sweets sold with drinks, Harbour-level
   prices on thin items) adds an estimated **$6.1k-$13.6k a year** on top.
2. **Should Stories go to the customer?** ([full write-up](docs/truck_business_case.md)).
   Branch revenue dipped **15.7% over Eid al-Fitr** 2026 (-$923, measured against the same
   weekday in nearby weeks) as customers spent the holiday with family. That raised a bigger
   question, tested from cheapest to most expensive: **Eid boxes + a limited-edition ma'amoul**
   (about 37 boxes of 6 replace the Eid profit gap), a **pop-up stand** at events, and a
   **truck**. At the demand Stories' own branches achieve (35-90 orders a day), renting a
   truck only breaks even at Harbour-like demand and **buying one does not pay back within
   two years**. Recommendation: boxes first, then one pop-up; rent a truck only if the pop-up
   proves 80+ orders a day.

**Measured vs estimated:** every number labelled *measured* comes straight from the data.
Every *estimate* is a measured input times a stated assumption, and the assumption is written
next to it.

## Data quality notes

- 132 exact duplicate rows removed (51,177 to 51,045 rows).
- Revenue and gross-profit formulas verified on every row (`src/clean.py`).
- 36.5% of orders have no Customer ID (walk-ins).
- The file contains product costs only: no labour, rent, waste or energy costs, so all profit
  figures are **gross** profit.

## Project 1: Menu engineering

| Output | File |
|---|---|
| Menu matrix per branch + chain | `outputs/tables/menu_matrix_*.csv`, `outputs/figures/matrix_*.png` |
| Items that change class between branches | `outputs/tables/class_differences.csv` |
| Action for every item at every branch | `outputs/tables/menu_actions.csv` |
| Four designed pairings with prices | `outputs/tables/designed_pairings.csv` |
| Money estimates with assumptions | `outputs/tables/money_estimates.csv`, `outputs/figures/money_estimates.png` |
| Pairing lift + model vs baseline | `outputs/tables/pair_lift_*.csv`, `outputs/tables/pairing_model_results.csv`, `outputs/figures/pairing_model.png` |
| Per-branch combos + till suggestions (from purchase history), tested on May-Jun | `outputs/tables/branch_combos.csv`, `outputs/tables/till_suggestions_by_branch.csv`, `outputs/tables/branch_combos_validation.csv`, `outputs/figures/branch_combos_validation.png` |
| Garden menu v2: reorganized board, new prices, impact in 3 scenarios | `outputs/figures/garden_menu_v2.png`, `outputs/tables/garden_menu_v2.csv`, `outputs/tables/garden_menu_impact.csv` |
| Time-of-day menu (12 items change class), time-of-day till rules tested on May-Jun, steerability test (members choose like random-by-popularity) | `outputs/tables/daypart_*.csv`, `outputs/tables/steerability.csv`, `outputs/figures/daypart_class_changes.png` |
| Garden case: cost leak, item actions, sourcing and repricing scenarios | `outputs/tables/garden_items.csv`, `outputs/tables/garden_scenarios.csv`, `outputs/tables/branch_kpis.csv`, `outputs/figures/garden_cost_leak.png`, `outputs/figures/garden_scenarios.png` |
| Test design checked on history (false alarms, detectable effect) | `outputs/tables/ab_test_power.csv`, `outputs/tables/ab_test_placebo.csv` |
| Evidence checks for every supporting fact quoted in the docs | `outputs/tables/evidence_checks.csv` |
| Leakage + stability validation | `menu_engineering/validate.py`, `outputs/tables/matrix_stability.csv` |

![Harbour menu matrix](outputs/figures/matrix_harbour.png)
![Garden cost leak](outputs/figures/garden_cost_leak.png)
![Money estimates](outputs/figures/money_estimates.png)

## Project 2: Reaching customers outside the branches

| Output | File |
|---|---|
| Holiday dips vs a local same-weekday baseline | `outputs/tables/eid_holiday_dips.csv`, `outputs/figures/eid_holiday_dips.png` |
| Eid boxes, limited edition, profit targets | `outputs/tables/eid_boxes.csv`, `outputs/tables/eid_box_targets.csv` |
| Truck menu economics | `outputs/tables/truck_menu.csv`, `outputs/tables/truck_menu_summary.csv` |
| Truck rent/buy scenarios at measured branch demand | `outputs/tables/truck_scenarios.csv`, `outputs/tables/truck_breakeven.csv`, `outputs/figures/truck_profit_per_day.png` |
| Boxes vs pop-up vs rent vs buy | `outputs/tables/truck_channel_comparison.csv`, `outputs/figures/truck_channel_comparison.png` |
| Holiday calendar, security notes, sources | `truck/holiday_calendar.csv`, `docs/truck_sources.md` |

![Truck profit per day at branch-sized demand](outputs/figures/truck_profit_per_day.png)

## How to run

```bash
pip install -r requirements.txt
python src/clean.py                         # clean data + integrity checks
python menu_engineering/menu_matrix.py      # Project 1: classify items per branch
python menu_engineering/actions.py          # Project 1: actions, pairings, money estimates
python menu_engineering/pairing_model.py    # Project 1: lift + model vs baseline
python menu_engineering/branch_combos.py    # Project 1: per-branch combos + till suggestions + test
python menu_engineering/daypart.py          # Project 1: time-of-day menu + steerability test
python menu_engineering/garden_case.py      # Project 1: Garden cost leak + options
python menu_engineering/garden_menu.py      # Project 1: Garden menu v2 (board, prices, impact)
python menu_engineering/ab_test_power.py    # Project 1: test design checked on history
python menu_engineering/evidence_checks.py  # Project 1: computes every supporting fact quoted in the docs
python menu_engineering/validate.py         # Project 1: leakage + stability checks (must print "All checks passed")
python truck/holiday_dips.py                # Project 2: holiday dips (local baseline)
python truck/truck_menu.py                  # Project 2: truck menu economics
python truck/eid_boxes.py                   # Project 2: Eid boxes + limited edition
python truck/truck_model.py                 # Project 2: rent/buy at measured demand
python truck/channel_comparison.py          # Project 2: boxes vs pop-up vs truck
```

All scripts run from the repository root and write to `outputs/`.

## Repository structure

```
data/raw/stories_transactions.csv   raw export (private repo)
src/clean.py                        load_clean(): shared cleaning for both projects
src/style.py                        shared chart style
menu_engineering/                   Project 1 scripts
truck/                              Project 2 scripts and inputs
docs/menu_engineering.md            Project 1 write-up for the CEO
docs/truck_business_case.md         Project 2 write-up for the CEO
docs/truck_sources.md               Project 2 sources (holidays, security, costs, ma'amoul)
outputs/tables, outputs/figures     generated results
```
