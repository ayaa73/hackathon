# Stories Coffee: Two Ways to Grow Profit

Hackathon project on Stories Coffee's Jan-Jun 2026 transaction data (3 branches: Garden,
Harbour, Uptown; 45 menu items; 33,887 orders).

## Executive summary

1. **Menu engineering per branch** ([full write-up](docs/menu_engineering.md)).
   53.8% of orders contain a single item, and profit per item varies more than 5x across the
   menu. Classify every item per branch (Star / Plowhorse / Puzzle / Dog), then push Stars,
   pair Plowhorses with Stars, rebrand Puzzles, and merge Dogs. If the three levers
   each land on their own, the estimate is **~$32.8k of extra gross profit a year**. They can
   overlap, and the bowl push may need new lunch orders. A pairing model beats a simple
   baseline only slightly (15.5% vs 13.4%), so the pairings are designed, then proven by an
   **8-week test at Harbour**.
2. **Should Stories go to the customer?** ([full write-up](docs/truck_business_case.md)).
   Eid al-Fitr was **$923 (−15.7%)** under a local baseline. The gap is fewer orders, not
   proof that customers left Beirut. Start with Eid boxes, then one pop-up. Rent a truck only
   if that pop-up holds about **80 orders a day**. Do not buy one on this file.

**Measured vs estimated:** every number labelled *measured* comes straight from the data.
Every *estimate* is a measured input times a stated assumption, and the assumption is written
next to it.

## Data quality notes

- 132 exact duplicate rows removed (51,177 to 51,045 rows).
- Revenue and gross-profit formulas verified on every row (`src/clean.py`).
- 37% of orders have no Customer ID (walk-ins).
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
| Leakage + stability validation | `menu_engineering/validate.py`, `outputs/tables/matrix_stability.csv` |

![Harbour menu matrix](outputs/figures/matrix_harbour.png)
![Money estimates](outputs/figures/money_estimates.png)

## Project 2: Holiday truck

See [docs/truck_business_case.md](docs/truck_business_case.md) and the `truck/` folder.

## How to run

```bash
pip install -r requirements.txt
python src/clean.py                         # clean data + integrity checks
python menu_engineering/menu_matrix.py      # Project 1: classify items per branch
python menu_engineering/actions.py          # Project 1: actions, pairings, money estimates
python menu_engineering/pairing_model.py    # Project 1: lift + model vs baseline
python menu_engineering/validate.py         # Project 1: leakage + stability checks (must print "All checks passed")
python truck/holiday_dips.py                # Project 2: local holiday baseline
python truck/dip_mechanism.py               # Project 2: orders vs basket, named-customer return
python truck/truck_menu.py                  # Project 2: truck menu economics
python truck/truck_model.py                 # Project 2: rent vs buy at measured demand
python truck/eid_boxes.py                   # Project 2: boxes, targets, retail benchmarks
python truck/service_capacity.py            # Project 2: 8-hour cap and permit stress
python truck/channel_comparison.py          # Project 2: boxes, pop-up, rent, buy
python truck/score_pilot.py                 # Project 2: score truck/pilot_log.csv (empty until a test)
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
outputs/tables, outputs/figures     generated results
```
