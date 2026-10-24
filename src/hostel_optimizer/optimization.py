"""NSGA-II integration for feasible weekly hostel menu candidates.

The Phase 2 evaluator remains the source of truth for objectives and hard
constraint reporting.  This module only supplies a slot-aware integer search
space and translates evaluator output to pymoo's ``G <= 0`` convention.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

import numpy as np
import pandas as pd

from . import config, data_loader, evaluation

try:
    from pymoo.algorithms.moo.nsga2 import NSGA2
    from pymoo.core.crossover import Crossover
    from pymoo.core.mutation import Mutation
    from pymoo.core.problem import Problem
    from pymoo.core.sampling import Sampling
    from pymoo.optimize import minimize
except ImportError as exc:  # pragma: no cover - exercised only without dependency
    PYMOO_IMPORT_ERROR = exc
    NSGA2 = Crossover = Mutation = Problem = Sampling = None  # type: ignore[assignment,misc]
    minimize = None  # type: ignore[assignment]
else:
    PYMOO_IMPORT_ERROR = None


SLOT_TYPES = ("breakfast", "lunch", "dinner")
CONSTRAINT_NAMES = (
    *(f"daily_calorie_min_day_{day}" for day in range(config.DAYS)),
    *(f"daily_calorie_max_day_{day}" for day in range(config.DAYS)),
    *(f"daily_cost_cap_day_{day}" for day in range(config.DAYS)),
    "slot_eligibility",
    "vegetarian_only",
    "no_repetition_within_window",
)


@dataclass(frozen=True)
class OptimizationConfig:
    """Reproducible, development-friendly settings for one NSGA-II run."""

    population_size: int = 100
    generations: int = 100
    seed: int = 42
    crossover_probability: float = 0.9
    mutation_probability: float | None = None
    initialization_attempts: int = 100
    verbose: bool = False

    def __post_init__(self) -> None:
        if self.population_size < 2 or self.generations < 1:
            raise ValueError("population_size must be >= 2 and generations must be >= 1")
        if not 0.0 <= self.crossover_probability <= 1.0:
            raise ValueError("crossover_probability must be between 0 and 1")
        if self.mutation_probability is not None and not 0.0 <= self.mutation_probability <= 1.0:
            raise ValueError("mutation_probability must be between 0 and 1")


def _require_pymoo() -> None:
    if PYMOO_IMPORT_ERROR is not None:
        raise RuntimeError(
            "pymoo is required for optimization. Install project dependencies with "
            "`python -m pip install -e .` or `python -m pip install pymoo`."
        ) from PYMOO_IMPORT_ERROR


def build_slot_eligible_indices(dataset: pd.DataFrame) -> tuple[np.ndarray, ...]:
    """Return stable dataframe-row indices eligible for every chromosome slot."""
    eligible_by_type: dict[str, list[int]] = {slot_type: [] for slot_type in SLOT_TYPES}
    for index, row in dataset.iterrows():
        suitable = {part.strip() for part in str(row["suitable_meal_types"]).split(";")}
        if config.VEGETARIAN_ONLY and not bool(row["is_veg"]):
            continue
        for slot_type in SLOT_TYPES:
            if slot_type in suitable:
                eligible_by_type[slot_type].append(int(index))

    empty = [slot_type for slot_type, values in eligible_by_type.items() if not values]
    if empty:
        raise ValueError(f"Dataset has no eligible meals for: {', '.join(empty)}")
    return tuple(np.asarray(eligible_by_type[SLOT_TYPES[slot % 3]], dtype=int) for slot in range(config.NUM_SLOTS))


def build_daily_feasible_options(dataset: pd.DataFrame, eligible: tuple[np.ndarray, ...]) -> np.ndarray:
    """Return slot-valid daily triples satisfying Phase 2 calorie and cost bounds."""
    breakfast, lunch, dinner = eligible[:3]
    calories = dataset["calories_kcal"].to_numpy(dtype=float)
    costs = dataset["cost_per_serving_inr"].to_numpy(dtype=float)
    daily_calories = calories[breakfast][:, None, None] + calories[lunch][None, :, None] + calories[dinner][None, None, :]
    daily_costs = costs[breakfast][:, None, None] + costs[lunch][None, :, None] + costs[dinner][None, None, :]
    positions = np.argwhere(
        (daily_calories >= config.MIN_CALORIES_PER_DAY)
        & (daily_calories <= config.MAX_CALORIES_PER_DAY)
        & (daily_costs <= config.MAX_COST_PER_DAY)
    )
    triples = np.column_stack((breakfast[positions[:, 0]], lunch[positions[:, 1]], dinner[positions[:, 2]])).astype(int)
    triples = triples[np.asarray([len(set(triple)) == 3 for triple in triples])]
    if len(triples) == 0:
        raise ValueError("No slot-valid daily menu satisfies the configured calorie and cost constraints")
    return triples


def _sample_feasible_chromosome(daily_options: np.ndarray, rng: np.random.Generator, attempts: int) -> np.ndarray:
    """Build one week while respecting the Phase 2 non-repetition window."""
    for _ in range(attempts):
        days: list[np.ndarray] = []
        for _day in range(config.DAYS):
            candidates = daily_options[rng.permutation(len(daily_options))]
            recent = set(np.concatenate(days[-(config.REPETITION_WINDOW_DAYS - 1):])) if days else set()
            choice = next((candidate for candidate in candidates if not recent.intersection(candidate)), None)
            if choice is None:
                break
            days.append(choice)
        if len(days) == config.DAYS:
            return np.concatenate(days).astype(int)
    raise RuntimeError("Unable to construct a feasible initial weekly menu under the configured constraints")


def _is_slot_valid(chromosome: Iterable[int], eligible: tuple[np.ndarray, ...]) -> bool:
    values = list(chromosome)
    return len(values) == config.NUM_SLOTS and all(int(gene) in eligible[slot] for slot, gene in enumerate(values))


def evaluator_constraint_vector(result: dict[str, Any]) -> np.ndarray:
    """Translate Phase 2 evaluation output into fixed normalized ``G <= 0`` values."""
    totals = result["daily_totals"]
    values: list[float] = []
    values.extend(
        (config.MIN_CALORIES_PER_DAY - float(value)) / config.MIN_CALORIES_PER_DAY
        for value in totals["daily_calories"]
    )
    values.extend(
        (float(value) - config.MAX_CALORIES_PER_DAY) / config.MAX_CALORIES_PER_DAY
        for value in totals["daily_calories"]
    )
    values.extend(
        (float(value) - config.MAX_COST_PER_DAY) / config.MAX_COST_PER_DAY
        for value in totals["daily_cost"]
    )
    violations = result["constraint_violations"]
    values.append(float(sum(item.name == "slot_eligibility" for item in violations)))
    values.append(float(sum(item.name == "vegetarian_only" for item in violations)))
    values.append(float(sum(item.name == "no_repetition_within_window" for item in violations)))
    return np.asarray(values, dtype=float)


if PYMOO_IMPORT_ERROR is None:

    class SlotAwareSampling(Sampling):
        """Sample integer genes only from their matching meal-slot candidates."""

        def __init__(self, eligible: tuple[np.ndarray, ...], daily_options: np.ndarray, seed: int | None = None, attempts: int = 100) -> None:
            super().__init__()
            self.eligible = eligible
            self.daily_options = daily_options
            self.rng = np.random.default_rng(seed)
            self.attempts = attempts

        def _do(self, problem: Problem, n_samples: int, **kwargs: Any) -> np.ndarray:
            return np.asarray([_sample_feasible_chromosome(self.daily_options, self.rng, self.attempts) for _ in range(n_samples)], dtype=int)


    class SlotAwareCrossover(Crossover):
        """Uniform crossover; inherited values are valid for the same slot."""

        def __init__(self, probability: float = 0.9, seed: int | None = None) -> None:
            super().__init__(2, 2, prob=probability)
            self.rng = np.random.default_rng(seed)

        def _do(self, problem: Problem, parents: np.ndarray, **kwargs: Any) -> np.ndarray:
            children = parents.copy().astype(int)
            swaps = self.rng.random(parents.shape[2]) < 0.5
            children[0, :, swaps], children[1, :, swaps] = parents[1, :, swaps], parents[0, :, swaps]
            return children


    class SlotAwareMutation(Mutation):
        """Replace mutated genes with a different valid choice for that slot."""

        def __init__(self, eligible: tuple[np.ndarray, ...], probability: float | None, seed: int | None = None) -> None:
            super().__init__(prob=1.0)
            self.eligible = eligible
            self.probability = probability if probability is not None else 1.0 / config.NUM_SLOTS
            self.rng = np.random.default_rng(seed)

        def _do(self, problem: Problem, values: np.ndarray, **kwargs: Any) -> np.ndarray:
            mutated = values.copy().astype(int)
            for row in mutated:
                for slot, options in enumerate(self.eligible):
                    if self.rng.random() < self.probability and len(options) > 1:
                        alternatives = options[options != row[slot]]
                        row[slot] = int(self.rng.choice(alternatives))
            return mutated


    class WeeklyMenuProblem(Problem):
        """Pymoo problem delegating objectives and violations to Phase 2."""

        def __init__(self, dataset: pd.DataFrame, eligible: tuple[np.ndarray, ...]) -> None:
            super().__init__(n_var=config.NUM_SLOTS, n_obj=3, n_ieq_constr=len(CONSTRAINT_NAMES), xl=0, xu=len(dataset) - 1, vtype=int)
            self.dataset = dataset
            self.eligible = eligible
            self.evaluations: list[dict[str, Any]] = []

        def _evaluate(self, values: np.ndarray, out: dict[str, Any], **kwargs: Any) -> None:
            objectives: list[tuple[float, float, float]] = []
            constraints: list[np.ndarray] = []
            batch: list[dict[str, Any]] = []
            for chromosome in values:
                genes = [int(gene) for gene in chromosome]
                if not _is_slot_valid(genes, self.eligible):
                    raise ValueError("NSGA-II produced a slot-invalid chromosome")
                result = evaluation.evaluate_menu(genes, self.dataset)
                objective = tuple(float(value) for value in result["objectives"])
                if len(objective) != 3 or not np.isfinite(objective).all():
                    raise ValueError("Evaluator returned non-finite or malformed objectives")
                objectives.append(objective)
                constraints.append(evaluator_constraint_vector(result))
                batch.append(result)
            self.evaluations.extend(batch)
            out["F"] = np.asarray(objectives, dtype=float)
            out["G"] = np.asarray(constraints, dtype=float)

else:  # Keeps imports useful enough to report the missing optional dependency.
    SlotAwareSampling = SlotAwareCrossover = SlotAwareMutation = WeeklyMenuProblem = None  # type: ignore[misc,assignment]


def _solution_record(chromosome: Iterable[int], dataset: pd.DataFrame) -> dict[str, Any]:
    genes = [int(gene) for gene in chromosome]
    result = evaluation.evaluate_menu(genes, dataset)
    return {
        "chromosome": genes,
        "signature": tuple(result["weekly_signature"]),
        "objectives": tuple(float(value) for value in result["objectives"]),
        "is_feasible": bool(result["is_feasible"]),
        "constraint_violations": result["constraint_violations"],
        "daily_totals": result["daily_totals"],
        "schedule": evaluation.chromosome_to_schedule(genes, dataset),
    }


def is_non_dominated(candidate: dict[str, Any], candidates: Iterable[dict[str, Any]]) -> bool:
    """Return whether no other candidate weakly improves all objectives."""
    objective = np.asarray(candidate["objectives"], dtype=float)
    for other in candidates:
        if other is candidate:
            continue
        alternative = np.asarray(other["objectives"], dtype=float)
        if np.all(alternative <= objective) and np.any(alternative < objective):
            return False
    return True


def select_compromise_solution(solutions: list[dict[str, Any]], weights: tuple[float, float, float] = (1.0, 1.0, 1.0)) -> dict[str, Any] | None:
    """Select a presentation compromise without changing the Pareto set."""
    if not solutions:
        return None
    weights_array = np.asarray(weights, dtype=float)
    if weights_array.shape != (3,) or np.any(weights_array < 0) or not weights_array.any():
        raise ValueError("weights must contain three non-negative values with at least one positive")
    objectives = np.asarray([solution["objectives"] for solution in solutions], dtype=float)
    span = objectives.max(axis=0) - objectives.min(axis=0)
    normalized = (objectives - objectives.min(axis=0)) / np.where(span == 0, 1.0, span)
    return solutions[int(np.argmin(normalized @ (weights_array / weights_array.sum())))]


def random_slot_valid_baseline(dataset: pd.DataFrame, seed: int = 42, attempts: int = 1_000) -> dict[str, Any]:
    """Return a feasible random baseline, or transparent failure diagnostics."""
    eligible = build_slot_eligible_indices(dataset)
    rng = np.random.default_rng(seed)
    best: dict[str, Any] | None = None
    for attempt in range(1, attempts + 1):
        record = _solution_record([int(rng.choice(options)) for options in eligible], dataset)
        if record["is_feasible"]:
            return {"found": True, "attempts": attempt, "solution": record}
        if best is None or len(record["constraint_violations"]) < len(best["constraint_violations"]):
            best = record
    return {"found": False, "attempts": attempts, "best_candidate": best}


def greedy_low_cost_baseline(dataset: pd.DataFrame) -> dict[str, Any]:
    """Evaluate the cheapest slot-valid menu without claiming it is feasible."""
    eligible = build_slot_eligible_indices(dataset)
    chromosome = [int(options[np.argmin(dataset.iloc[options]["cost_per_serving_inr"].to_numpy())]) for options in eligible]
    record = _solution_record(chromosome, dataset)
    return {"found": record["is_feasible"], "solution": record}


def optimize_weekly_menus(
    optimization_config: OptimizationConfig | None = None,
    dataset: pd.DataFrame | None = None,
    seed: int | None = None,
) -> dict[str, Any]:
    """Run constrained NSGA-II and return unique feasible approximate Pareto menus."""
    _require_pymoo()
    settings = optimization_config or OptimizationConfig()
    effective_seed = settings.seed if seed is None else seed
    source = data_loader.load_dataset() if dataset is None else dataset.copy()
    eligible = build_slot_eligible_indices(source)
    daily_options = build_daily_feasible_options(source, eligible)
    problem = WeeklyMenuProblem(source, eligible)
    algorithm = NSGA2(
        pop_size=settings.population_size,
        sampling=SlotAwareSampling(eligible, daily_options, effective_seed, settings.initialization_attempts),
        crossover=SlotAwareCrossover(settings.crossover_probability, effective_seed + 1),
        mutation=SlotAwareMutation(eligible, settings.mutation_probability, effective_seed + 2),
        eliminate_duplicates=True,
    )
    result = minimize(problem, algorithm, termination=("n_gen", settings.generations), seed=effective_seed, verbose=settings.verbose, save_history=True)
    population = result.pop if result.pop is not None else []
    records: dict[tuple[str, ...], dict[str, Any]] = {}
    feasible_per_generation: list[int] = []
    best_constraint_violation: list[float] = []
    for state in result.history:
        cv = np.asarray(state.pop.get("CV"), dtype=float).reshape(-1)
        feasible_per_generation.append(int(np.count_nonzero(cv <= 0.0)))
        best_constraint_violation.append(float(cv.min()) if len(cv) else float("inf"))
    for chromosome in population.get("X") if len(population) else []:
        record = _solution_record(chromosome, source)
        if record["is_feasible"]:
            records.setdefault(record["signature"], record)
    feasible = list(records.values())
    pareto = [record for record in feasible if is_non_dominated(record, feasible)]
    pareto.sort(key=lambda item: item["objectives"])
    return {
        "pareto_solutions": pareto,
        "has_feasible_solutions": bool(pareto),
        "compromise_solution": select_compromise_solution(pareto),
        "settings": asdict(settings),
        "seed": effective_seed,
        "diagnostics": {
            "eligible_options_per_slot": [int(len(options)) for options in eligible],
            "daily_feasible_options": int(len(daily_options)),
            "evaluated_candidates": len(problem.evaluations),
            "evaluated_feasible_candidates": sum(bool(item["is_feasible"]) for item in problem.evaluations),
            "evaluated_infeasible_candidates": sum(not bool(item["is_feasible"]) for item in problem.evaluations),
            "feasible_candidates_per_generation": feasible_per_generation,
            "best_constraint_violation_per_generation": best_constraint_violation,
            "final_feasible_population_size": len(feasible),
            "distinct_feasible_signatures": len(records),
            "constraint_names": CONSTRAINT_NAMES,
        },
        "message": "Approximate feasible Pareto front generated by NSGA-II." if pareto else "No feasible weekly menu was found; constraints were not relaxed.",
    }
