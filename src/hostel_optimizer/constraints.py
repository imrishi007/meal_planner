"""Hard constraint checking for the hostel mess menu optimizer.

A weekly menu is a sequence of exactly 21 meal indices (or stable meal IDs)
mapped to dataset rows.  This module checks that all hard constraints are
satisfied and returns structured violation reports.

Convention:  constraint arrays for pymoo use non-positive values for
satisfied inequalities  (g_i <= 0  =>  feasible).  Positive values mean
violation.  This convention is reflected in the return values below.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, NamedTuple, Tuple

import pandas as pd

from . import config

__all__ = [
    "ConstraintViolation",
    "check_constraints",
    "DEFAULT_CONSTRAINTS",
]


# ---------------------------------------------------------------------------
# Violation representation
# ---------------------------------------------------------------------------

class ConstraintViolation(NamedTuple):
    """A single hard-constraint violation."""

    name: str
    description: str
    observed: float | int | str | None
    limit: float | int | str | None
    severity: str  # "error" or "warning"
    day: int | None = None  # 0-based slot index within the 21-slot chromosome
    meal_id: str | None = None


# ---------------------------------------------------------------------------
# Default constraint enablement
# ---------------------------------------------------------------------------

DEFAULT_CONSTRAINTS: dict[str, bool] = {
    "exactly_21_choices": True,
    "valid_meal_indices": True,
    "slot_eligibility": True,
    "daily_calorie_bounds": True,
    "daily_cost_cap": True,
    "vegetarian_only": config.VEGETARIAN_ONLY,
    "no_repetition_within_window": True,
    "kitchen_capacity": False,  # disabled by default; see docs
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _validate_chromosome_length(chromosome: List[int], n_meals: int) -> List[ConstraintViolation]:
    """Check that the chromosome has exactly 21 choices in valid index range."""
    violations: list[ConstraintViolation] = []
    n_choices = len(chromosome)

    if n_choices != config.NUM_SLOTS:
        violations.append(
            ConstraintViolation(
                name="exactly_21_choices",
                description=f"Expected {config.NUM_SLOTS} choices, got {n_choices}",
                observed=n_choices,
                limit=config.NUM_SLOTS,
                severity="error",
            )
        )
    else:
        # Check index bounds
        for idx in chromosome:
            if idx < 0 or idx >= n_meals:
                violations.append(
                    ConstraintViolation(
                        name="valid_meal_indices",
                        description=f"Meal index {idx} out of range [0, {n_meals - 1}]",
                        observed=idx,
                        limit=f"[0, {n_meals - 1}]",
                        severity="error",
                        day=chromosome.index(idx) if idx in chromosome else None,
                    )
                )

    return violations


def _validate_slot_eligibility(
    chromosome: List[int],
    df: pd.DataFrame,
    n_meals: int,
) -> list[ConstraintViolation]:
    """Check that meals are placed in eligible slots.

    A meal's ``suitable_meal_types`` determines which slots it can occupy.
    Breakfast-only meals (suitable_meal_types contains "breakfast" but
    neither "lunch" nor "dinner") cannot be placed at lunch or dinner slots.

    Slot order: 0=Monday breakfast, 1=Monday lunch, 2=Monday dinner,
    2=Tuesday breakfast, ... 20=Sunday dinner.
    """
    violations: list[ConstraintViolation] = []

    for slot_idx, meal_idx in enumerate(chromosome):
        meal_row = df.iloc[meal_idx]
        meal_id = meal_row["meal_id"]
        suitable = {s.strip() for s in meal_row["suitable_meal_types"].split(";")}

        # Determine the slot's meal type based on position
        # Slots where idx % 3 == 0 are breakfast slots
        # Slots where idx % 3 == 1 are lunch slots
        # Slots where idx % 3 == 2 are dinner slots
        slot_slot_type: str
        if slot_idx % 3 == 0:
            slot_slot_type = "breakfast"
        elif slot_idx % 3 == 1:
            slot_slot_type = "lunch"
        else:
            slot_slot_type = "dinner"

        # If the slot is lunch or dinner, and the meal is breakfast-only,
        # that's a violation
        if slot_slot_type in ("lunch", "dinner") and "lunch" not in suitable and "dinner" not in suitable:
            violations.append(
                ConstraintViolation(
                    name="slot_eligibility",
                    description=f"Breakfast-only meal '{meal_id}' placed at slot {slot_idx} ({slot_slot_type})",
                    observed=slot_slot_type,
                    limit="breakfast-only",
                    severity="error",
                    day=slot_idx // 3,  # day number 0-6
                    meal_id=meal_id,
                )
            )

    return violations


def _validate_daily_calorie_bounds(
    chromosome: List[int],
    df: pd.DataFrame,
    n_meals: int,
) -> list[ConstraintViolation]:
    """Check daily calorie min/max bounds.

    Each day's total calories = sum of 3 meals' calories.
    Violations are reported per day (0 = Monday, ..., 6 = Sunday).
    """
    violations: list[ConstraintViolation] = []

    for day in range(7):
        start = day * 3
        end = start + 3
        daily_calories = sum(df.iloc[chromosome[i]]["calories_kcal"] for i in range(start, end))

        if daily_calories < config.MIN_CALORIES_PER_DAY:
            violations.append(
                ConstraintViolation(
                    name="daily_calorie_min",
                    description=f"Day {day} total calories {daily_calories:.1f} below minimum {config.MIN_CALORIES_PER_DAY:.1f}",
                    observed=daily_calories,
                    limit=config.MIN_CALORIES_PER_DAY,
                    severity="error",
                    day=day,
                ))
        elif daily_calories > config.MAX_CALORIES_PER_DAY:
            violations.append(
                ConstraintViolation(
                    name="daily_calorie_max",
                    description=f"Day {day} total calories {daily_calories:.1f} exceeds maximum {config.MAX_CALORIES_PER_DAY:.1f}",
                    observed=daily_calories,
                    limit=config.MAX_CALORIES_PER_DAY,
                    severity="error",
                    day=day,
                ))

    return violations


def _validate_daily_cost_cap(
    chromosome: List[int],
    df: pd.DataFrame,
    n_meals: int,
) -> list[ConstraintViolation]:
    """Check daily cost cap.

    Each day's total cost = sum of 3 meals' cost per serving.
    """
    violations: list[ConstraintViolation] = []

    for day in range(7):
        start = day * 3
        end = start + 3
        daily_cost = sum(df.iloc[chromosome[i]]["cost_per_serving_inr"] for i in range(start, end))

        if daily_cost > config.MAX_COST_PER_DAY:
            violations.append(
                ConstraintViolation(
                    name="daily_cost_cap",
                    description=f"Day {day} total cost {daily_cost:.1f} INR exceeds cap {config.MAX_COST_PER_DAY:.1f} INR",
                    observed=daily_cost,
                    limit=config.MAX_COST_PER_DAY,
                    severity="error",
                    day=day,
                ))

    return violations


def _validate_vegetarian_only(
    chromosome: List[int],
    df: pd.DataFrame,
) -> list[ConstraintViolation]:
    """Check that all selected meals are vegetarian when VEGETARIAN_ONLY=True."""
    violations: list[ConstraintViolation] = []

    if not config.VEGETARIAN_ONLY:
        return violations

    for slot_idx, meal_idx in enumerate(chromosome):
        meal_row = df.iloc[meal_idx]
        if not meal_row["is_veg"]:
            violations.append(
                ConstraintViolation(
                    name="vegetarian_only",
                    description=f"Non-vegetarian meal '{meal_row['meal_id']}' placed at slot {slot_idx}",
                    observed=meal_row["meal_id"],
                    limit="vegetarian-only",
                    severity="error",
                    day=slot_idx,
                    meal_id=meal_row["meal_id"],
                ))

    return violations


def _validate_no_repetitionWithin_window(
    chromosome: List[int],
    df: pd.DataFrame,
) -> list[ConstraintViolation]:
    """Check that no meal repeats within the configured three-day window.

    Interpretation: the same meal ID must not appear on any two days
    whose day indices differ by less than REPETITION_WINDOW_DAYS (3).

    Slot 0..20 -> day 0..6 (Monday..Sunday), each day having 3 slots.
    Two slots are on the same day if floor(slot/3) == floor(slot2/3).
    Two slots are on different days if the day indices differ by >= window.

    A repetition violation occurs when the same meal ID appears on two
    days with 0 < |day1 - day2| < REPETITION_WINDOW_DAYS.
    """
    violations: list[ConstraintViolation] = []

    window = config.REPETITION_WINDOW_DAYS

    # Extract meal IDs for each of the 21 slots
    meal_ids_chromosome = [df.iloc[chromosome[i]]["meal_id"] for i in range(config.NUM_SLOTS)]

    # Track which day each slot belongs to
    slot_to_day = [i // 3 for i in range(config.NUM_SLOTS)]  # 0=Mon, ..., 6=Sun

    # For each meal ID, find all slots where it appears
    meal_to_slots: dict[str, list[int]] = {}
    for slot_idx, mid in enumerate(meal_ids_chromosome):
        if mid not in meal_to_slots:
            meal_to_slots[mid] = []
        meal_to_slots[mid].append(slot_idx)

    # Check for repetitions within the window
    for meal_id, slots in meal_to_slots.items():
        if len(slots) < 2:
            continue
        # Check all pairs
        for i in range(len(slots)):
            for j in range(i + 1, len(slots)):
                day_i = slot_to_day[slots[i]]
                day_j = slot_to_day[slots[j]]
                diff = abs(day_i - day_j)
                # Violation if 0 < diff < window (same day diff=0 is also a rep, but within-window covers it)
                if 0 < diff < window:
                    violations.append(
                        ConstraintViolation(
                            name="no_repetition_within_window",
                            description=f"Meal '{meal_id}' appears on days {day_i} and {day_j}, "
                                        f"differing by {diff} days (within {window}-day window)",
                            observed=f"days {day_i},{day_j}",
                            limit=f">= {window} or same day",
                            severity="error",
                            day=slots[i],  # report first occurrence day
                            meal_id=meal_id,
                        ))
                # Also flag same-day repetitions as errors (diff == 0)
                elif diff == 0 and i != j:
                    # Same meal twice on the same day - this is always a violation
                    violations.append(
                        ConstraintViolation(
                            name="no_repetition_within_window",
                            description=f"Meal '{meal_id}' appears twice on the same day (slot {slots[i]} and {slots[j]})",
                            observed="same day",
                            limit="once per day",
                            severity="error",
                            day=slot_to_day[slots[i]],
                            meal_id=meal_id,
                        ))

    return violations


# ---------------------------------------------------------------------------
# Main constraint-checking function
# ---------------------------------------------------------------------------

def check_constraints(
    chromosome: List[int],
    df: pd.DataFrame | None = None,
    constraints: dict[str, bool] | None = None,
) -> Tuple[list[ConstraintViolation], bool]:
    """Validate a weekly menu chromosome against all hard constraints.

    Parameters
    ----------
    chromosome :
        List of exactly 21 integer indices mapping to rows in ``df``.
    df :
        DataFrame from ``load_dataset()``.  If ``None``, loaded automatically.
    constraints :
        Dictionary mapping constraint names to enabled/disabled flags.
        If ``None``, ``DEFAULT_CONSTRAINTS`` is used.

    Returns
    -------
    violations : list[ConstraintViolation]
        All detected constraint violations.
    is_feasible : bool
        True if no hard constraints are violated (empty violations list).
    """
    if df is None:
        df = load_dataset()

    n_meals = len(df)
    violations: list[ConstraintViolation] = []

    if constraints is None:
        constraints = dict(DEFAULT_CONSTRAINTS)

    # 1. Chromosome length check
    length_violations = _validate_chromosome_length(chromosome, n_meals)
    violations.extend(length_violations)

    # If length is wrong, we can't meaningfully check other constraints
    if any(v.name == "exactly_21_choices" for v in length_violations):
        # Chromosome length is not 21; skip other checks that require 21 choices
        return violations, False

    # 2. Slot eligibility (breakfast-only meals at lunch/dinner)
    if constraints.get("slot_eligibility", True):
        slot_violations = _validate_slot_eligibility(chromosome, df, n_meals)
        violations.extend(slot_violations)

    # 3. Daily calorie bounds
    if constraints.get("daily_calorie_bounds", True):
        calorie_violations = _validate_daily_calorie_bounds(chromosome, df, n_meals)
        violations.extend(calorie_violations)

    # 4. Daily cost cap
    if constraints.get("daily_cost_cap", True):
        cost_violations = _validate_daily_cost_cap(chromosome, df, n_meals)
        violations.extend(cost_violations)

    # 5. Vegetarian-only policy
    if constraints.get("vegetarian_only", True):
        veg_violations = _validate_vegetarian_only(chromosome, df)
        violations.extend(veg_violations)

    # 6. No repetition within window
    if constraints.get("no_repetitionWithin_window", True):
        rep_violations = _validate_no_repetitionWithin_window(chromosome, df)
        violations.extend(rep_violations)

    # 7. Kitchen capacity (disabled by default; see module docstring)
    if constraints.get("kitchen_capacity", False):
        # TODO: implement if semantics become clear
        pass

    # Determine feasibility: no errors (severity="error") violations
    has_errors = any(v.severity == "error" for v in violations)
    is_feasible = not has_errors

    return violations, is_feasible