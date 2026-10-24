# Hostel Mess Menu Optimizer

## Project Overview

The Hostel Mess Menu Optimizer uses Multi-Objective Evolutionary Optimization (NSGA-II) to generate weekly hostel mess menus that balance three conflicting objectives:

1. **Minimize average daily cost per student**
2. **Minimize deviation from daily calorie and protein targets**
3. **Minimize student dissatisfaction (accounting for ratings and meal repetition)**

A weekly schedule contains 21 meal selections (7 days × 3 meals per day).

## Current Implementation Status - Phases 3–7

Phase 2 of the project implements the **Menu Evaluation Engine**, which:

- Evaluates a candidate weekly menu against three objective functions
- Checks hard constraints (slot eligibility, calorie bounds, cost caps, vegetarian policy, repetition limits)
- Returns structured results with objectives, daily totals, violation reports, feasibility status, and weekly signatures

Phase 3 adds a constrained, slot-aware **pymoo NSGA-II** optimizer that produces
deduplicated feasible Pareto candidates, stable meal-ID signatures, diagnostics,
and simple random/greedy baselines. See `docs/optimization.md` for usage.

Phases 4–5 add repeatable benchmark outputs and a feasibility-preserving monthly
selector for four diverse weekly schedules. See `docs/benchmarking_and_monthly.md`.

Phase 6 added a Streamlit research interface, retained as a legacy option.
Phase 7 adds a student-facing React app and FastAPI adapter that reuse the same
optimizer, monthly scheduler, dataset, and evaluator. See
`docs/react_frontend.md`.

## Repository Structure

```
sc_meal_planner/
├── data/
│   └── hostel_meal_dataset_cleaned.csv  (authoritative dataset, 200 vegetarian meals)
├── src/
│   └── hostel_optimizer/
│       ├── config.py, data_loader.py, evaluation.py, constraints.py
│       ├── optimization.py, monthly_scheduler.py, experiments.py
│       └── ui/                 # Presentation helpers and theme
├── app.py                     # Streamlit entry point
├── assets/meal_images/        # Illustrative, local dish image sheet
├── frontend/                  # React + TypeScript + Vite student app
├── src/hostel_optimizer/api.py # FastAPI adapter for existing Python logic
├── tests/
│   ├── test_data_loader.py
│   ├── test_evaluation.py
│   └── test_constraints.py
└── docs/
    └── evaluation_engine.md  # Detailed evaluation engine documentation
```

## Dataset

The authoritative dataset is `data/hostel_meal_dataset_cleaned.csv`, containing 200 affordable vegetarian meal options from mixed cuisines (North Indian, South Indian, Gujarati, Maharashtrian, Indo-Chinese, and other practical Indian hostel meals). Each meal has:

- 20 nutritional/cost attributes
- Meal type (breakfast, lunch, dinner) and slot eligibility
- Synthetic student ratings (all rating_count = 0)
- Provenance columns for tracking

## Environment Setup

- Python 3.10+
- Dependencies: pandas, NumPy, pymoo, FastAPI, Uvicorn, Streamlit, Plotly, matplotlib, pytest
- Install: `python -m pip install -e ".[dev]"`
- Launch: `streamlit run app.py`
- Run tests: `python -m pytest -q`

## Dependencies

The Python app and optimizer dependencies are declared in `pyproject.toml`:
- `pandas`, `numpy`, `pymoo` - dataset, evaluation, and optimization
- `fastapi`, `uvicorn` - local HTTP API
- `streamlit`, `plotly` - legacy research interface
- `matplotlib` - saved experiment figures
- `pytest` (development extra) - automated tests

React dependencies are declared separately in `frontend/package.json`. No paid
APIs or external services are used.

## How to Run Tests

```powershell
python -m pytest -q
```

## NSGA-II Optimization

```python
from hostel_optimizer.optimization import OptimizationConfig, optimize_weekly_menus

result = optimize_weekly_menus(OptimizationConfig(population_size=100, generations=100, seed=42))
for solution in result["pareto_solutions"]:
    print(solution["objectives"], solution["signature"])
```

Only feasible, non-dominated weekly schedules are returned. Each uses exactly
21 integer row indices and exposes its stable ordered 21-meal-ID signature.
Use `result["diagnostics"]` when a run finds no feasible schedule. Full details,
including constraints and reproducibility, are in `docs/optimization.md`.

## React Application (Student Interface)

Install Python and frontend dependencies once:

```powershell
python -m pip install -e ".[dev]"
cd frontend
npm install
```

Run the API and frontend in separate terminals from the repository root:

```powershell
python -m uvicorn hostel_optimizer.api:app --app-dir src --reload --host 127.0.0.1 --port 8000
```

```powershell
cd frontend
npm run dev
```

Open the Vite URL printed in the frontend terminal (normally
`http://127.0.0.1:5173`). Vite proxies `/api` to the local Python service.
Generated plans are stored in `data/generated_plans/`, separate from benchmark
artifacts and excluded from version control.

Build with `cd frontend; npm run build`. A deployed frontend still requires a
deployed Python API; a local build is not a hosted application. See
`docs/react_frontend.md` for API behavior, images, and limitations.

## Legacy Streamlit Application

```powershell
python -m pip install -e ".[dev]"
streamlit run app.py
```

The legacy research UI includes a monthly planner, optimization lab, and
benchmark results; it remains available for academic inspection. The React
application above is the primary student interface. See `docs/frontend.md`
for details about the legacy interface.

## Benchmark and Monthly Commands

The ten-seed benchmark instructions and results are documented in
`docs/benchmarking_and_monthly.md`. A short benchmark can be invoked with:

```powershell
$env:PYTHONPATH='src'
python -c "from hostel_optimizer.experiments import ExperimentConfig, run_benchmarks, save_benchmark_results; from hostel_optimizer.optimization import OptimizationConfig; result=run_benchmarks(ExperimentConfig(seeds=(1,), optimization=OptimizationConfig(population_size=20,generations=3))); print(save_benchmark_results(result, 'results', save_plots=True))"
```

Each benchmark save chooses a new run number. To generate a plan and save the
current result through the interface, launch `streamlit run app.py`, open
Monthly Planner, and use its JSON or CSV download controls.

## Example: Evaluating a Weekly Menu

```python
import pandas as pd
from hostel_optimizer import evaluation, config, data_loader

# Load the dataset
df = data_loader.load_dataset()

# Example chromosome: 21 meal indices (one per slot, in slot order)
# Slot order: Monday breakfast, Monday lunch, Monday dinner, Tuesday breakfast, ...
chromosome = [0, 1, 2, 3, 4, 5, 0, 1, 2, 3, 4, 5, 0, 1, 2, 3, 4, 5, 0, 1, 2]

# Evaluate the menu
result = evaluation.evaluate_menu(chromosome, df)

# Results
print("Objectives (all to be minimized):")
print(f"  f1 (avg daily cost):  {result['objectives'][0]:.2f} INR")
print(f"  f2 (nutrition dev):   {result['objectives'][1]:.4f}")
print(f"  f3 (dissatisfaction): {result['objectives'][2]:.4f}")

print("\nDaily totals:")
for day in range(7):
    print(f"  Day {day}: cost={result['daily_totals']['daily_cost'][day]:.1f} INR, "
          f"calories={result['daily_totals']['daily_calories'][day]:.1f} kcal, "
          f"protein={result['daily_totals']['daily_protein'][day]:.1f} g")

print(f"\nFeasible: {result['is_feasible']}")
print(f"Weekly signature (21 meal IDs): {result['weekly_signature']}")
print(f"Constraint violations: {len(result['constraint_violations'])}")
```

## Limitations

- Nutrition estimates are not independently verified; the project is not clinical guidance.
- Ratings are synthetic and do not represent real student feedback.
- Food images are illustrative and do not depict the exact dataset recipe or hostel preparation.
- Benchmark results apply to the measured dataset and run budget only.
- The full 10-seed benchmark is separate from the default test suite
- Monthly selection is a four-week candidate selector, not a calendar-wide optimizer
- Synthetic ratings (all rating_count = 0) - dissatisfaction objective is provisional
- Nutrition targets (2000 kcal, 50 g protein) are provisional defaults that must be calibrated to the actual hostel
- Calorie bounds and cost cap must be hostel-specific
- Repetition window semantics: a meal must not appear within 3 calendar days (same meal on day D and day D+3 is allowed; day D and D+2 is prohibited)
- Vegetarian-only policy is enforced by default but configurable
- Kitchen capacity constraint is disabled by default (see documentation for details)

## Configuration Defaults (Provisional)

- **Days**: 7
- **Meal slots**: breakfast, lunch, dinner (21 total)
- **Calorie target**: 2000 kcal/day (provisional, not medical advice)
- **Protein target**: 50 g/day (provisional)
- **Min calories/day**: 1500 kcal
- **Max calories/day**: 3000 kcal
- **Max cost/day**: 80 INR
- **Vegetarian-only**: True
- **Repetition window**: 3 days
- **Min differing slots (monthly)**: 7 out of 21
