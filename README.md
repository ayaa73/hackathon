# Stories Coffee: Two Ways to Grow Profit

Hackathon project on Stories Coffee's Jan-Jun 2026 transaction data (3 branches: Garden,
Harbour, Uptown; 45 menu items; 33,887 orders).

## Executive summary

1. **Menu engineering per branch** ([full write-up](docs/menu_engineering.md)).
   53.8% of orders contain a single item, and profit per item varies more than 5x across the
   menu. Classifying every item per branch (Star / Plowhorse / Puzzle / Dog) and acting on it
   (push Stars, pair Plowhorses with Stars, rebrand Puzzles, merge Dogs) is worth an
   **estimated ~$32.8k of extra gross profit a year**, with no new customers. A pairing model
   beats a simple baseline only slightly (15.5% vs 13.4%), so we recommend designed pairings
   proven by an **8-week A/B test at Harbour**.
2. **Holiday truck** ([full write-up](docs/truck_business_case.md)).
   Eid al-Fitr 2026 cut branch revenue by 14% for four days as customers left Beirut. A Stories
   truck that follows the holiday crowd, built on a menu of easy-to-transport best-sellers.
   *(Section owned by teammate B.)*

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

## Approaches considered and rejected

See [docs/approaches_considered_and_rejected.md](docs/approaches_considered_and_rejected.md)
(section to be filled in by the team).

## How to run

```bash
pip install -r requirements.txt
python src/clean.py                         # clean data + integrity checks
python menu_engineering/menu_matrix.py      # Project 1: classify items per branch
python menu_engineering/actions.py          # Project 1: actions, pairings, money estimates
python menu_engineering/pairing_model.py    # Project 1: lift + model vs baseline
python menu_engineering/validate.py         # Project 1: leakage + stability checks (must print "All checks passed")
# Project 2 scripts: see truck/ (run in the order listed in docs/truck_business_case.md)
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
docs/approaches_considered_and_rejected.md  approaches we tried or considered and dropped
outputs/tables, outputs/figures     generated results
```
