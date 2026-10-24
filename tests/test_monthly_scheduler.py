"""Phase 5 monthly-scheduling tests using real evaluator-compatible candidates."""

from hostel_optimizer import config, data_loader
from hostel_optimizer.benchmarking import BaselineConfig, random_feasible_search
import json

from hostel_optimizer.monthly_scheduler import MonthlySchedulerConfig, schedule_monthly_menu, serialize_monthly_result, weekly_slot_difference


def _candidates(count: int = 8):
    return random_feasible_search(data_loader.load_dataset(), seed=19, config=BaselineConfig(random_candidates=count))["all_feasible_solutions"]


def test_weekly_difference_uses_slot_positions() -> None:
    left = tuple(f"M{index:03d}" for index in range(21))
    right = list(left)
    right[0], right[1] = right[1], right[0]
    assert weekly_slot_difference(left, right) == 2


def test_monthly_scheduler_selects_feasible_diverse_weeks() -> None:
    result = schedule_monthly_menu(_candidates(), MonthlySchedulerConfig(seed=19, candidate_limit=8))

    assert result["has_schedule"]
    assert len(result["weeks"]) == 4
    assert all(len(week["signature"]) == config.NUM_SLOTS and week["is_feasible"] for week in result["weeks"])
    assert all(item["different_slots"] >= config.MIN_DIFFERING_SLOTS for item in result["pairwise_differences"])
    assert result["monthly_summary"]["distinct_meal_count"] > 0
    assert result["monthly_summary"]["monthly_total_cost"] > 0
    assert json.dumps(serialize_monthly_result(result))


def test_monthly_scheduler_reports_insufficient_and_duplicate_pool() -> None:
    candidate = _candidates(1)[0]
    result = schedule_monthly_menu([candidate, candidate], MonthlySchedulerConfig())

    assert not result["has_schedule"]
    assert "Insufficient" in result["message"]


def test_monthly_scheduler_skips_malformed_candidates() -> None:
    result = schedule_monthly_menu([{"chromosome": [999], "signature": ("bad",)}], MonthlySchedulerConfig())

    assert not result["has_schedule"]
    assert result["diagnostics"]["candidate_pool_size"] == 0
