# Phases 4 and 5: Benchmarking and Monthly Scheduling

## Benchmarking

`hostel_optimizer.experiments.run_benchmarks` evaluates NSGA-II, random feasible search, and greedy cost selection against the same dataset, Phase 2 evaluator, and hard constraints. Random search reuses the slot-aware feasible weekly builder. The greedy baseline ranks daily triples by cost and uses bounded backtracking to avoid the existing repetition rule.

Each run records seed, runtime, generated/feasible/infeasible counts, unique signatures, non-dominated count, objective values, and normalized objective-space diversity. Diversity is mean pairwise Euclidean distance after per-run min/max normalization; it is not comparable across differently scaled definitions. NSGA-II's generated-candidate count is an estimated population × generation budget, so it should not be treated as identical work to baseline candidate counts.

Run a short verified smoke benchmark:

```powershell
$env:PYTHONPATH='src'
python -c "from hostel_optimizer.experiments import ExperimentConfig, run_benchmarks, save_benchmark_results; from hostel_optimizer.optimization import OptimizationConfig; result=run_benchmarks(ExperimentConfig(seeds=(1,2), optimization=OptimizationConfig(population_size=20,generations=3), output_dir='results')); print(save_benchmark_results(result, 'results'))"
```

For the documented ten-seed experiment, use `seeds=tuple(range(10))`. It is intentionally not part of pytest because NSGA-II evaluation is computationally expensive. Each save creates the next `results/benchmark_run_###.{json,csv}` plus an aggregate `_summary.csv` and measured plots for Pareto candidates, objective variation, feasibility, and diversity; existing result files are not overwritten.

All findings are simulation measurements on estimated nutrition and synthetic ratings. They are not evidence of real nutritional adequacy or student satisfaction.

### Measured smoke findings

The checked-in smoke artifacts in `results/benchmark_run_001.csv` used seeds 1 and 2, population 20, three generations, and 40 random candidates. NSGA-II produced 10 and 7 unique non-dominated schedules, respectively, in about 1.08 seconds per seed. Random feasible search produced 16 and 8, in about 0.57 seconds. The single greedy result cost ₹75.71/day; the NSGA-II mean candidate costs were ₹78.97 and ₹78.94/day. This small run does **not** establish overall superiority: it uses different candidate budgets and is only a reproducible smoke comparison.

## Monthly scheduling

`schedule_monthly_menu` selects four independently feasible weekly records. It rejects duplicate 21-ID signatures and requires every pair to differ in at least `MIN_DIFFERING_SLOTS` positions (default 7). It never relaxes that threshold. Candidates may be supplied directly, or `build_weekly_candidate_pool` runs multiple seeded NSGA-II searches.

Valid combinations are scored by min/max-normalized weekly objectives plus a configurable month-wide meal-frequency penalty. The weights are transparent configuration assumptions, not scientifically validated preferences. The output includes schedules, objectives, pairwise differences, total and average cost, daily nutrition summaries, meal-frequency statistics, diagnostics, and reproducibility metadata. Use `serialize_monthly_result` before `json.dump`.

```powershell
$env:PYTHONPATH='src'
python -c "import json; from hostel_optimizer.monthly_scheduler import MonthlySchedulerConfig, schedule_monthly_menu, serialize_monthly_result; from hostel_optimizer.optimization import OptimizationConfig; result=schedule_monthly_menu(scheduler_config=MonthlySchedulerConfig(candidate_runs=2), optimization_config=OptimizationConfig(population_size=20,generations=3)); print(result['message']); json.dump(serialize_monthly_result(result), open('results/monthly_smoke.json','w'), indent=2)"
```

The scheduler is deliberately not a calendar-wide optimizer: it preserves weekly daily constraints, prepares stable weekly signatures for a later calendar layer, and does not implement frontend, Plotly, or monthly frequency hard limits.

The real-data monthly smoke output in `results/monthly_smoke.json` used two short NSGA-II runs and selected four weeks from 23 candidates. Pairwise differences ranged from 17 to 21 slots, above the required 7. It reported ₹2,196 total cost, ₹78.43 average daily cost, 21 distinct meals, and maximum meal frequency 9. These are synthetic planning outputs, not validated operational recommendations.

The completed ten-seed run is summarized in `results/benchmark_run_004_summary.csv` (with raw candidate/run data in `benchmark_run_004.json` and `.csv`). It used population 40 and 12 generations. All 10 runs for every method found feasible candidates. Mean runtimes were 7.430 seconds for NSGA-II, 0.583 seconds for random feasible search, and 0.036 seconds for greedy cost selection. NSGA-II evaluated 480 candidates per run on average, with 40.1 feasible evaluations; random evaluated 40 feasible candidates; greedy produced one feasible candidate. Mean non-dominated counts were 13.2, 13.2, and 1 respectively. Mean daily costs were ₹78.898, ₹78.898, and ₹75.714; average daily calories were 1,508.98, 1,508.98, and 1,501.43 kcal, and protein was 62.38, 62.38, and 59.86 g. These results describe this dataset and budget only, and do not establish that one method is universally better.
