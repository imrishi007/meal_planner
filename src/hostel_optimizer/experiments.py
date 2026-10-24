"""Run, serialize, and visualize repeatable Phase 4 benchmark experiments."""

from __future__ import annotations

import csv
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import data_loader
from .benchmarking import BaselineConfig, greedy_cost_baseline, random_feasible_search, serialize_solution, summarize_solutions
from .optimization import OptimizationConfig, optimize_weekly_menus


@dataclass(frozen=True)
class ExperimentConfig:
    seeds: tuple[int, ...] = tuple(range(10))
    optimization: OptimizationConfig = OptimizationConfig(population_size=40, generations=12)
    baselines: BaselineConfig = BaselineConfig(random_candidates=40)
    dataset_path: str | None = None
    output_dir: str = "results"
    save_plots: bool = True

    def __post_init__(self) -> None:
        if not self.seeds:
            raise ValueError("At least one seed is required")


def _json_default(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, tuple):
        return list(value)
    if hasattr(value, "_asdict"):
        return value._asdict()
    raise TypeError(f"Not JSON serializable: {type(value)!r}")


def _run_method(method: str, seed: int, source: pd.DataFrame, settings: ExperimentConfig) -> dict[str, Any]:
    started = time.perf_counter()
    if method == "nsga2":
        result = optimize_weekly_menus(settings.optimization, source, seed=seed)
        solutions = result["pareto_solutions"]
        generated = result["diagnostics"]["evaluated_candidates"]
        feasible = result["diagnostics"]["evaluated_feasible_candidates"]
        infeasible = result["diagnostics"]["evaluated_infeasible_candidates"]
        message = result["message"]
    elif method == "random_feasible":
        result = random_feasible_search(source, seed, settings.baselines)
        solutions = result["pareto_solutions"]
        generated, feasible, message = result["generated_candidates"], result["feasible_candidates"], result["message"]
        infeasible = result["infeasible_candidates"]
    else:
        result = greedy_cost_baseline(source, seed, settings.baselines)
        solutions = result["pareto_solutions"]
        generated, feasible, message = result["generated_candidates"], result["feasible_candidates"], result["message"]
        infeasible = result["infeasible_candidates"]
    return {
        "method": method,
        "seed": seed,
        "runtime_seconds": time.perf_counter() - started,
        "generated_candidates": generated,
        "feasible_candidates": feasible,
        "infeasible_candidates": infeasible,
        "failed": not bool(solutions),
        "message": message,
        "metrics": summarize_solutions(solutions),
        "solutions": [serialize_solution(solution) for solution in solutions],
    }


def run_benchmarks(config: ExperimentConfig | None = None, dataset: pd.DataFrame | None = None) -> dict[str, Any]:
    """Benchmark NSGA-II and both evaluator-consistent baselines for every seed."""
    settings = config or ExperimentConfig()
    source = data_loader.load_dataset(settings.dataset_path) if dataset is None else dataset
    runs = []
    for seed in settings.seeds:
        for method in ("nsga2", "random_feasible", "greedy_cost"):
            try:
                runs.append(_run_method(method, seed, source, settings))
            except Exception as exc:
                runs.append({"method": method, "seed": seed, "runtime_seconds": None, "generated_candidates": 0, "feasible_candidates": 0, "infeasible_candidates": 0, "failed": True, "message": f"{type(exc).__name__}: {exc}", "metrics": summarize_solutions([]), "solutions": []})
    return {"configuration": asdict(settings), "dataset_rows": len(source), "runs": runs}


def _unique_output_dir(base: str) -> Path:
    root = Path(base)
    root.mkdir(parents=True, exist_ok=True)
    index = 1
    while (root / f"benchmark_run_{index:03d}.json").exists():
        index += 1
    return root / f"benchmark_run_{index:03d}"


def save_benchmark_results(result: dict[str, Any], output_dir: str = "results", save_plots: bool = True) -> dict[str, str]:
    """Write stable, non-overwriting JSON/CSV result files and real-data plots."""
    prefix = _unique_output_dir(output_dir)
    json_path = prefix.with_suffix(".json")
    csv_path = prefix.with_suffix(".csv")
    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, default=_json_default)
    rows: list[dict[str, Any]] = []
    for run in result["runs"]:
        summary = run["metrics"]
        objectives = summary["objective_summary"] or {}
        daily = summary.get("daily_summary") or {}
        rows.append({"method": run["method"], "seed": run["seed"], "runtime_seconds": run["runtime_seconds"], "generated_candidates": run["generated_candidates"], "feasible_candidates": run["feasible_candidates"], "infeasible_candidates": run["infeasible_candidates"], "failed": run["failed"], "unique_signatures": summary["unique_signatures"], "non_dominated_count": summary["non_dominated_count"], "objective_space_diversity": summary["objective_space_diversity"], "mean_daily_cost": daily.get("mean_daily_cost_inr"), "median_daily_cost": daily.get("median_daily_cost_inr"), "mean_daily_calories": daily.get("mean_daily_calories_kcal"), "mean_daily_protein": daily.get("mean_daily_protein_g"), "mean_calorie_deviation": daily.get("mean_normalized_calorie_deviation"), "mean_protein_deviation": daily.get("mean_normalized_protein_deviation"), "mean_dissatisfaction": (objectives.get("mean") or [None, None, None])[2]})
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ["method"])
        writer.writeheader()
        writer.writerows(rows)
    summary_path = prefix.with_name(prefix.name + "_summary.csv")
    aggregate_rows: list[dict[str, Any]] = []
    for method in sorted({row["method"] for row in rows}):
        method_rows = [row for row in rows if row["method"] == method]
        aggregate_rows.append({
            "method": method,
            "runs": len(method_rows),
            "successful_runs": sum(not row["failed"] for row in method_rows),
        "mean_runtime_seconds": float(np.mean([row["runtime_seconds"] for row in method_rows if row["runtime_seconds"] is not None])) if any(row["runtime_seconds"] is not None for row in method_rows) else None,
            "mean_feasible_candidates": float(np.mean([row["feasible_candidates"] for row in method_rows])),
            "mean_non_dominated_count": float(np.mean([row["non_dominated_count"] for row in method_rows])),
            "mean_daily_cost": float(np.mean([row["mean_daily_cost"] for row in method_rows if row["mean_daily_cost"] is not None])) if any(row["mean_daily_cost"] is not None for row in method_rows) else None,
            "mean_daily_calories": float(np.mean([row["mean_daily_calories"] for row in method_rows if row["mean_daily_calories"] is not None])) if any(row["mean_daily_calories"] is not None for row in method_rows) else None,
            "mean_daily_protein": float(np.mean([row["mean_daily_protein"] for row in method_rows if row["mean_daily_protein"] is not None])) if any(row["mean_daily_protein"] is not None for row in method_rows) else None,
            "mean_calorie_deviation": float(np.mean([row["mean_calorie_deviation"] for row in method_rows if row["mean_calorie_deviation"] is not None])) if any(row["mean_calorie_deviation"] is not None for row in method_rows) else None,
            "mean_protein_deviation": float(np.mean([row["mean_protein_deviation"] for row in method_rows if row["mean_protein_deviation"] is not None])) if any(row["mean_protein_deviation"] is not None for row in method_rows) else None,
            "mean_dissatisfaction": float(np.mean([row["mean_dissatisfaction"] for row in method_rows if row["mean_dissatisfaction"] is not None])) if any(row["mean_dissatisfaction"] is not None for row in method_rows) else None,
        })
    with summary_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(aggregate_rows[0]) if aggregate_rows else ["method"])
        writer.writeheader()
        writer.writerows(aggregate_rows)
    outputs = {"json": str(json_path), "csv": str(csv_path), "summary_csv": str(summary_path)}
    if save_plots:
        outputs.update(_save_plots(result, prefix))
    return outputs


def _save_plots(result: dict[str, Any], prefix: Path) -> dict[str, str]:
    """Generate figures only from recorded benchmark data; tolerate empty runs."""
    import matplotlib.pyplot as plt

    outputs: dict[str, str] = {}
    runs = result["runs"]
    fig, axis = plt.subplots()
    for run in runs:
        for solution in run["solutions"]:
            axis.scatter(solution["objectives"][0], solution["objectives"][1], label=run["method"])
    axis.set(xlabel="Average daily cost (INR)", ylabel="Nutrition deviation", title="Recorded feasible Pareto candidates")
    handles, labels = axis.get_legend_handles_labels()
    if handles:
        axis.legend(dict(zip(labels, handles)).values(), dict(zip(labels, handles)).keys())
    path = prefix.with_name(prefix.name + "_pareto.png")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    outputs["pareto_plot"] = str(path)
    fig, axis = plt.subplots()
    grouped: dict[str, list[float]] = {}
    for run in runs:
        mean = (run["metrics"]["objective_summary"] or {}).get("mean")
        if mean:
            grouped.setdefault(run["method"], []).append(mean[0])
    for method, values in grouped.items():
        axis.plot(range(len(values)), values, marker="o", label=method)
    axis.set(xlabel="Seed-run index", ylabel="Mean daily cost (INR)", title="Objective variation across seeds")
    if grouped:
        axis.legend()
    path = prefix.with_name(prefix.name + "_objective_variation.png")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    outputs["objective_variation_plot"] = str(path)
    fig, axis = plt.subplots()
    methods = sorted({run["method"] for run in runs})
    feasible = [sum(run["feasible_candidates"] for run in runs if run["method"] == method) for method in methods]
    axis.bar(methods, feasible)
    axis.set(xlabel="Method", ylabel="Feasible candidates", title="Feasibility summary")
    path = prefix.with_name(prefix.name + "_feasibility.png")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    outputs["feasibility_plot"] = str(path)
    fig, axis = plt.subplots()
    diversity = [float(run["metrics"]["objective_space_diversity"]) for run in runs]
    labels = [f"{run['method']}:{run['seed']}" for run in runs]
    axis.bar(range(len(diversity)), diversity)
    axis.set(xlabel="Method:seed run", ylabel="Normalized objective-space diversity", title="Diversity summary")
    axis.set_xticks(range(len(labels)), labels, rotation=45, ha="right")
    path = prefix.with_name(prefix.name + "_diversity.png")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    outputs["diversity_plot"] = str(path)
    return outputs
