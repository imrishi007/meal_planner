"""Select diverse, feasible weekly candidates for a four-week monthly menu."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from itertools import combinations
from typing import Any, Iterable

import numpy as np
import pandas as pd

from . import config, data_loader, evaluation
from .optimization import OptimizationConfig, optimize_weekly_menus


@dataclass(frozen=True)
class MonthlySchedulerConfig:
    weeks: int = 4
    min_differing_slots: int = config.MIN_DIFFERING_SLOTS
    candidate_runs: int = 2
    candidate_limit: int = 24
    seed: int = 42
    objective_weights: tuple[float, float, float] = (1.0, 1.0, 1.0)
    repetition_weight: float = 0.25

    def __post_init__(self) -> None:
        if self.weeks < 1 or self.candidate_runs < 1 or self.candidate_limit < self.weeks:
            raise ValueError("Invalid monthly scheduler candidate settings")
        if self.min_differing_slots < 0 or self.min_differing_slots > config.NUM_SLOTS:
            raise ValueError("min_differing_slots must be between 0 and 21")
        if len(self.objective_weights) != 3 or any(weight < 0 for weight in self.objective_weights):
            raise ValueError("objective_weights must contain three non-negative values")


def weekly_slot_difference(left: Iterable[str], right: Iterable[str]) -> int:
    """Count different stable meal IDs at the same 21 weekly positions."""
    first, second = tuple(left), tuple(right)
    if len(first) != config.NUM_SLOTS or len(second) != config.NUM_SLOTS:
        raise ValueError("Weekly signatures must each contain 21 meal IDs")
    return sum(a != b for a, b in zip(first, second))


def _valid_records(candidates: Iterable[dict[str, Any]], dataset: pd.DataFrame) -> list[dict[str, Any]]:
    unique: dict[tuple[str, ...], dict[str, Any]] = {}
    for candidate in candidates:
        chromosome = candidate.get("chromosome")
        signature = candidate.get("signature")
        if chromosome is None or signature is None:
            continue
        try:
            genes = [int(gene) for gene in chromosome]
            result = evaluation.evaluate_menu(genes, dataset)
        except (TypeError, ValueError, IndexError, KeyError):
            continue
        if result["is_feasible"] and tuple(result["weekly_signature"]) == tuple(signature):
            candidate = dict(candidate)
            candidate["chromosome"] = genes
            candidate["objectives"] = tuple(float(value) for value in result["objectives"])
            candidate["schedule"] = evaluation.chromosome_to_schedule(candidate["chromosome"], dataset)
            candidate["meal_details"] = [
                {
                    "slot": slot,
                    "meal_id": str(dataset.iloc[int(gene)]["meal_id"]),
                    "meal_name": str(dataset.iloc[int(gene)]["meal_name"]),
                    "primary_cuisine": str(dataset.iloc[int(gene)]["primary_cuisine"]),
                    "is_veg": bool(dataset.iloc[int(gene)]["is_veg"]),
                    "cost": float(dataset.iloc[int(gene)]["cost_per_serving_inr"]),
                    "calories": float(dataset.iloc[int(gene)]["calories_kcal"]),
                    "protein": float(dataset.iloc[int(gene)]["protein_g"]),
                }
                for slot, gene in zip(config.SLOT_ORDER, candidate["chromosome"])
            ]
            candidate["is_feasible"] = True
            unique.setdefault(tuple(signature), candidate)
    return list(unique.values())


def build_weekly_candidate_pool(
    scheduler_config: MonthlySchedulerConfig | None = None,
    optimization_config: OptimizationConfig | None = None,
    dataset: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Run multiple seeded NSGA-II searches and deduplicate feasible results."""
    settings = scheduler_config or MonthlySchedulerConfig()
    source = data_loader.load_dataset() if dataset is None else dataset
    base = optimization_config or OptimizationConfig(population_size=40, generations=12, seed=settings.seed)
    candidates: list[dict[str, Any]] = []
    run_diagnostics: list[dict[str, Any]] = []
    for offset in range(settings.candidate_runs):
        seed = settings.seed + offset
        result = optimize_weekly_menus(base, source, seed=seed)
        candidates.extend(result["pareto_solutions"])
        run_diagnostics.append({"seed": seed, "candidate_count": len(result["pareto_solutions"]), "message": result["message"]})
    records = _valid_records(candidates, source)
    return {"candidates": records, "run_diagnostics": run_diagnostics, "candidate_pool_size": len(records)}


def _combination_score(records: tuple[dict[str, Any], ...], pool: list[dict[str, Any]], settings: MonthlySchedulerConfig) -> float:
    objectives = np.asarray([record["objectives"] for record in pool], dtype=float)
    span = objectives.max(axis=0) - objectives.min(axis=0)
    normalized = (np.asarray([record["objectives"] for record in records]) - objectives.min(axis=0)) / np.where(span == 0, 1.0, span)
    weights = np.asarray(settings.objective_weights, dtype=float)
    quality = float(np.mean(normalized @ (weights / weights.sum()))) if weights.any() else 0.0
    frequencies = Counter(meal for record in records for meal in record["signature"])
    repetition = sum(count * (count - 1) for count in frequencies.values()) / (config.NUM_SLOTS * settings.weeks * (settings.weeks - 1 or 1))
    return quality + settings.repetition_weight * repetition


def _monthly_summary(records: list[dict[str, Any]], dataset: pd.DataFrame) -> dict[str, Any]:
    evaluations = [evaluation.evaluate_menu(record["chromosome"], dataset) for record in records]
    frequencies = Counter(meal for record in records for meal in record["signature"])
    costs = sum(sum(item["daily_totals"]["daily_cost"]) for item in evaluations)
    calories = [value for item in evaluations for value in item["daily_totals"]["daily_calories"]]
    protein = [value for item in evaluations for value in item["daily_totals"]["daily_protein"]]
    return {
        "monthly_total_cost": float(costs),
        "average_daily_cost": float(costs / (len(records) * config.DAYS)),
        "average_daily_calories": float(np.mean(calories)),
        "average_daily_protein": float(np.mean(protein)),
        "distinct_meal_count": len(frequencies),
        "meal_frequencies": dict(sorted(frequencies.items())),
        "maximum_meal_frequency": max(frequencies.values(), default=0),
        "repeated_meal_occurrences": int(sum(count - 1 for count in frequencies.values() if count > 1)),
    }


def schedule_monthly_menu(
    candidates: Iterable[dict[str, Any]] | None = None,
    scheduler_config: MonthlySchedulerConfig | None = None,
    optimization_config: OptimizationConfig | None = None,
    dataset: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Select a feasible, pairwise-diverse monthly set without relaxing rules."""
    settings = scheduler_config or MonthlySchedulerConfig()
    source = data_loader.load_dataset() if dataset is None else dataset
    diagnostics: dict[str, Any] = {}
    if candidates is None:
        pool_result = build_weekly_candidate_pool(settings, optimization_config, source)
        candidates = pool_result["candidates"]
        diagnostics.update({key: value for key, value in pool_result.items() if key != "candidates"})
    pool = _valid_records(candidates, source)
    diagnostics["candidate_pool_size"] = len(pool)
    if len(pool) < settings.weeks:
        return {"has_schedule": False, "weeks": [], "message": "Insufficient feasible unique weekly candidates.", "diagnostics": diagnostics, "settings": asdict(settings), "seed": settings.seed}
    ordered = sorted(pool, key=lambda record: record["objectives"])[: settings.candidate_limit]
    valid: list[tuple[dict[str, Any], ...]] = []
    for combination in combinations(ordered, settings.weeks):
        if all(weekly_slot_difference(left["signature"], right["signature"]) >= settings.min_differing_slots for left, right in combinations(combination, 2)):
            valid.append(combination)
    diagnostics["combinations_considered"] = len(list(combinations(ordered, settings.weeks)))
    diagnostics["valid_diverse_combinations"] = len(valid)
    if not valid:
        return {"has_schedule": False, "weeks": [], "message": "No weekly combination satisfies the configured diversity threshold; constraints were not relaxed.", "diagnostics": diagnostics, "settings": asdict(settings), "seed": settings.seed}
    selected = list(min(valid, key=lambda combination: _combination_score(combination, ordered, settings)))
    differences = [{"week_a": first + 1, "week_b": second + 1, "different_slots": weekly_slot_difference(left["signature"], right["signature"])} for (first, left), (second, right) in combinations(enumerate(selected), 2)]
    return {
        "has_schedule": True,
        "weeks": [{"week_number": index + 1, **record} for index, record in enumerate(selected)],
        "pairwise_differences": differences,
        "monthly_summary": _monthly_summary(selected, source),
        "settings": asdict(settings),
        "seed": settings.seed,
        "diagnostics": diagnostics,
        "message": "Feasible four-week schedule selected with the configured diversity threshold.",
    }


def serialize_monthly_result(result: dict[str, Any]) -> dict[str, Any]:
    """Convert a monthly result to JSON-compatible built-in values."""
    def convert(value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): convert(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [convert(item) for item in value]
        if isinstance(value, np.generic):
            return value.item()
        if hasattr(value, "_asdict"):
            return convert(value._asdict())
        return value
    return convert(result)
