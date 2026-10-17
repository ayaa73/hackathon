"""Rebuild every table and chart in the repository, in dependency order.

Run from the repository root:  python run_all.py
Stops at the first script that fails. Takes a few minutes (permutation tests and bootstraps).
"""
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent

STEPS = [
    ("Data", "src/clean.py"),
    ("Data", "src/data_quality.py"),
    ("1. Menu engineering", "menu_engineering/menu_matrix.py"),
    ("1. Menu engineering", "menu_engineering/actions.py"),
    ("1. Menu engineering", "menu_engineering/pairing_model.py"),
    ("1. Menu engineering", "menu_engineering/branch_combos.py"),
    ("1. Menu engineering", "menu_engineering/daypart.py"),
    ("1. Menu engineering", "menu_engineering/garden_case.py"),
    ("1. Menu engineering", "menu_engineering/garden_menu.py"),
    ("1. Menu engineering", "menu_engineering/ab_test_power.py"),
    ("1. Menu engineering", "menu_engineering/evidence_checks.py"),
    ("1. Menu engineering", "menu_engineering/validate.py"),
    ("1. Menu engineering", "menu_engineering/decision_thresholds.py"),
    ("2. Holiday truck", "truck/holiday_dips.py"),
    ("2. Holiday truck", "truck/fitr_alternatives.py"),
    ("2. Holiday truck", "truck/truck_menu.py"),
    ("2. Holiday truck", "truck/eid_boxes.py"),
    ("2. Holiday truck", "truck/truck_model.py"),
    ("2. Holiday truck", "truck/channel_comparison.py"),
    ("3. Morning offer", "morning/morning_demand.py"),
    ("3. Morning offer", "morning/morning_supply.py"),
    ("3. Morning offer", "morning/morning_offer.py"),
    ("3. Morning offer", "morning/decision_thresholds.py"),
    ("4. Payday cycle", "payday/payday_cycle.py"),
    ("4. Payday cycle", "payday/month_pass.py"),
    ("Rejected ideas", "rejected_approaches/event_tests.py"),
]


def main() -> None:
    start = time.time()
    for project, script in STEPS:
        t = time.time()
        res = subprocess.run([sys.executable, script], cwd=ROOT, capture_output=True, text=True)
        if res.returncode != 0:
            print(res.stdout[-2000:], res.stderr[-4000:], sep="\n")
            sys.exit(f"FAILED: {script}")
        if script.endswith("validate.py") and "All checks passed" not in res.stdout:
            print(res.stdout[-2000:])
            sys.exit("FAILED: validation checks did not pass")
        print(f"ok  {project:<22} {script:<40} {time.time() - t:5.1f}s")
    print(f"\nAll {len(STEPS)} scripts ran in {time.time() - start:.0f}s. Results are in outputs/<project>/.")


if __name__ == "__main__":
    main()
