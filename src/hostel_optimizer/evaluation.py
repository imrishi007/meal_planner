"""Weekly menu evaluation engine.

Evaluates a candidate weekly menu (21 meal selections) and returns
structured results containing objectives, daily totals, constraint
violations, feasibility status, and a stable weekly signature.

The three objectives (all to be minimized) are:

1. **Average daily cost** (f1): sum of costs of all 21 meals / 7
2. **Nutrition deviation** (f2): average over 7 days of
   (|daily_calories - target| / target + |daily_protein - target| / target)
3. **Dissatisfaction** (f3): average (5 - rating) across 21 meals +
   configurable repetition penalty

Hard constraints are checked in ``constraints.check_constraints``.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from . import config
from . import constraints
from . import data_loader


# ---------------------------------------------------------------------------
# Chromosome / schedule helpers
# ---------------------------------------------------------------------------

SLOT_ORDER: list[str] = config.SLOT_ORDER


def chromosome_to_schedule(chromosome: list[int], df: pd.DataFrame | None = None) -> dict[str, any]:
    """Convert a 21-element chromosome into a seven-day schedule dict.

    Parameters
    ----------
    chromosome :
        List of 21 integer indices mapping to dataset rows.
    df :
        DataFrame from ``load_dataset()``.  If ``None``, loaded automatically.

    Returns
    -------
    dict with keys:
        - "monday": {breakfast: row, lunch: row, dinner: row, ...}
        - "tuesday": ...
        - ... "sunday": ...
        - "all_slots": list of 21 row dicts in slot order
    """
    if df is None:
        df = data_loader.load_dataset()

    if len(chromosome) != config.NUM_SLOTS:
        msg = f"Chromosome must have {config.NUM_SLOTS} elements, got {len(chromosome)}"
        raise ValueError(msg)

    schedule: dict[str, dict] = {}
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    all_slots: list[dict] = []

    for day_idx, day_name in enumerate(day_names):
        slot_indices = [day_idx * 3, day_idx * 3 + 1, day_idx * 3 + 2]
        schedule[day_name] = {}
        for slot_offset, slot_name in zip(
            slot_indices, ["breakfast", "lunch", "dinner"]
        ):
            meal_idx = chromosome[slot_offset]
            meal_row = df.iloc[meal_idx]
            slot_data = {
                "meal_id": meal_row["meal_id"],
                "meal_name": meal_row["meal_name"],
                "meal_type": meal_row["meal_type"],
                "cost": meal_row["cost_per_serving_inr"],
                "calories": meal_row["calories_kcal"],
                "protein": meal_row["protein_g"],
                "carbs": meal_row["carbs_g"],
                "fat": meal_row["fat_g"],
                "rating": meal_row["student_rating"],
                "slot": f"{day_name} {slot_name}",
                "slot_index": slot_offset,
            }
            schedule[day_name][slot_name] = slot_data
            all_slots.append(slot_data)

    schedule["all_slots"] = all_slots
    return schedule


def schedule_to_21_id_signature(schedule: dict[str, any]) -> list[str]:
    """Convert a schedule dict into a stable ordered sequence of 21 meal IDs.

    The signature is the meal_id values in the documented slot order:
    Monday breakfast, Monday lunch, Monday dinner, Tuesday breakfast, ...
    Sunday dinner.

    Parameters
    ----------
    schedule :
        Schedule dict as returned by ``chromosome_to_schedule``.

    Returns
    -------
    list of 21 meal_id strings
    """
    all_slots = schedule.get("all_slots", [])
    if len(all_slots) != config.NUM_SLOTS:
        msg = f"Expected {config.NUM_SLOTS} slots, got {len(all_slots)}"
        raise ValueError(msg)
    return [slot["meal_id"] for slot in all_slots]


def validate_chromosome(chromosome: list[int], df: pd.DataFrame | None = None) -> dict[str, any]:
    """Validate a chromosome's basic properties.

    Checks:
    - Length is exactly 21
    - All indices are within [0, len(df)-1]
    - Returns a dict with 'valid' flag and any error messages.
    """
    if df is None:
        df = data_loader.load_dataset()

    issues: list[str] = []

    if len(chromosome) != config.NUM_SLOTS:
        issues.append(f"Chromosome length {len(chromosome)} != {config.NUM_SLOTS}")

    n_meals = len(df)
    for i, idx in enumerate(chromosome):
        if idx < 0 or idx >= n_meals:
            issues.append(f"Index {idx} at position {i} out of range [0, {n_meals - 1}]")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "num_meals_in_dataset": n_meals,
    }


# ---------------------------------------------------------------------------
# Objective calculations
# ---------------------------------------------------------------------------

def _compute_daily_totals(chromosome: list[int], df: pd.DataFrame) -> dict[str, list[float]]:
    """Compute daily totals for cost, calories, protein, carbs, fat.

    Returns a dict mapping objective names to lists of 7 values (one per day).
    """
    daily_costs: list[float] = []
    daily_calories: list[float] = []
    daily_protein: list[float] = []
    daily_carbs: list[float] = []
    daily_fat: list[float] = []

    for day in range(7):
        start = day * 3
        end = start + 3
        day_cost = sum(df.iloc[chromosome[i]]["cost_per_serving_inr"] for i in range(start, end))
        day_cal = sum(df.iloc[chromosome[i]]["calories_kcal"] for i in range(start, end))
        day_prot = sum(df.iloc[chromosome[i]]["protein_g"] for i in range(start, end))
        day_carb = sum(df.iloc[chromosome[i]]["carbs_g"] for i in range(start, end))
        day_fat = sum(df.iloc[chromosome[i]]["fat_g"] for i in range(start, end))

        daily_costs.append(day_cost)
        daily_calories.append(day_cal)
        daily_protein.append(day_prot)
        daily_carbs.append(day_carb)
        daily_fat.append(day_fat)

    return {
        "daily_cost": daily_costs,
        "daily_calories": daily_calories,
        "daily_protein": daily_protein,
        "daily_carbs": daily_carbs,
        "daily_fat": daily_fat,
    }


def _compute_objective1_daily_cost(chromosome: list[int], df: pd.DataFrame) -> tuple[float, dict[str, list[float]]]:
    """Objective 1: Minimize average daily cost per student.

    f1 = sum of the costs of all 21 selected meals / 7.

    Returns (f1_value, daily_totals_dict).
    """
    daily_totals = _compute_daily_totals(chromosome, df)
    total_cost = sum(daily_totals["daily_cost"])
    avg_daily_cost = total_cost / config.DAYS  # 7
    return avg_daily_cost, daily_totals


def _compute_objective2_nutrition_deviation(
    chromosome: list[int],
    df: pd.DataFrame,
    calorie_target: float | None = None,
    protein_target: float | None = None,
) -> tuple[float, dict[str, list[float]]]:
    """Objective 2: Minimize nutrition deviation.

    For each day, compute:
        daily_deviation = abs(daily_calories - target_calories) / target_calories
                        + abs(daily_protein - target_protein) / target_protein

    Then average the seven daily deviations.

    Keyword arguments override the module-level defaults; useful for testing.
    """
    cal_target = calorie_target or config.DEFAULT_CALORIE_TARGET
    prot_target = protein_target or config.DEFAULT_PROTEIN_TARGET

    daily_totals = _compute_daily_totals(chromosome, df)

    deviations: list[float] = []
    for day in range(7):
        cal_deviation = abs(daily_totals["daily_calories"][day] - cal_target) / cal_target
        prot_deviation = abs(daily_totals["daily_protein"][day] - prot_target) / prot_target
        daily_dev = cal_deviation + prot_deviation
        deviations.append(daily_dev)

    avg_deviation = sum(deviations) / config.DAYS
    return avg_deviation, daily_totals


def _compute_objective3_dissatisfaction(
    chromosome: list[int],
    df: pd.DataFrame,
    repetition_penalty: float | None = None,
) -> tuple[float, int]:
    """Objective 3: Minimize student dissatisfaction.

    meal_dissatisfaction = 5 - student_rating  (rating in [1, 5])
    Average dissatisfaction across the 21 selected meals.

    Configurable repetition penalty: for any meal ID that appears within
    the configured three-day window, add a penalty proportional to the
    number of repetitions.  The penalty is added per violating pair.

    Parameters
    ----------
    chromosome : list[int]
        21 meal indices.
    df : pd.DataFrame
        The dataset.
    repetition_penalty : float or None
        If provided, added per repetition pair within the window.
        If None, uses ``config.REPETITION_PENALTY_PER_REP`` or 0.0
        (no penalty) depending on what is set.

    Returns
    -------
    (f3_value, repetition_penalty_count)
        f3 is the average dissatisfaction plus any configured penalty.
        repetition_penalty_count is the number of violating pairs.
    """
    rp = repetition_penalty if repetition_penalty is not None else (
        getattr(config, "REPETITION_PENALTY_PER_REP", 0.0) or 0.0
    )

    # Average dissatisfaction
    total_dissatisfaction = 0.0
    for slot_idx in range(config.NUM_SLOTS):
        meal_row = df.iloc[chromosome[slot_idx]]
        total_dissatisfaction += (5 - meal_row["student_rating"])

    avg_dissatisfaction = total_dissatisfaction / config.NUM_SLOTS

    # Repetition penalty
    # Same interpretation as in constraints: a meal may not appear within
    # the three-day window.  Each violating pair adds the penalty.
    window = config.REPETITION_WINDOW_DAYS

    meal_ids_chromosome = [df.iloc[chromosome[i]]["meal_id"] for i in range(config.NUM_SLOTS)]
    slot_to_day = [i // 3 for i in range(config.NUM_SLOTS)]

    meal_to_slots: dict[str, list[int]] = {}
    for slot_idx, mid in enumerate(meal_ids_chromosome):
        if mid not in meal_to_slots:
            meal_to_slots[mid] = []
        meal_to_slots[mid].append(slot_idx)

    # Count violating pairs and compute penalty total
    violating_pair_count = 0
    repetition_penalty_total = 0.0
    for meal_id, slots in meal_to_slots.items():
        if len(slots) < 2:
            continue
        for i in range(len(slots)):
            for j in range(i + 1, len(slots)):
                day_i = slot_to_day[slots[i]]
                day_j = slot_to_day[slots[j]]
                diff = abs(day_i - day_j)
                if 0 < diff < window:
                    violating_pair_count += 1
                    repetition_penalty_total += rp

    f3 = avg_dissatisfaction + repetition_penalty_total
    return f3, violating_pair_count


# ---------------------------------------------------------------------------
# Main evaluation function
# ---------------------------------------------------------------------------

def evaluate_menu(
    chromosome: list[int],
    dataset: pd.DataFrame | None = None,
    config_obj: config.Config | None = None,
) -> dict[str, any]:
    """Evaluate one candidate weekly menu and return a structured result.

    Parameters
    ----------
    chromosome :
        List of exactly 21 integer indices mapping to dataset rows.
    dataset :
        DataFrame from ``load_dataset()``.  If ``None``, loaded automatically.
    config_obj :
        Configuration object.  If ``None``, ``config`` module defaults are
        used.

    Returns
    -------
    result : dict with the following keys:
        - "objectives": tuple of 3 floats (f1, f2, f3) in the required order
        - "daily_totals": dict with daily cost, calories, protein, carbs, fat
        - "constraint_violations": list of ``ConstraintViolation`` named tuples
        - "is_feasible": bool  -- True if no hard constraints are violated
        - "weekly_signature": list of 21 meal_id strings in slot order

    Raises
    ------
    ValueError
        If the chromosome is malformed (wrong length, unknown IDs, etc.).
    RuntimeError
        If the dataset structure is unexpected.
    """
    # Use provided config or module defaults
    cfg = config_obj or config

    # Load dataset if not provided
    if dataset is None:
        dataset = data_loader.load_dataset()
    else:
        if not isinstance(dataset, pd.DataFrame):
            msg = "Dataset must be a pandas DataFrame."
            raise ValueError(msg)

    n_meals = len(dataset)

    # --- Validate chromosome ---
    validation = validate_chromosome(chromosome, dataset)
    if not validation["valid"]:
        msg = "; ".join(validation["issues"])
        raise ValueError(f"Malformed chromosome: {msg}")

    # --- Check for unknown meal IDs (indices out of range already checked,
  # but also verify that the indices map to valid records) ---
    # (Index range check already done in validate_chromosome)

    # --- Compute daily totals ---
    daily_totals = _compute_daily_totals(chromosome, dataset)

    # --- Compute objectives ---
    f1, daily_cost_totals = _compute_objective1_daily_cost(chromosome, dataset)
    f2, nutrition_daily_totals = _compute_objective2_nutrition_deviation(chromosome, dataset)
    f3, rep_penalty_count = _compute_objective3_dissatisfaction(chromosome, dataset)

    objectives = (f1, f2, f3)

    # --- Constraint violations ---
    constraint_violations, is_feasible = constraints.check_constraints(
        chromosome, dataset
    )

    # --- Weekly signature ---
    schedule = chromosome_to_schedule(chromosome, dataset)
    weekly_signature = schedule_to_21_id_signature(schedule)

    # --- Assemble result ---
    result: dict[str, any] = {
        "objectives": objectives,
        "daily_totals": {
            "daily_cost": daily_totals["daily_cost"],
            "daily_calories": daily_totals["daily_calories"],
            "daily_protein": daily_totals["daily_protein"],
            "daily_carbs": daily_totals["daily_carbs"],
            "daily_fat": daily_totals["daily_fat"],
        },
        "constraint_violations": constraint_violations,
        "is_feasible": is_feasible,
        "weekly_signature": weekly_signature,
        "repetition_penalty_count": rep_penalty_count,
    }

    return result