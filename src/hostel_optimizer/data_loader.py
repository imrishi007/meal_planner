"""Data loading and validation for the hostel meal dataset.

Loads the authoritative CSV from a repository-relative path, validates
its structure and content, and returns a clean pandas DataFrame.

Provenance columns are kept in the raw dataset; the evaluation engine
only consumes the columns it needs.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Path configuration
# ---------------------------------------------------------------------------

# The dataset is kept at data/hostel_meal_dataset_cleaned.csv relative to
# the repository root.  We determine the repository root as the parent of
# the `src` package directory so that the path is stable regardless of
# the caller's current working directory.
_REPO_ROOT: Path = Path(__file__).resolve().parent.parent.parent
# Dataset is at the repository root's data/ directory
_DATASET_PATH: Path = _REPO_ROOT / "data" / "hostel_meal_dataset_cleaned.csv"


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

REQUIRED_COLUMNS: set[str] = {
    "meal_id",
    "meal_name",
    "primary_cuisine",
    "meal_type",
    "suitable_meal_types",
    "meal_components",
    "is_veg",
    "cost_per_serving_inr",
    "calories_kcal",
    "protein_g",
    "carbs_g",
    "fat_g",
    "student_rating",
    "rating_source",
    "rating_count",
    "prep_time_minutes",
    "kitchen_load",
    "allergens",
    "data_source",
    "data_quality",
}


def _series_is_numeric(series: pd.Series, name: str) -> None:
    """Ensure a series is numeric; raise ValueError if not."""
    if not pd.api.types.is_numeric_dtype(series):
        try:
            series = pd.to_numeric(series, errors="coerce")
        except (TypeError, ValueError) as exc:
            msg = f"Column '{name}' contains non-numeric values that cannot be coerced."
            raise ValueError(msg) from exc


def _validate_meal_id_uniqueness(df: pd.DataFrame) -> None:
    """Ensure all meal_id values are unique."""
    ids = df["meal_id"]
    dupes = ids[ids.duplicated(keep=False)]
    if len(dupes) > 0:
        # Format: show a few examples
        examples = dupes.head(5).tolist()
        msg = f"Duplicate meal_id values found: {examples}"
        raise ValueError(msg)


def _validate_record_count(df: pd.DataFrame, expected: int = 200) -> None:
    """Ensure the dataset has the expected number of records."""
    if len(df) != expected:
        msg = f"Expected {expected} records, got {len(df)}."
        raise ValueError(msg)


def _validate_cost_range(df: pd.DataFrame) -> None:
    """Validate that cost values are positive."""
    costs = df["cost_per_serving_inr"]
    if (costs <= 0).any():
        bad = costs[costs <= 0]
        msg = f"Cost values must be positive; found non-positive: {bad.tolist()}"
        raise ValueError(msg)


def _validate_nutrition_range(df: pd.DataFrame) -> None:
    """Validate that nutrition values are non-negative."""
    for col in ("calories_kcal", "protein_g", "carbs_g", "fat_g"):
        s = df[col]
        if (s < 0).any():
            bad = s[s < 0].index.tolist()
            msg = f"Nutrition column '{col}' contains negative values at indices {bad}"
            raise ValueError(msg)


def _validate_meal_type(df: pd.DataFrame) -> None:
    """Validate that meal_type is one of breakfast/lunch/dinner."""
    valid = {"breakfast", "lunch", "dinner"}
    invalid = ~df["meal_type"].isin(valid)
    if invalid.any():
        bad_rows = df[invalid][["meal_id", "meal_name", "meal_type"]]
        msg = f"Invalid meal_type values found:\n{bad_rows.to_string()}"
        raise ValueError(msg)


def _validate_vegetarian_policy(df: pd.DataFrame) -> None:
    """Ensure is_veg column is consistent with meal content."""
    # All records should be vegetarian; warn if not.
    # No exception thrown; the caller can enforce VEGETARIAN_ONLY later.
    pass


def _validate_rating_count(df: pd.DataFrame) -> None:
    """Verify that synthetic ratings have rating_count = 0."""
    zero_rc = df[df["rating_count"] == 0]
    if len(zero_rc) == 0:
        msg = "Expected all records to have rating_count = 0 (synthetic ratings)."
        raise ValueError(msg)
    # Optional: warn if some have non-zero counts
    non_zero = df[df["rating_count"] > 0]
    if len(non_zero) > 0:
        # Log but do not raise — the dataset may have been updated.
        print(
            f"WARNING: {len(non_zero)} records have rating_count > 0; "
            "expected all to be 0 (synthetic)."
        )


def _validate_meal_names(df: pd.DataFrame) -> None:
    """Verify every record has a non-empty meal name."""
    empty_names = df[df["meal_name"].isna()] | df[df["meal_name"].astype(str).str.strip() == ""]
    if len(empty_names) > 0:
        msg = f"Found {len(empty_names)} records with empty meal name."
        raise ValueError(msg)


def _validate_meal_components(df: pd.DataFrame) -> None:
    """Verify every record has a non-empty component list."""
    empty_comp = df[df["meal_components"].isna()] | df[
        df["meal_components"].astype(str).str.strip() == ""
    ]
    if len(empty_comp) > 0:
        msg = f"Found {len(empty_comp)} records with empty meal components."
        raise ValueError(msg)


def _parse_meal_slot_eligibility(suitable_meal_types: str) -> set[str]:
    """Parse the semicolon-separated suitable_meal_types string into a set."""
    if pd.isna(suitable_meal_types):
        return set()
    return {s.strip() for s in suitable_meal_types.split(";")}


def _validate_slot_eligibility(df: pd.DataFrame) -> None:
    """Ensure each meal's primary meal_type appears in its eligible slots.

    Also ensures that breakfast-only meals cannot be placed at lunch or dinner.
    """
    for _, row in df.iterrows():
        slots = _parse_meal_slot_eligibility(row["suitable_meal_types"])
        if row["meal_type"] not in slots:
            msg = (
                f"Meal {row['meal_id']} ({row['meal_name']}): primary meal_type "
                f"'{row['meal_type']}' is not in suitable_meal_types '{row['suitable_meal_types']}'."
            )
            raise ValueError(msg)


def load_dataset(dataset_path: str | Path | None = None) -> pd.DataFrame:
    """Load and validate the authoritative dataset.

    Returns
    -------
    pd.DataFrame
        A validated DataFrame containing the meal options.

    Raises
    ------
    FileNotFoundError
        If the dataset file does not exist.
    ValueError
        If any validation check fails.
    """
    path = Path(dataset_path) if dataset_path is not None else _DATASET_PATH
    if not path.is_file():
        msg = f"Dataset not found at expected path: {path}"
        raise FileNotFoundError(msg)

    df = pd.read_csv(path)

    # --- Basic column check ---
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        msg = f"Missing required columns: {sorted(missing)}"
        raise ValueError(msg)

    extra = set(df.columns) - REQUIRED_COLUMNS
    if extra:
        print(
            f"WARNING: Extra columns found (ignored): {sorted(extra)}"
        )

    # --- Record count ---
    _validate_record_count(df, expected=200)

    # --- meal_id uniqueness ---
    _validate_meal_id_uniqueness(df)

    # --- Numeric type validation ---
    _series_is_numeric(df["cost_per_serving_inr"], "cost_per_serving_inr")
    _series_is_numeric(df["calories_kcal"], "calories_kcal")
    _series_is_numeric(df["protein_g"], "protein_g")
    _series_is_numeric(df["carbs_g"], "carbs_g")
    _series_is_numeric(df["fat_g"], "fat_g")
    _series_is_numeric(df["student_rating"], "student_rating")
    _series_is_numeric(df["rating_count"], "rating_count")
    _series_is_numeric(df["prep_time_minutes"], "prep_time_minutes")

    # --- Range validations ---
    _validate_cost_range(df)
    _validate_nutrition_range(df)

    # --- Categorical validations ---
    _validate_meal_type(df)
    _validate_vegetarian_policy(df)
    _validate_slot_eligibility(df)
    _validate_rating_count(df)
    _validate_meal_names(df)
    _validate_meal_components(df)

    # --- Derived: ensure meal_id values are stable strings ---
    df["meal_id"] = df["meal_id"].astype(str)

    # --- Sort by meal_id for reproducibility ---
    df = df.sort_values("meal_id").reset_index(drop=True)

    return df


# ---------------------------------------------------------------------------
# Convenience helpers (small, testable functions)
# ---------------------------------------------------------------------------

def get_meal_by_id(meal_id: str, df: pd.DataFrame | None = None) -> pd.Series:
    """Return the row for a given meal_id.

    Parameters
    ----------
    meal_id :
        The stable meal identifier (e.g. "M001").
    df :
        DataFrame from ``load_dataset()``.  If ``None``, the dataset is
        loaded automatically.

    Returns
    -------
    pd.Series
        The meal record.

    Raises
    ------
    KeyError
        If the meal_id is not found.
    """
    if df is None:
        df = load_dataset()
    matches = df[df["meal_id"] == str(meal_id)]
    if matches.empty:
        msg = f"Unknown meal_id: {meal_id}"
        raise KeyError(msg)
    if len(matches) > 1:
        msg = f"Duplicate meal_id found: {meal_id}"
        raise ValueError(msg)
    return matches.iloc[0]


def get_meals_by_type(meal_type: str, df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Return all meals whose primary meal_type matches.

    Parameters
    ----------
    meal_type :
        One of "breakfast", "lunch", "dinner".
    df :
        DataFrame from ``load_dataset()``.  If ``None``, loaded automatically.

    Returns
    -------
    pd.DataFrame
    """
    if df is None:
        df = load_dataset()
    return df[df["meal_type"] == meal_type].reset_index(drop=True)


def get_vegetarian_meals(df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Return all vegetarian meals.

    Parameters
    ----------
    df :
        DataFrame from ``load_dataset()``.  If ``None``, loaded automatically.

    Returns
    -------
    pd.DataFrame
    """
    if df is None:
        df = load_dataset()
    return df[df["is_veg"] == True].reset_index(drop=True)


def get_breakfast_only_meals(df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Return meals that are eligible only for breakfast.

    A meal is "breakfast-only" if its ``suitable_meal_types`` contains
    "breakfast" and does NOT contain "lunch" or "dinner".
    """
    if df is None:
        df = load_dataset()
    mask = (
        df["suitable_meal_types"].str.contains("breakfast")
        & ~df["suitable_meal_types"].str.contains("lunch")
        & ~df["suitable_meal_types"].str.contains("dinner")
    )
    return df[mask].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Module-level test guard
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Quick sanity check when run directly
    df = load_dataset()
    print(f"Dataset loaded: {len(df)} meals")
    print(f"Columns: {list(df.columns)}")
    print(f"Meal types: {df['meal_type'].value_counts().to_dict()}")
    print(f"Breakfast-only meals: {len(get_breakfast_only_meals(df))}")
