"""Phase 4 benchmark and experiment-runner tests."""

import json

from hostel_optimizer import data_loader
from hostel_optimizer.benchmarking import BaselineConfig, objective_space_diversity, random_feasible_search, greedy_cost_baseline, summarize_solutions
from hostel_optimizer.experiments import ExperimentConfig, run_benchmarks, save_benchmark_results
from hostel_optimizer.optimization import OptimizationConfig


def test_baselines_are_feasible_and_reproducible() -> None:
    dataset = data_loader.load_dataset()
    settings = BaselineConfig(random_candidates=4)
    first = random_feasible_search(dataset, seed=5, config=settings)
    second = random_feasible_search(dataset, seed=5, config=settings)
    greedy = greedy_cost_baseline(dataset, seed=5, config=settings)

    assert first["feasible_candidates"] == 4
    assert [item["signature"] for item in first["all_feasible_solutions"]] == [item["signature"] for item in second["all_feasible_solutions"]]
    assert all(item["is_feasible"] for item in first["all_feasible_solutions"])
    assert greedy["feasible_candidates"] == 1
    assert greedy["all_feasible_solutions"][0]["is_feasible"]
    summary = summarize_solutions(first["all_feasible_solutions"])
    assert summary["daily_summary"]["mean_daily_cost_inr"] > 0
    assert summary["daily_summary"]["mean_normalized_calorie_deviation"] >= 0


def test_metric_functions_handle_diversity_and_empty_inputs() -> None:
    records = [{"signature": ("a",), "objectives": (1.0, 2.0, 3.0), "is_feasible": True}, {"signature": ("b",), "objectives": (2.0, 1.0, 3.0), "is_feasible": True}]
    assert objective_space_diversity(records) > 0
    assert summarize_solutions([])["solution_count"] == 0
    assert summarize_solutions(records)["non_dominated_count"] == 2


def test_experiment_runner_writes_structured_outputs(tmp_path) -> None:
    dataset = data_loader.load_dataset()
    settings = ExperimentConfig(seeds=(3,), optimization=OptimizationConfig(population_size=10, generations=1, seed=3), baselines=BaselineConfig(random_candidates=3), save_plots=False)
    result = run_benchmarks(settings, dataset)
    paths = save_benchmark_results(result, str(tmp_path), save_plots=False)

    assert len(result["runs"]) == 3
    assert all("runtime_seconds" in run and "metrics" in run for run in result["runs"])
    assert json.loads(open(paths["json"], encoding="utf-8").read())["dataset_rows"] == 200
    assert open(paths["csv"], encoding="utf-8").read().startswith("method,")
    assert open(paths["summary_csv"], encoding="utf-8").read().startswith("method,")
