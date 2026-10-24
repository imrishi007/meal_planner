"""Repeatable, evaluator-consistent baselines and benchmark metrics."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from typing import Any, Iterable

import numpy as np
import pandas as pd

from . import config, data_loader, evaluation
from .optimization import (
    _sample_feasible_chromosome,
    _solution_record,
    build_daily_feasible_options,
    build_slot_eligible_indices,
    is_non_dominated,
)


@dataclass(frozen=True)
class BaselineConfig:
    """Bounded, reproducible budgets for non-evolutionary comparisons."""

    random_candidates: int = 100
    greedy_backtracking_limit: int = 100

    def __post_init__(self) -> None:
        if self.random_candidates < 1 or self.greedy_backtracking_limit < 1:
            raise ValueError("Baseline budgets must be positive")


def _pareto_unique(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    unique = {record["signature"]: record for record in records if record["is_feasible"]}
    feasible = list(unique.values())
    return [record for record in feasible if is_non_dominated(record, feasible)]


def random_feasible_search(
    dataset: pd.DataFrame | None = None,
    seed: int = 42,
    config: BaselineConfig | None = None,
) -> dict[str, Any]:
    """Sample bounded feasible weekly candidates using Phase 3's slot-aware builder."""
    settings = config or BaselineConfig()
    source = data_loader.load_dataset() if dataset is None else dataset
    eligible = build_slot_eligible_indices(source)
    daily_options = build_daily_feasible_options(source, eligible)
    rng = np.random.default_rng(seed)
    records = [_solution_record(_sample_feasible_chromosome(daily_options, rng, 100), source) for _ in range(settings.random_candidates)]
    feasible = [record for record in records if record["is_feasible"]]
    return {
        "method": "random_feasible",
        "seed": seed,
        "generated_candidates": len(records),
        "feasible_candidates": len(feasible),
        "infeasible_candidates": len(records) - len(feasible),
        "pareto_solutions": _pareto_unique(feasible),
        "all_feasible_solutions": feasible,
        "message": "Feasible random search completed." if feasible else "No feasible random candidates were generated.",
    }


def greedy_cost_baseline(
    dataset: pd.DataFrame | None = None,
    seed: int = 42,
    config: BaselineConfig | None = None,
) -> dict[str, Any]:
    """Use cost-ranked feasible daily options with deterministic weekly backtracking."""
    settings = config or BaselineConfig()
    source = data_loader.load_dataset() if dataset is None else dataset
    eligible = build_slot_eligible_indices(source)
    daily_options = build_daily_feasible_options(source, eligible)
    costs = source["cost_per_serving_inr"].to_numpy(dtype=float)
    rng = np.random.default_rng(seed)
    ranked = daily_options[np.argsort(costs[daily_options].sum(axis=1), kind="stable")]
    ranked = ranked[rng.permutation(len(ranked))] if len(ranked) == 1 else ranked

    def choose(day: int, selected: list[np.ndarray]) -> list[np.ndarray] | None:
        if day == 7:
            return selected
        recent = set(np.concatenate(selected[-2:])) if selected else set()
        attempts = 0
        for option in ranked:
            if attempts >= settings.greedy_backtracking_limit:
                break
            attempts += 1
            if recent.intersection(option):
                continue
            outcome = choose(day + 1, [*selected, option])
            if outcome is not None:
                return outcome
        return None

    selected = choose(0, [])
    if selected is None:
        return {"method": "greedy_cost", "seed": seed, "generated_candidates": 0, "feasible_candidates": 0, "infeasible_candidates": 0, "pareto_solutions": [], "all_feasible_solutions": [], "message": "Greedy backtracking could not build a feasible week."}
    record = _solution_record(np.concatenate(selected), source)
    feasible = [record] if record["is_feasible"] else []
    return {
        "method": "greedy_cost",
        "seed": seed,
        "generated_candidates": 1,
        "feasible_candidates": len(feasible),
        "infeasible_candidates": 1 - len(feasible),
        "pareto_solutions": feasible,
        "all_feasible_solutions": feasible,
        "message": "Greedy cost baseline completed." if feasible else "Greedy candidate was infeasible.",
    }


def objective_space_diversity(solutions: Iterable[dict[str, Any]]) -> float:
    """Mean pairwise Euclidean distance after per-set min/max normalization."""
    values = np.asarray([solution["objectives"] for solution in solutions], dtype=float)
    if len(values) < 2:
        return 0.0
    span = values.max(axis=0) - values.min(axis=0)
    normalized = (values - values.min(axis=0)) / np.where(span == 0, 1.0, span)
    distances = [float(np.linalg.norm(left - right)) for left, right in combinations(normalized, 2)]
    return float(np.mean(distances))


def summarize_solutions(solutions: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Calculate transparent objective, uniqueness, and diversity summaries."""
    records = list(solutions)
    if not records:
        return {"solution_count": 0, "unique_signatures": 0, "non_dominated_count": 0, "objective_summary": None, "objective_space_diversity": 0.0}
    objectives = np.asarray([record["objectives"] for record in records], dtype=float)
    totals = [record.get("daily_totals") for record in records]
    totals = [item for item in totals if item is not None]
    nutrition_summary = None
    if totals:
        calories = np.asarray([daily for item in totals for daily in item["daily_calories"]], dtype=float)
        protein = np.asarray([daily for item in totals for daily in item["daily_protein"]], dtype=float)
        calorie_deviation = np.abs(calories - config.DEFAULT_CALORIE_TARGET) / config.DEFAULT_CALORIE_TARGET
        protein_deviation = np.abs(protein - config.DEFAULT_PROTEIN_TARGET) / config.DEFAULT_PROTEIN_TARGET
        daily_cost = np.asarray([daily for item in totals for daily in item["daily_cost"]], dtype=float)
        nutrition_summary = {
            "mean_daily_cost_inr": float(daily_cost.mean()),
            "median_daily_cost_inr": float(np.median(daily_cost)),
            "mean_daily_calories_kcal": float(calories.mean()),
            "mean_daily_protein_g": float(protein.mean()),
            "mean_normalized_calorie_deviation": float(calorie_deviation.mean()),
            "mean_normalized_protein_deviation": float(protein_deviation.mean()),
        }
    return {
        "solution_count": len(records),
        "unique_signatures": len({record["signature"] for record in records}),
        "non_dominated_count": len(_pareto_unique(records)),
        "objective_summary": {
            "names": ["average_daily_cost", "nutrition_deviation", "dissatisfaction"],
            "mean": objectives.mean(axis=0).tolist(),
            "median": np.median(objectives, axis=0).tolist(),
            "best": objectives.min(axis=0).tolist(),
            "worst": objectives.max(axis=0).tolist(),
        },
        "objective_space_diversity": objective_space_diversity(records),
        "daily_summary": nutrition_summary,
    }


def serialize_solution(record: dict[str, Any]) -> dict[str, Any]:
    """Return a JSON-compatible public subset of an evaluated weekly record."""
    return {
        "chromosome": [int(value) for value in record["chromosome"]],
        "signature": list(record["signature"]),
        "objectives": [float(value) for value in record["objectives"]],
        "is_feasible": bool(record["is_feasible"]),
        "schedule": record["schedule"],
        "constraint_violations": [violation._asdict() for violation in record["constraint_violations"]],
        "daily_totals": record.get("daily_totals"),
    }
