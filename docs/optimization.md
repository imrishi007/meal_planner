# Phase 3: NSGA-II Weekly Optimization

`hostel_optimizer.optimization` searches for **approximate** feasible Pareto-optimal weekly menus. It does not replace the Phase 2 evaluator: every candidate is evaluated through `evaluation.evaluate_menu`, so objective formulas, signatures, and hard-constraint reporting remain consistent.

## Install and run

```bash
python -m pip install -e .
python -c "from hostel_optimizer.optimization import optimize_weekly_menus; result = optimize_weekly_menus(); print(result['message']); print(len(result['pareto_solutions']))"
```

The development defaults are a population of 100, 100 generations, and seed 42. Configure a run explicitly:

```python
from hostel_optimizer import data_loader
from hostel_optimizer.optimization import OptimizationConfig, optimize_weekly_menus

dataset = data_loader.load_dataset()
settings = OptimizationConfig(population_size=100, generations=100, seed=17)
result = optimize_weekly_menus(settings, dataset)

for solution in result["pareto_solutions"]:
    print(solution["objectives"], solution["signature"])
    print(solution["schedule"]["Monday"])
```

## Encoding and operators

A chromosome is 21 dataframe-row integers in the documented Monday-breakfast through Sunday-dinner order. The loader sorts `meal_id` before returning the dataset, creating a stable ID-to-row mapping for each loaded dataset. Results always expose the stronger stable representation: an ordered 21-meal-ID signature.

Initialization samples each position only from the meals whose `suitable_meal_types` contains that slot type. Uniform crossover swaps parents' values at the *same* position, so validity is preserved. Mutation replaces a gene only with another choice from the same slot's eligible set. These discrete operators avoid floating-point rounding and reject malformed representations rather than interpreting them as menus.

## Objectives and constraints

NSGA-II minimizes the evaluator's three objectives: average daily cost, normalized calorie/protein deviation, and dissatisfaction (including configured repetition penalty). There is no single best solution because reducing cost can conflict with nutrition or satisfaction.

The optimizer uses pymoo's constrained comparison (`G <= 0` is satisfied). Daily calorie and cost constraints are normalized by their configured limits; slot, vegetarian, and repetition violations use positive counts. Candidate objectives and violations are always derived from the existing evaluator. Kitchen capacity remains unsupported because Phase 2 does not define operational semantics for it.

Final recommendations are feasible-only, non-dominated, and deduplicated by ordered 21-ID signature. `diagnostics` reports per-generation feasible counts, minimum observed constraint violation, final feasible population size, and the number of distinct signatures. If no feasible solutions exist, the result says so without relaxing constraints.

`random_slot_valid_baseline` and `greedy_low_cost_baseline` use the same evaluator and explicitly report whether they satisfy all hard constraints.

## Reproducibility and future scheduling

Pass a fixed `OptimizationConfig.seed` (or `seed=`) to reproduce a run in the same Python/pymoo environment. Stochastic algorithms do not prove global optimality.

Monthly scheduling is intentionally not implemented. A later layer will reject exact weekly signatures, require at least `MIN_DIFFERING_SLOTS` (initially 7 of 21) between compatible weeks, and track meal frequency across the month. This weekly optimizer returns distinct feasible candidate schedules to support that step.

Ratings are currently synthetic and nutrition values are recipe estimates; objectives and limits need calibration with hostel data before operational use.
