# Hostel Mess Menu Optimizer: Evaluation Engine Documentation

## 21-Chromosome Representation

A weekly menu is represented as a chromosome of exactly 21 integer indices, where each index maps to a row in the dataset. The 21 slots follow this documented order:

| Slot | Day | Meal |
|------|-----|------|
| 0 | Monday | Breakfast |
| 1 | Monday | Lunch |
| 2 | Monday | Dinner |
| 3 | Tuesday | Breakfast |
| 4 | Tuesday | Lunch |
| 5 | Tuesday | Dinner |
| 6 | Wednesday | Breakfast |
| 7 | Wednesday | Lunch |
| 8 | Wednesday | Dinner |
| 9 | Thursday | Breakfast |
| 10 | Thursday | Lunch |
| 11 | Thursday | Dinner |
| 12 | Friday | Breakfast |
| 13 | Friday | Lunch |
| 14 | Friday | Dinner |
| 15 | Saturday | Breakfast |
| 16 | Saturday | Lunch |
| 17 | Saturday | Dinner |
| 18 | Sunday | Breakfast |
| 19 | Sunday | Lunch |
| 20 | Sunday | Dinner |

### Index to Meal Mapping

Each integer index refers to a row in the dataset (accessed via `df.iloc[idx]`). The dataset is sorted by `meal_id` for reproducibility, so index 0 = M001, index 1 = M002, etc.

### Stable 21-ID Signature

The weekly signature is a list of 21 meal_id strings, one per slot, in the documented order. This signature is stable (deterministic for a fixed menu, dataset, and configuration) and will be used by the monthly scheduler to compare weeks and enforce minimum slot differences.

## Three Objectives (all to be minimized)

### Objective 1: Average Daily Cost (f1)

**Formula**: f1 = (sum of costs of all 21 selected meals) / 7

**Daily costs**: Computed separately for each of the 7 days (breakfast + lunch + dinner per day).

**Behavior**: Lower values indicate better cost efficiency. The cost per meal is taken from `cost_per_serving_inr` in the dataset.

### Objective 2: Nutrition Deviation (f2)

**Formula**: For each day d:
```
daily_deviation_d = |daily_calories_d - target_calories| / target_calories
                  + |daily_protein_d - target_protein| / target_protein
```
Then average the seven daily deviations:
```
f2 = (sum of daily_deviation_d for d=0..6) / 7
```

**Targets** (provisional, must be calibrated to hostel):
- `target_calories` = 2000 kcal/day
- `target_protein` = 50 g/day

**Daily calorie minimum and maximum** are enforced separately as hard constraints (see below). The targets represent desired goals, not acceptable intervals.

**Behavior when daily total is above vs below target**: The formula uses absolute deviation divided by the target, so the deviation is symmetric — being 100 kcal above or below the target gives the same calorie deviation. The protein deviation works the same way.

### Objective 3: Dissatisfaction (f3)

**Base formula**: meal_dissatisfaction = 5 - student_rating (rating ranges from 1 to 5)
Average dissatisfaction across the 21 selected meals.

**Repetition penalty**: Configurable penalty for repeated meal IDs within the 3-day window. Each violating pair (same meal on two days with 0 < |day_diff| < 3) adds `REPETITION_PENALTY_PER_REP` to the objective.

**Current default**: `REPETITION_PENALTY_PER_REP = 0.0` (no penalty enabled).

**Important notes**:
- The ratings are synthetic, so this objective is provisional and cannot establish real student satisfaction.
- The penalty only applies to repeats within the 3-day window; repeats on day D and day D+3 or later are NOT penalized.
- Each pair of violating repetitions adds the penalty amount; self-/duplicate-on-same-day is also handled per the window rules.

## Hard Constraints

The following hard constraints are checked for every evaluated menu. A menu is **feasible** if no hard constraints are violated.

### 1. Exactly 21 Choices

The chromosome must have exactly 21 elements. Fewer or more choices trigger a violation.

### 2. Valid Meal Indices

Each index must be in the range [0, n_meals-1], where n_meals is the number of rows in the dataset.

### 3. Slot Eligibility (Breakfast-Only Constraint)

A meal whose `suitable_meal_types` contains only "breakfast" (and neither "lunch" nor "dinner") cannot be placed at lunch or dinner slots. The slot type is determined by position: slot_idx % 3 == 0 → breakfast, == 1 → lunch, == 2 → dinner.

**Violation example**: M004 has `suitable_meal_types = "breakfast"` and `meal_type = "breakfast"`. Placing M004 at slot 1 (Monday lunch) is a violation.

### 4. Daily Calorie Bounds

Each day's total calories (sum of 3 meals' calories_kcal) must satisfy:
- `daily_calories >= MIN_CALORIES_PER_DAY` (1500 kcal default)
- `daily_calories <= MAX_CALORIES_PER_DAY` (3000 kcal default)

Violations are reported per day with the observed and limit values.

### 5. Daily Cost Cap

Each day's total cost (sum of 3 meals' cost_per_serving_inr) must not exceed `MAX_COST_PER_DAY` (80 INR default). Violations are reported per day.

### 6. Vegetarian-Only Policy

When `VEGETARIAN_ONLY = True` (default), all 21 selected meals must have `is_veg = True`. Non-vegetarian meals trigger a violation. When disabled, this check is skipped.

### 7. No Repetition Within Window

A meal ID must not appear on two different days whose day indices differ by less than the configured `REPETITION_WINDOW_DAYS` (3 default). 

**Interpretation**: The same meal may appear on day D and day D+3 or later (the window excludes the boundary). Each pair of violating repetitions is counted.

**Example**: If M001 appears on Monday (day 0) and Wednesday (day 2), the difference is 2 days, which is within the 3-day window → violation. If M001 appears on Monday (day 0) and the following Monday (day 7), the difference is 7 days, which is outside the window → no violation.

### 8. Kitchen Capacity (Disabled by Default)

This constraint is disabled by default. If enabled, it checks that the number of distinct dishes required for a meal service does not exceed the configured kitchen capacity. The semantics are not well-defined from the available data and must be determined operationally.

**Note**: The dataset contains complete meal options, not individual ingredients. A weekly slot selects one complete meal option. Incorrectly counting components inside a complete meal as separate candidate choices is a modeling error.

## Constraint Violation Reporting

Each violation has a `name`, `description`, `observed` value, `limit` value, `severity` ("error"), and optional `day` and `meal_id` fields. The conventions are:

- **Non-positive constraint values** (for pymoo translation): satisfied inequalities have non-positive values; positive values indicate violations
- **Named violations**: Each type has a clear name (see above)
- **Per-day reporting**: Calorie and cost violations are reported per day (0-6 for Monday-Sunday)
- **Meal ID reporting**: Repetition and slot eligibility violations include the meal_id

## Configuration Defaults and Assumptions

| Parameter | Default | Description |
|-----------|---------|-------------|
| `DAYS` | 7 | Number of days in a weekly schedule |
| `NUM_SLOTS` | 21 | 7 × 3 meal slots |
| `DEFAULT_CALORIE_TARGET` | 2000.0 kcal/day | Provisional; must be calibrated to hostel |
| `DEFAULT_PROTEIN_TARGET` | 50.0 g/day | Provisional; must be calibrated to hostel |
| `MIN_CALORIES_PER_DAY` | 1500.0 kcal | Hard lower bound |
| `MAX_CALORIES_PER_DAY` | 3000.0 kcal | Hard upper bound |
| `MAX_COST_PER_DAY` | 80.0 INR | Hard daily cap |
| `VEGETARIAN_ONLY` | True | Enforce veg-only meals |
| `REPETITION_WINDOW_DAYS` | 3 | No meal repeat within 3 calendar days |
| `MIN_DIFFERING_SLOTS` | 7 | Monthly diversity: at least 7 slots must differ between weeks |
| `REPETITION_PENALTY_PER_REP` | 0.0 | Configurable penalty per repeating pair |
| `kitchen_capacity` | False | Disabled by default |

## Target vs. Bounds: Important Distinction

- **Nutrition targets** (calorie_target, protein_target) are **soft goals** for the deviation objective (f2). They indicate desirable daily averages.
- **Calorie bounds** (MIN/MAX_CALORIES_PER_DAY) are **hard constraints** that must be satisfied for a menu to be feasible. A menu exceeding the bounds is infeasible regardless of the target values.
- **Behavior explanation**: When a daily total is above the target, the deviation uses `abs(value - target) / target`. Same behavior when below the target — the formula is symmetric. The bounds are separate from the targets and are always enforced.

## Synthetic Ratings and Estimated Nutrition Limitations

- All `rating_count` values are 0, indicating synthetic (not real student feedback) ratings.
- The dissatisfaction objective (f3) using `5 - rating` is **provisional** and cannot establish real student satisfaction.
- Nutrition values (`calories_kcal`, `protein_g`, `carbs_g`, `fat_g`) are **recipe-estimated** and may not match laboratory-tested values. They should be calibrated to the actual hostel's nutritional data if available.

## Monthly Scheduler Integration (Future)

The weekly evaluator produces a **stable 21-ID signature** for each weekly menu. The future monthly scheduler will:

1. Compare the signatures of two weekly menus
2. Count the number of differing slots (positions where meal_ids differ)
3. Enforce `MIN_DIFFERING_SLOTS >= 7` (provisional: at least 7 of 21 slots must differ between consecutive weeks)
4. Prevent exact weekly repeats and encourage meaningful diversity

For now, the signature helper (`schedule_to_21_id_signature`) is documented and the integration point is designed, but the monthly scheduler logic is not implemented in Phase 2.

## How the Engine Integrates with pymoo NSGA-II (Future)

The evaluation engine is designed to be compatible with pymoo's NSGA-II optimizer. The typical integration pattern is:

1. The evaluator function `evaluate_menu(chromosome, dataset, config)` returns `(f1, f2, f3)` objectives and constraint violations
2. pymoo's constraint array convention: non-positive values = satisfied, positive values = violated
3. The constraint violations from `evaluate_menu` can be translated into pymoo's constraint array format
4. The population evolves to find Pareto-optimal solutions along the tradeoff front between the three objectives

This integration is planned for Phase 3 and is not implemented in the current phase.
