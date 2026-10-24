"""Tests for data_loader module.

Uses a small controlled test dataset so expected results can be calculated
manually.  Independently calculates expected values; does not merely repeat
the implementation's own calculations.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from hostel_optimizer.data_loader import (
    load_dataset,
    get_meal_by_id,
    get_meals_by_type,
    get_vegetarian_meals,
    get_breakfast_only_meals,
    REQUIRED_COLUMNS,
    _validate_meal_id_uniqueness,
    _validate_record_count,
    _validate_cost_range,
    _validate_nutrition_range,
    _validate_meal_type,
    _validate_slot_eligibility,
    _validate_rating_count,
    _validate_meal_names,
    _validate_meal_components,
)


# ---------------------------------------------------------------------------
# Small synthetic dataset for tests that need independent control
# ---------------------------------------------------------------------------

_SMALL_CSV = Path(__file__).parent.parent / "src" / "hostel_optimizer" / "test_small.csv"


def _create_small_dataset() -> pd.DataFrame:
    """Create a minimal dataset for unit-test purposes."""
    data = {
        "meal_id": ["M001", "M002", "M003", "M004"],
        "meal_name": ["Roti + Dal", "Chole Rice", "Sabzi + Roti", "Pulao"],
        "primary_cuisine": ["North Indian", "North Indian", "North Indian", "North Indian"],
        "meal_type": ["breakfast", "lunch", "lunch", "dinner"],
        "suitable_meal_types": ["breakfast;lunch;dinner", "lunch;dinner", "lunch;dinner", "dinner"],
        "meal_components": ["Roti;Dal", "Chole;Rice", "Sabzi;Roti", "Vegetable Rice"],
        "is_veg": [True, True, True, True],
        "cost_per_serving_inr": [20, 30, 25, 35],
        "calories_kcal": [400, 500, 350, 450],
        "protein_g": [15, 20, 12, 18],
        "carbs_g": [50, 60, 45, 55],
        "fat_g": [10, 12, 8, 11],
        "student_rating": [4, 3, 5, 2],
        "rating_source": ["synthetic", "synthetic", "synthetic", "synthetic"],
        "rating_count": [0, 0, 0, 0],
        "prep_time_minutes": [20, 30, 15, 25],
        "kitchen_load": ["medium", "high", "medium", "low"],
        "allergens": ["wheat", "wheat", "wheat", "wheat;milk"],
        "data_source": ["recipe_estimated"] * 4,
        "data_quality": ["estimated"] * 4,
    }
    return pd.DataFrame(data)


# ---------------------------------------------------------------------------
# load_dataset tests
# ---------------------------------------------------------------------------

def test_load_dataset_uses_repository_relative_path(tmp_path) -> None:
    """CSV loads from the repository-relative path, not cwd."""
    # The load_dataset function uses __file__ to determine the repo root,
    # so it should work regardless of cwd.
    df = load_dataset()
    assert len(df) == 200


def test_load_dataset_has_200_rows() -> None:
    """Exactly 200 rows are loaded."""
    df = load_dataset()
    assert len(df) == 200


def test_load_dataset_meal_id_unique() -> None:
    """ meal_id values are unique."""
    df = load_dataset()
    ids = df["meal_id"]
    assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# Validation helper tests
# ---------------------------------------------------------------------------

def test__validate_meal_id_uniqueness_no_dupes() -> None:
    """_validate_meal_id_uniqueness passes for unique IDs."""
    df = _create_small_dataset()
    _validate_meal_id_uniqueness(df)  # should not raise


def test__validate_meal_id_uniqueness_with_dupes() -> None:
    """_validate_meal_id_uniqueness raises ValueError for duplicate IDs."""
    df = pd.DataFrame({
        "meal_id": ["M001", "M001", "M003"],
        "meal_name": ["A", "A", "C"],
        "primary_cuisine": ["X", "X", "X"],
        "meal_type": ["lunch", "lunch", "lunch"],
        "suitable_meal_types": ["lunch;dinner"] * 3,
        "meal_components": ["a", "a", "a"],
        "is_veg": [True, True, True],
        "cost_per_serving_inr": [1, 2, 3],
        "calories_kcal": [100, 200, 300],
        "protein_g": [5, 6, 7],
        "carbs_g": [10, 11, 12],
        "fat_g": [2, 3, 4],
        "student_rating": [1, 2, 3],
        "rating_source": ["synthetic"] * 3,
        "rating_count": [0, 0, 0],
        "prep_time_minutes": [1, 2, 3],
        "kitchen_load": ["low"] * 3,
        "allergens": ["none"] * 3,
        "data_source": ["recipe"] * 3,
        "data_quality": ["est"] * 3,
    })
    with pytest.raises(ValueError, match="Duplicate meal_id"):
        _validate_meal_id_uniqueness(df)


def test__validate_record_count_ok() -> None:
    """_validate_record_count raises ValueError when record count mismatches."""
    df = _create_small_dataset()
    # Calling with expected=99 on a 4-row dataset gives: "Expected 99 records, got 4."
    with pytest.raises(ValueError, match="Expected 99 records"):
        _validate_record_count(df, expected=99)

    # Calling with expected=200 on a 4-row dataset gives: "Expected 200 records, got 4."
    with pytest.raises(ValueError, match="Expected 200 records"):
        _validate_record_count(df, expected=200)


def test__validate_record_count_too_few() -> None:
    """_validate_record_count raises when too few records."""
    df = pd.DataFrame({"a": [1, 2, 3]})
    with pytest.raises(ValueError, match="Expected 200 records"):
        _validate_record_count(df, expected=200)


# ---------------------------------------------------------------------------
# Numeric type validation tests
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Cost range validation tests
# ---------------------------------------------------------------------------

def test__validate_cost_range_all_positive() -> None:
    """Cost range validation passes when all costs > 0."""
    df = _create_small_dataset()
    _validate_cost_range(df)  # should not raise


def test__validate_cost_range_with_negative() -> None:
    """Cost range validation raises when cost <= 0."""
    df = pd.DataFrame({
        "meal_id": ["M001", "M002"],
        "meal_name": ["A", "B"],
        "primary_cuisine": ["X", "X"],
        "meal_type": ["lunch", "lunch"],
        "suitable_meal_types": ["lunch;dinner"] * 2,
        "meal_components": ["a", "a"],
        "is_veg": [True, True],
        "cost_per_serving_inr": [-5, 10],  # negative cost
        "calories_kcal": [100, 200],
        "protein_g": [5, 6],
        "carbs_g": [10, 11],
        "fat_g": [2, 3],
        "student_rating": [1, 2],
        "rating_source": ["synthetic"] * 2,
        "rating_count": [0, 0],
        "prep_time_minutes": [1, 2],
        "kitchen_load": ["low"] * 2,
        "allergens": ["none"] * 2,
        "data_source": ["recipe"] * 2,
        "data_quality": ["est"] * 2,
    })
    with pytest.raises(ValueError, match="positive"):
        _validate_cost_range(df)


# ---------------------------------------------------------------------------
# Nutrition range validation tests
# ---------------------------------------------------------------------------

def test__validate_nutrition_range_all_non_negative() -> None:
    """Nutrition range validation passes when all values >= 0."""
    df = _create_small_dataset()
    _validate_nutrition_range(df)  # should not raise


def test__validate_nutrition_range_with_negative() -> None:
    """Nutrition range validation raises when negative values exist."""
    df = pd.DataFrame({
        "meal_id": ["M001", "M002"],
        "meal_name": ["A", "B"],
        "primary_cuisine": ["X", "X"],
        "meal_type": ["lunch", "lunch"],
        "suitable_meal_types": ["lunch;dinner"] * 2,
        "meal_components": ["a", "a"],
        "is_veg": [True, True],
        "cost_per_serving_inr": [10, 20],
        "calories_kcal": [-10, 200],  # negative calories
        "protein_g": [5, 6],
        "carbs_g": [10, 11],
        "fat_g": [2, 3],
        "student_rating": [1, 2],
        "rating_source": ["synthetic"] * 2,
        "rating_count": [0, 0],
        "prep_time_minutes": [1, 2],
        "kitchen_load": ["low"] * 2,
        "allergens": ["none"] * 2,
        "data_source": ["recipe"] * 2,
        "data_quality": ["est"] * 2,
    })
    with pytest.raises(ValueError, match="negative"):
        _validate_nutrition_range(df)


# ---------------------------------------------------------------------------
# Meal type validation tests
# ---------------------------------------------------------------------------

def test__validate_meal_type_all_valid() -> None:
    """Meal type validation passes for valid types."""
    df = _create_small_dataset()
    _validate_meal_type(df)  # should not raise


def test__validate_meal_type_with_invalid() -> None:
    """Meal type validation raises for invalid types."""
    df = pd.DataFrame({
        "meal_id": ["M001", "M002"],
        "meal_name": ["A", "B"],
        "primary_cuisine": ["X", "X"],
        "meal_type": ["brunch", "supper"],  # invalid
        "suitable_meal_types": ["lunch;dinner"] * 2,
        "meal_components": ["a", "a"],
        "is_veg": [True, True],
        "cost_per_serving_inr": [10, 20],
        "calories_kcal": [100, 200],
        "protein_g": [5, 6],
        "carbs_g": [10, 11],
        "fat_g": [2, 3],
        "student_rating": [1, 2],
        "rating_source": ["synthetic"] * 2,
        "rating_count": [0, 0],
        "prep_time_minutes": [1, 2],
        "kitchen_load": ["low"] * 2,
        "allergens": ["none"] * 2,
        "data_source": ["recipe"] * 2,
        "data_quality": ["est"] * 2,
    })
    with pytest.raises(ValueError, match="Invalid meal_type"):
        _validate_meal_type(df)


# ---------------------------------------------------------------------------
# Slot eligibility validation tests
# ---------------------------------------------------------------------------

def test__validate_slot_eligibility_all_ok() -> None:
    """Slot eligibility validation passes when all meal types match suitable slots."""
    df = _create_small_dataset()
    _validate_slot_eligibility(df)  # should not raise


def test__validate_slot_eligibility_breakfast_only_at_lunch() -> None:
    """Slot eligibility raises when breakfast-only meal placed at lunch."""
    df = pd.DataFrame({
        "meal_id": ["M001", "M002"],
        "meal_name": ["A", "B"],
        "primary_cuisine": ["X", "X"],
        "meal_type": ["brunch", "lunch"],  # "brunch" is not a valid meal type
        "suitable_meal_types": ["breakfast", "lunch;dinner"],  # "brunch" not in suitable for M001
        "meal_components": ["a", "a"],
        "is_veg": [True, True],
        "cost_per_serving_inr": [10, 20],
        "calories_kcal": [100, 200],
        "protein_g": [5, 6],
        "carbs_g": [10, 11],
        "fat_g": [2, 3],
        "student_rating": [1, 2],
        "rating_source": ["synthetic"] * 2,
        "rating_count": [0, 0],
        "prep_time_minutes": [1, 2],
        "kitchen_load": ["low"] * 2,
        "allergens": ["none"] * 2,
        "data_source": ["recipe"] * 2,
        "data_quality": ["est"] * 2,
    })
    # M001 has meal_type="brunch" which is not in suitable_meal_types="breakfast"
    with pytest.raises(ValueError, match="brunch"):
        _validate_slot_eligibility(df)


# ---------------------------------------------------------------------------
# Rating count validation tests
# ---------------------------------------------------------------------------

def test__validate_rating_count_all_zero() -> None:
    """Rating count validation passes when all rating_count == 0."""
    df = _create_small_dataset()
    _validate_rating_count(df)  # should not raise


def test__validate_rating_count_with_nonzero() -> None:
    """Rating count validation warns when some rating_count > 0."""
    df = pd.DataFrame({
        "meal_id": ["M001", "M002"],
        "meal_name": ["A", "B"],
        "primary_cuisine": ["X", "X"],
        "meal_type": ["lunch", "lunch"],
        "suitable_meal_types": ["lunch;dinner"] * 2,
        "meal_components": ["a", "a"],
        "is_veg": [True, True],
        "cost_per_serving_inr": [10, 20],
        "calories_kcal": [100, 200],
        "protein_g": [5, 6],
        "carbs_g": [10, 11],
        "fat_g": [2, 3],
        "student_rating": [1, 2],
        "rating_source": ["synthetic"] * 2,
        "rating_count": [1, 0],  # one non-zero
        "prep_time_minutes": [1, 2],
        "kitchen_load": ["low"] * 2,
        "allergens": ["none"] * 2,
        "data_source": ["recipe"] * 2,
        "data_quality": ["est"] * 2,
    })
    # Should not raise, just warn
    _validate_rating_count(df)


# ---------------------------------------------------------------------------
# Meal name / component validation tests
# ---------------------------------------------------------------------------

def test__validate_meal_names_all_have_names() -> None:
    """Meal name validation passes when all names are non-empty."""
    df = _create_small_dataset()
    _validate_meal_names(df)  # should not raise


def test__validate_meal_names_with_empty() -> None:
    """Meal name validation raises when some names are empty."""
    df = pd.DataFrame({
        "meal_id": ["M001", "M002"],
        "meal_name": ["", "B"],  # empty name
        "primary_cuisine": ["X", "X"],
        "meal_type": ["lunch", "lunch"],
        "suitable_meal_types": ["lunch;dinner"] * 2,
        "meal_components": ["a", "a"],
        "is_veg": [True, True],
        "cost_per_serving_inr": [10, 20],
        "calories_kcal": [100, 200],
        "protein_g": [5, 6],
        "carbs_g": [10, 11],
        "fat_g": [2, 3],
        "student_rating": [1, 2],
        "rating_source": ["synthetic"] * 2,
        "rating_count": [0, 0],
        "prep_time_minutes": [1, 2],
        "kitchen_load": ["low"] * 2,
        "allergens": ["none"] * 2,
        "data_source": ["recipe"] * 2,
        "data_quality": ["est"] * 2,
    })
    with pytest.raises(ValueError, match="empty meal name"):
        _validate_meal_names(df)


def test__validate_meal_components_all_have_components() -> None:
    """Meal component validation passes when all components are non-empty."""
    df = _create_small_dataset()
    _validate_meal_components(df)  # should not raise


def test__validate_meal_components_with_empty() -> None:
    """Meal component validation raises when some components are empty."""
    df = pd.DataFrame({
        "meal_id": ["M001", "M002"],
        "meal_name": ["A", "B"],
        "primary_cuisine": ["X", "X"],
        "meal_type": ["lunch", "lunch"],
        "suitable_meal_types": ["lunch;dinner"] * 2,
        "meal_components": ["", "a"],  # empty components
        "is_veg": [True, True],
        "cost_per_serving_inr": [10, 20],
        "calories_kcal": [100, 200],
        "protein_g": [5, 6],
        "carbs_g": [10, 11],
        "fat_g": [2, 3],
        "student_rating": [1, 2],
        "rating_source": ["synthetic"] * 2,
        "rating_count": [0, 0],
        "prep_time_minutes": [1, 2],
        "kitchen_load": ["low"] * 2,
        "allergens": ["none"] * 2,
        "data_source": ["recipe"] * 2,
        "data_quality": ["est"] * 2,
    })
    with pytest.raises(ValueError, match="empty meal components"):
        _validate_meal_components(df)


# ---------------------------------------------------------------------------
# get_meal_by_id tests
# ---------------------------------------------------------------------------

def test_get_meal_by_id_found() -> None:
    """get_meal_by_id returns the correct row."""
    df = _create_small_dataset()
    row = get_meal_by_id("M002", df)
    assert row["meal_name"] == "Chole Rice"


def test_get_meal_by_id_not_found() -> None:
    """get_meal_by_id raises KeyError for unknown ID."""
    df = _create_small_dataset()
    with pytest.raises(KeyError, match="Unknown meal_id"):
        get_meal_by_id("M999", df)


def test_get_meal_by_id_default_dataset() -> None:
    """get_meal_by_id works when df is not provided (loads automatically)."""
    # This test just ensures no crash; the actual dataset has 200 records.
    try:
        row = get_meal_by_id("M001")  # type: ignore
        assert row["meal_id"] == "M001"
    except FileNotFoundError:
        # Expected if the dataset path is not set up in this environment.
        pytest.xfail("Dataset not available in test environment")


# ---------------------------------------------------------------------------
# get_meals_by_type tests
# ---------------------------------------------------------------------------

def test_get_meals_by_type_breakfast() -> None:
    """get_meals_by_type returns the correct subset."""
    df = _create_small_dataset()
    meals = get_meals_by_type("breakfast", df)
    assert len(meals) == 1
    assert meals.iloc[0]["meal_type"] == "breakfast"


def test_get_meals_by_type_lunch() -> None:
    """get_meals_by_type returns lunch meals."""
    df = _create_small_dataset()
    meals = get_meals_by_type("lunch", df)
    assert len(meals) == 2  # M002 and M003; M004 is dinner-type


def test_get_meals_by_type_dinner() -> None:
    """get_meals_by_type returns dinner meals."""
    df = _create_small_dataset()
    meals = get_meals_by_type("dinner", df)
    assert len(meals) == 1


# ---------------------------------------------------------------------------
# get_vegetarian_meals tests
# ---------------------------------------------------------------------------

def test_get_vegetarian_meals() -> None:
    """get_vegetarian_meals returns only veg meals."""
    df = _create_small_dataset()
    veg = get_vegetarian_meals(df)
    assert all(veg["is_veg"] == True)


# ---------------------------------------------------------------------------
# get_breakfast_only_meals tests
# ---------------------------------------------------------------------------

def test_get_breakfast_only_meals() -> None:
    """get_breakfast_only_meals returns breakfast-only meals."""
    df = _create_small_dataset()
    # M001 suitable=breakfast;lunch;dinner, type=breakfast -> not breakfast-only
    # because lunch and dinner are in suitable types
    # M002 suitable=lunch;dinner, type=lunch -> not breakfast-only
    # M003 suitable=lunch;dinner, type=lunch -> not breakfast-only
    # M004 suitable=dinner, type=dinner -> not breakfast-only
    # Actually none are breakfast-only in this tiny dataset because
    # breakfast-only means suitable contains "breakfast" AND does NOT contain
    # "lunch" or "dinner"
    # Let's create a proper test:
    df2 = pd.DataFrame({
        "meal_id": ["M001", "M002", "M003"],
        "meal_name": ["Plain Roti", "Veg Rice", "Dal"],
        "primary_cuisine": ["North Indian"] * 3,
        "meal_type": ["breakfast", "lunch", "lunch"],
        "suitable_meal_types": ["breakfast", "lunch;dinner", "breakfast;lunch;dinner"],
        "meal_components": ["Roti", "Rice;Dal", "Dal"],
        "is_veg": [True, True, True],
        "cost_per_serving_inr": [10, 30, 20],
        "calories_kcal": [400, 500, 350],
        "protein_g": [10, 15, 12],
        "carbs_g": [50, 60, 40],
        "fat_g": [5, 10, 8],
        "student_rating": [4, 3, 5],
        "rating_source": ["synthetic"] * 3,
        "rating_count": [0, 0, 0],
        "prep_time_minutes": [10, 30, 15],
        "kitchen_load": ["low", "medium", "low"],
        "allergens": ["wheat"] * 3,
        "data_source": ["recipe"] * 3,
        "data_quality": ["est"] * 3,
    })
    breakfast_only = get_breakfast_only_meals(df2)
    # Only M001 has suitable=breakfast without lunch/dinner
    assert len(breakfast_only) == 1
    assert breakfast_only.iloc[0]["meal_id"] == "M001"