# Streamlit application

## Run locally

From the repository root, install the project and development dependencies, then launch Streamlit:

```powershell
python -m pip install -e ".[dev]"
streamlit run app.py
```

The app loads `data/hostel_meal_dataset_cleaned.csv` through the existing validated loader. It does not rewrite dataset rows or optimizer configuration. The currently checked-in `results/monthly_final.json` is shown only if its four weeks revalidate against the dataset, evaluator, and configured diversity threshold. Otherwise, the planner starts empty and offers plan generation.

## Sections

- **Overview:** monthly totals, daily averages, weekly cost, cuisine distribution, and a sample of meals from the current plan.
- **Monthly Planner:** weekly meal detail, daily cost and nutrition, pairwise diversity, monthly repetition, and JSON/CSV download of the current plan. A new plan is installed in the current session only after the scheduler returns a complete valid result.
- **Optimization Lab:** runs the real NSGA-II optimizer with supported parameters, plots the approximate feasible Pareto front, and exposes a returned weekly solution.
- **Benchmark Results:** loads the latest complete `benchmark_run_*_summary.csv` and matching raw JSON. A user-triggered benchmark writes to the existing non-overwriting results convention.
- **Meal Library:** searchable, filterable, paginated view of the actual dataset. Filters are for browsing; they do not change optimizer constraints.
- **Settings:** temporary session controls for supported optimizer and monthly-scheduler settings. Backend calorie, protein, and cost rules are shown read-only to prevent UI/backend disagreement.
- **About:** explains objectives, constraints, technologies, and data limitations.

The app does not automatically run NSGA-II or a benchmark at startup. Optimization and plan generation show a loading state and display user-facing errors if a backend call fails. Technical exceptions are visible to the project operator for debugging.

## Meal imagery

`data/meal_images.json` maps stable meal IDs to tiles in `assets/meal_images/indian_vegetarian_sprite.png`. The local generated sheet provides illustrative coverage for 9 of the 200 meal IDs; other meals receive a branded fallback tile. No meal names are matched fuzzily. Replace or add mappings by meal ID; optional individual local images belong under `assets/meal_images/` and can be declared under `images`. Paths are checked to remain inside the repository. The current image set is illustrative and is not a photograph of an exact meal or hostel kitchen.

## Experiment use

The Benchmark Results page initially displays saved observations; it never fabricates per-run samples from an aggregate. Its optional Run Benchmark form is intentionally small by default. For a reproducible ten-seed run from PowerShell, see `docs/benchmarking_and_monthly.md`; every save uses a new benchmark number rather than replacing an earlier artifact.

## Tests

```powershell
python -m pytest -q
```

UI data helpers can be tested without Streamlit interaction or network access. The image system uses local assets and a fallback; it does not fetch remote images.

## Limitations

- Meal nutrition entries are estimates and have not been independently verified.
- Rating fields are synthetic and are not real student feedback.
- Benchmark findings describe only the specified data and computational budget.
- The monthly scheduler selects among feasible weekly candidates; it is not a calendar-wide optimization over 84 independent meal decisions.
- The monthly diversity default of 7 differing positions out of 21 is an initial design choice, not an evidence-based threshold.
- NSGA-II returns an approximate stochastic Pareto set, not a guarantee of global optimality.
- The daily cost cap remains the provisional ₹80 from the backend configuration.
