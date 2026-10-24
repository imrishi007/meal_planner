"""Regression coverage for the Phase 3 default feasible region."""

import numpy as np

from hostel_optimizer import config, data_loader
from hostel_optimizer.optimization import build_slot_eligible_indices


def test_default_cost_and_calorie_bounds_allow_slot_valid_daily_menu() -> None:
    dataset = data_loader.load_dataset()
    breakfast, lunch, dinner = build_slot_eligible_indices(dataset)[:3]
    calories = dataset["calories_kcal"].to_numpy()
    costs = dataset["cost_per_serving_inr"].to_numpy()
    daily_calories = calories[breakfast][:, None, None] + calories[lunch][None, :, None] + calories[dinner][None, None, :]
    daily_costs = costs[breakfast][:, None, None] + costs[lunch][None, :, None] + costs[dinner][None, None, :]

    feasible = (
        (daily_calories >= config.MIN_CALORIES_PER_DAY)
        & (daily_calories <= config.MAX_CALORIES_PER_DAY)
        & (daily_costs <= config.MAX_COST_PER_DAY)
    )
    assert np.count_nonzero(feasible) > 0
