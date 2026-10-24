"""Focused Phase 3 tests for slot-aware optimization helpers."""

import math

import numpy as np
import pytest

from hostel_optimizer import config, data_loader, evaluation, optimization


def test_slot_eligible_indices_produce_valid_integer_chromosome() -> None:
    dataset = data_loader.load_dataset()
    eligible = optimization.build_slot_eligible_indices(dataset)
    chromosome = [int(options[0]) for options in eligible]

    assert len(chromosome) == config.NUM_SLOTS
    assert all(isinstance(gene, int) for gene in chromosome)
    assert all(gene in eligible[slot] for slot, gene in enumerate(chromosome))


def test_constraint_vector_matches_phase2_evaluation() -> None:
    dataset = data_loader.load_dataset()
    chromosome = [int(options[0]) for options in optimization.build_slot_eligible_indices(dataset)]
    result = evaluation.evaluate_menu(chromosome, dataset)
    constraints = optimization.evaluator_constraint_vector(result)

    assert constraints.shape == (len(optimization.CONSTRAINT_NAMES),)
    assert np.isfinite(constraints).all()
    assert (constraints > 0).any() == (not result["is_feasible"])


def test_solution_record_uses_evaluator_objectives() -> None:
    dataset = data_loader.load_dataset()
    chromosome = [int(options[-1]) for options in optimization.build_slot_eligible_indices(dataset)]
    record = optimization._solution_record(chromosome, dataset)
    expected = evaluation.evaluate_menu(chromosome, dataset)

    assert record["objectives"] == expected["objectives"]
    assert record["signature"] == tuple(expected["weekly_signature"])
    assert len(record["schedule"]["all_slots"]) == config.NUM_SLOTS
    assert all(math.isfinite(value) for value in record["objectives"])


def test_compromise_preserves_original_pareto_candidates() -> None:
    solutions = [
        {"objectives": (10.0, 2.0, 3.0)},
        {"objectives": (12.0, 1.0, 2.0)},
    ]
    selected = optimization.select_compromise_solution(solutions)

    assert selected in solutions
    assert len(solutions) == 2


@pytest.mark.skipif(optimization.PYMOO_IMPORT_ERROR is not None, reason="pymoo is not installed")
def test_custom_operators_preserve_integer_slot_validity() -> None:
    dataset = data_loader.load_dataset()
    eligible = optimization.build_slot_eligible_indices(dataset)
    daily_options = optimization.build_daily_feasible_options(dataset, eligible)
    rng = np.random.default_rng(11)
    first = optimization._sample_feasible_chromosome(daily_options, rng, 100)
    second = optimization._sample_feasible_chromosome(daily_options, rng, 100)
    parents = np.stack((first, second), axis=0)[:, None, :]
    children = optimization.SlotAwareCrossover(seed=12)._do(None, parents)
    mutated = optimization.SlotAwareMutation(eligible, probability=1.0, seed=13)._do(None, children.reshape(2, -1))

    assert np.issubdtype(children.dtype, np.integer)
    assert np.issubdtype(mutated.dtype, np.integer)
    assert all(optimization._is_slot_valid(child, eligible) for child in children.reshape(2, -1))
    assert all(optimization._is_slot_valid(child, eligible) for child in mutated)


@pytest.mark.skipif(optimization.PYMOO_IMPORT_ERROR is not None, reason="pymoo is not installed")
def test_small_nsga2_run_is_reproducible_and_returns_valid_schedules() -> None:
    dataset = data_loader.load_dataset()
    settings = optimization.OptimizationConfig(population_size=20, generations=3, seed=7)
    first = optimization.optimize_weekly_menus(settings, dataset)
    second = optimization.optimize_weekly_menus(settings, dataset)

    assert first["diagnostics"]["feasible_candidates_per_generation"] == second["diagnostics"]["feasible_candidates_per_generation"]
    assert first["diagnostics"]["evaluated_candidates"] == (
        first["diagnostics"]["evaluated_feasible_candidates"]
        + first["diagnostics"]["evaluated_infeasible_candidates"]
    )
    for solution in first["pareto_solutions"]:
        assert solution["is_feasible"]
        assert len(solution["chromosome"]) == config.NUM_SLOTS
        assert len(solution["signature"]) == config.NUM_SLOTS
        assert len(solution["schedule"]["all_slots"]) == config.NUM_SLOTS
        assert optimization.is_non_dominated(solution, first["pareto_solutions"])
