"""Configuration module for the Hostel Mess Menu Optimizer.

Provisional defaults are documented with clear explanations that they must
be calibrated to the actual hostel.  All values are intended to be
overridden via configuration or command-line flags before production use.
"""

from __future__ import annotations

from typing import Final

# === General settings ===
DAYS: Final[int] = 7
MEAL_SLOTS: Final[str] = "breakfast, lunch, dinner"
NUM_SLOTS: Final[int] = DAYS * 3  # 21

# === Nutrition targets (provisional – calibrate to your hostel) ===
# Default calorie target: around 2000 kcal/day for average adult.
# Default protein target: around 50 g/day.
# These are *targets* for the deviation objective; they are NOT hard
#   bounds.  Daily calorie minimum and maximum are enforced separately
#   as hard constraints (see below).
DEFAULT_CALORIE_TARGET: Final[float] = 2000.0   # kcal per day
DEFAULT_PROTEIN_TARGET: Final[float] = 50.0    # g per day

# Daily calorie hard bounds (minimum and maximum acceptable per day).
# Choose values that permit feasibility testing.  Must be calibrated to
# the actual hostel; these are placeholders.
MIN_CALORIES_PER_DAY: Final[float] = 1500.0   # kcal
MAX_CALORIES_PER_DAY: Final[float] = 3000.0   # kcal

# Maximum daily food cost per student (in INR).  Must be calibrated to
# the actual hostel.  Meal cost is per serving; the cap applies per day.
MAX_COST_PER_DAY: Final[float] = 80.0   # INR per day

# === Policy settings ===
VEGETARIAN_ONLY: Final[bool] = True  # enforce vegetarian-only meals

# Repetition window: a meal must not reappear within this many calendar
# days.  A three-day window means: if meal X is served on Day D, the same
# meal cannot appear on Days D+1, D+2, or D+3 (modulo 7).  The window
# wraps around the week.
REPETITION_WINDOW_DAYS: Final[int] = 3

# Minimum number of differing meal slots between two weekly schedules
# (monthly diversity setting).  7 out of 21 is the provisional default.
MIN_DIFFERING_SLOTS: Final[int] = 7

# Repetition penalty per violating pair (within the three-day window).
# Set to 0.0 to disable; positive values add to the dissatisfaction objective.
REPETITION_PENALTY_PER_REP: float = 0.0

# === Derived constants ===
SLOT_ORDER: Final[list[str]] = [
    "Monday breakfast",
    "Monday lunch",
    "Monday dinner",
    "Tuesday breakfast",
    "Tuesday lunch",
    "Tuesday dinner",
    "Wednesday breakfast",
    "Wednesday lunch",
    "Wednesday dinner",
    "Thursday breakfast",
    "Thursday lunch",
    "Thursday dinner",
    "Friday breakfast",
    "Friday lunch",
    "Friday dinner",
    "Saturday breakfast",
    "Saturday lunch",
    "Saturday dinner",
    "Sunday breakfast",
    "Sunday lunch",
    "Sunday dinner",
]

# ---------------------------------------------------------------------------
# Documentation of assumptions (imported where needed)
# ---------------------------------------------------------------------------

__doc__ = """
Configuration assumptions:

1. Nutrition targets (calorie_target, protein_target) are provisional
   software-testing assumptions around 2000 kcal and 50 g protein.
   They are NOT medical advice or universal requirements.

2. MIN_CALORIES_PER_DAY and MAX_CALORIES_PER_DAY are hard bounds that
   are enforced as constraints.  They must be set wide enough to allow
   feasible menus given the available meal options.

3. VEGETARIAN_ONLY=True means every selected meal must have
   is_veg=True in the dataset.

4. REPETITION_WINDOW_DAYS=3 means a meal ID may not appear twice within
   a three-day interval.  See the evaluation engine for the exact
   interpretation (same meal on day D and day D+3 is allowed; same meal
   on day D and day D+2 is prohibited).

5. MIN_DIFFERING_SLOTS=7 is a monthly-diversity setting: when comparing
   two weekly schedules, at least 7 of the 21 slots must differ.  This
   is *not* implemented in the weekly evaluator; it is documented for
   later integration with the monthly scheduler.

6. All cost, calorie, and protein values are per-serving (per meal).
   Daily totals are the sum of three meals (breakfast + lunch + dinner).
"""
