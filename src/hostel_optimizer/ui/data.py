"""Pure presentation-data helpers for the Streamlit application."""

from __future__ import annotations

import csv
import io
import json
from collections import Counter
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .. import config, evaluation
from ..monthly_scheduler import serialize_monthly_result, weekly_slot_difference

REPO_ROOT = Path(__file__).resolve().parents[3]
DATASET_PATH = REPO_ROOT / "data" / "hostel_meal_dataset_cleaned.csv"


def filter_meals(
    dataset: pd.DataFrame,
    *,
    query: str = "",
    cuisine: str | None = None,
    meal_type: str | None = None,
    cost_range: tuple[float, float] | None = None,
    calorie_range: tuple[float, float] | None = None,
    protein_range: tuple[float, float] | None = None,
) -> pd.DataFrame:
    """Return a filtered copy without changing the authoritative dataframe."""
    filtered = dataset.copy()
    if query.strip():
        filtered = filtered[filtered["meal_name"].astype(str).str.contains(query.strip(), case=False, na=False)]
    if cuisine and cuisine != "All cuisines":
        filtered = filtered[filtered["primary_cuisine"] == cuisine]
    if meal_type and meal_type != "All slots":
        filtered = filtered[
            filtered["suitable_meal_types"].astype(str).map(
                lambda value: meal_type.lower() in {part.strip().lower() for part in value.split(";")}
            )
        ]
    for column, bounds in (
        ("cost_per_serving_inr", cost_range),
        ("calories_kcal", calorie_range),
        ("protein_g", protein_range),
    ):
        if bounds is not None:
            filtered = filtered[filtered[column].between(bounds[0], bounds[1])]
    return filtered.reset_index(drop=True)


def weekly_meal_rows(week: dict[str, Any], dataset: pd.DataFrame) -> list[dict[str, Any]]:
    """Resolve one weekly result to its 21 dataset-backed meal rows."""
    signature = week.get("signature")
    if not isinstance(signature, (list, tuple)) or len(signature) != config.NUM_SLOTS:
        raise ValueError("A weekly result must contain 21 ordered meal IDs")
    indexed = dataset.set_index(dataset["meal_id"].astype(str), drop=False)
    rows: list[dict[str, Any]] = []
    for slot_index, (slot, meal_id) in enumerate(zip(config.SLOT_ORDER, signature)):
        meal_id = str(meal_id)
        if meal_id not in indexed.index:
            raise ValueError(f"Weekly schedule refers to unknown meal ID {meal_id}")
        meal = indexed.loc[meal_id]
        if isinstance(meal, pd.DataFrame):
            raise ValueError(f"Meal ID {meal_id} is not unique in the dataset")
        rows.append({
            "slot_index": slot_index,
            "day": slot.split(" ", 1)[0],
            "slot": slot.split(" ", 1)[1],
            "meal_id": meal_id,
            "meal_name": str(meal["meal_name"]),
            "cuisine": str(meal["primary_cuisine"]),
            "cost": float(meal["cost_per_serving_inr"]),
            "calories": float(meal["calories_kcal"]),
            "protein": float(meal["protein_g"]),
            "rating": float(meal["student_rating"]),
            "rating_source": str(meal["rating_source"]),
            "is_veg": bool(meal["is_veg"]),
        })
    return rows


def weekly_daily_totals(week: dict[str, Any], dataset: pd.DataFrame) -> dict[str, list[float]]:
    """Calculate daily totals through the existing Phase 2 evaluator."""
    chromosome = week.get("chromosome")
    if chromosome is None:
        raise ValueError("Weekly result is missing its chromosome")
    result = evaluation.evaluate_menu([int(gene) for gene in chromosome], dataset)
    return result["daily_totals"]


def validate_monthly_result(result: dict[str, Any], dataset: pd.DataFrame) -> tuple[bool, str]:
    """Recheck the scheduler's weekly invariants before presenting a plan."""
    if not isinstance(result, dict) or not result.get("has_schedule"):
        return False, "The scheduler did not return a complete monthly schedule."
    weeks = result.get("weeks")
    if not isinstance(weeks, list) or len(weeks) != 4:
        return False, "A monthly plan must contain exactly four weeks."
    signatures: list[list[str]] = []
    evaluations: list[dict[str, Any]] = []
    try:
        for week_index, week in enumerate(weeks, start=1):
            if not isinstance(week, dict) or int(week.get("week_number", -1)) != week_index:
                return False, "Monthly week records must be numbered from 1 through 4."
            signature = week.get("signature")
            chromosome = week.get("chromosome")
            if not isinstance(signature, (list, tuple)) or len(signature) != config.NUM_SLOTS:
                return False, "A week does not contain exactly 21 ordered meal IDs."
            if not isinstance(chromosome, (list, tuple)) or len(chromosome) != config.NUM_SLOTS:
                return False, "A week does not contain exactly 21 chromosome decisions."
            evaluated = evaluation.evaluate_menu([int(gene) for gene in chromosome], dataset)
            if not evaluated["is_feasible"]:
                return False, f"Week {week.get('week_number', '?')} fails the configured hard constraints."
            if week.get("is_feasible") is not True:
                return False, f"Week {week.get('week_number', '?')} does not declare its evaluated feasibility."
            if list(evaluated["weekly_signature"]) != [str(meal_id) for meal_id in signature]:
                return False, "A weekly signature does not match its chromosome and dataset mapping."
            objectives = np.asarray(week.get("objectives", []), dtype=float)
            if objectives.shape != (3,) or not np.isfinite(objectives).all():
                return False, "A weekly objective vector must contain three finite values."
            if not np.allclose(objectives, np.asarray(evaluated["objectives"], dtype=float)):
                return False, "A weekly objective vector does not match the existing evaluator."
            signatures.append([str(meal_id) for meal_id in signature])
            evaluations.append(evaluated)
    except (AttributeError, TypeError, ValueError, IndexError, KeyError, OverflowError):
        return False, "A weekly result contains invalid chromosome or meal-ID data."
    if len({tuple(signature) for signature in signatures}) != 4:
        return False, "The monthly schedule contains duplicate weekly signatures."
    settings = result.get("settings")
    settings = settings if isinstance(settings, dict) else {}
    try:
        threshold = int(settings.get("min_differing_slots", config.MIN_DIFFERING_SLOTS))
    except (TypeError, ValueError, OverflowError):
        return False, "The saved monthly diversity threshold is invalid."
    if not 0 <= threshold <= config.NUM_SLOTS:
        return False, "The saved monthly diversity threshold is invalid."
    actual_pairs = []
    for (week_a, signature_a), (week_b, signature_b) in combinations(enumerate(signatures, start=1), 2):
        difference = weekly_slot_difference(signature_a, signature_b)
        if difference < threshold:
            return False, f"At least one week pair is below the {threshold}-slot diversity threshold."
        actual_pairs.append((week_a, week_b, difference))
    reported_pairs = result.get("pairwise_differences")
    if not isinstance(reported_pairs, list) or len(reported_pairs) != len(actual_pairs):
        return False, "The monthly result is missing its six pairwise diversity comparisons."
    reported_map = {(item.get("week_a"), item.get("week_b")): item.get("different_slots") for item in reported_pairs if isinstance(item, dict)}
    if any(reported_map.get((week_a, week_b)) != difference for week_a, week_b, difference in actual_pairs):
        return False, "Reported pairwise diversity values do not match the weekly signatures."
    summary = result.get("monthly_summary")
    if not isinstance(summary, dict):
        return False, "The monthly summary is missing."
    daily_costs = [cost for item in evaluations for cost in item["daily_totals"]["daily_cost"]]
    daily_calories = [value for item in evaluations for value in item["daily_totals"]["daily_calories"]]
    daily_protein = [value for item in evaluations for value in item["daily_totals"]["daily_protein"]]
    frequencies = Counter(meal_id for signature in signatures for meal_id in signature)
    expected_summary = {
        "monthly_total_cost": float(sum(daily_costs)),
        "average_daily_cost": float(np.mean(daily_costs)),
        "average_daily_calories": float(np.mean(daily_calories)),
        "average_daily_protein": float(np.mean(daily_protein)),
        "distinct_meal_count": len(frequencies),
        "maximum_meal_frequency": max(frequencies.values(), default=0),
        "repeated_meal_occurrences": sum(count - 1 for count in frequencies.values() if count > 1),
    }
    try:
        for key, expected in expected_summary.items():
            actual = summary.get(key)
            if actual is None or not np.isclose(float(actual), float(expected)):
                return False, f"Monthly summary field '{key}' does not match the evaluator and schedule."
        if {str(key): int(value) for key, value in summary.get("meal_frequencies", {}).items()} != dict(sorted(frequencies.items())):
            return False, "Monthly meal frequencies do not match the weekly signatures."
    except (AttributeError, TypeError, ValueError, OverflowError):
        return False, "The monthly summary contains invalid values."
    return True, "Monthly schedule passed weekly feasibility, signature, objective, and diversity validation."


def monthly_csv(result: dict[str, Any], dataset: pd.DataFrame) -> str:
    """Serialize the currently displayed monthly plan as one row per meal."""
    output = io.StringIO()
    fields = ["week", "day", "meal_slot", "meal_id", "meal_name", "cuisine", "cost_inr", "calories_kcal", "protein_g", "objective_cost", "objective_nutrition_deviation", "objective_dissatisfaction"]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for week in result.get("weeks", []):
        objectives = list(week.get("objectives", []))
        for row in weekly_meal_rows(week, dataset):
            writer.writerow({
                "week": week.get("week_number"), "day": row["day"], "meal_slot": row["slot"],
                "meal_id": row["meal_id"], "meal_name": row["meal_name"], "cuisine": row["cuisine"],
                "cost_inr": row["cost"], "calories_kcal": row["calories"], "protein_g": row["protein"],
                "objective_cost": objectives[0] if len(objectives) > 0 else "",
                "objective_nutrition_deviation": objectives[1] if len(objectives) > 1 else "",
                "objective_dissatisfaction": objectives[2] if len(objectives) > 2 else "",
            })
    return output.getvalue()


def monthly_json(result: dict[str, Any]) -> str:
    """Serialize the selected monthly schedule using the backend's adapter."""
    return json.dumps(serialize_monthly_result(result), indent=2, ensure_ascii=False)


def load_benchmark_artifacts(results_dir: Path | str = REPO_ROOT / "results") -> dict[str, Any] | None:
    """Load the newest complete aggregate/raw experiment pair, if present."""
    directory = Path(results_dir)
    candidates = sorted(
        directory.glob("benchmark_run_*_summary.csv"),
        key=lambda path: int(path.stem.split("_")[2]),
        reverse=True,
    )
    for summary_path in candidates:
        prefix = summary_path.name.removesuffix("_summary.csv")
        raw_path = directory / f"{prefix}.json"
        if not raw_path.is_file():
            continue
        try:
            summary = pd.read_csv(summary_path)
            raw = json.loads(raw_path.read_text(encoding="utf-8"))
            if "runs" not in raw or not isinstance(raw["runs"], list):
                continue
            return {"summary": summary, "raw": raw, "summary_path": summary_path, "raw_path": raw_path}
        except (OSError, ValueError, pd.errors.ParserError):
            continue
    return None
