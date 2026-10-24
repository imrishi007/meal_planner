"""HTTP adapter for the existing hostel menu optimization modules."""

from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4
from zoneinfo import ZoneInfo

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from . import config, data_loader, evaluation
from .monthly_scheduler import MonthlySchedulerConfig, schedule_monthly_menu, weekly_slot_difference
from .optimization import OptimizationConfig, optimize_weekly_menus

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[2]
STORE = Path(os.environ.get("HOSTEL_MENU_STORE", ROOT / "data" / "generated_plans"))
APP_TIMEZONE = ZoneInfo(os.environ.get("HOSTEL_MENU_TIMEZONE", "Asia/Kolkata"))
DAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
SLOTS = ("breakfast", "lunch", "dinner")
HORIZONS = ("today", "tomorrow", "next_3_days", "next_7_days", "four_weeks")


class GenerateRequest(BaseModel):
    horizon: Literal["today", "tomorrow", "next_3_days", "next_7_days", "four_weeks"]
    seed: int = Field(default=42, ge=0, le=2_147_483_647)
    population_size: int = Field(default=40, ge=4, le=200)
    generations: int = Field(default=12, ge=1, le=100)


class MealResponse(BaseModel):
    meal_id: str
    meal_name: str
    cuisine: str
    meal_type: str
    suitable_meal_types: list[str]
    meal_components: list[str]
    allergens: str
    prep_time_minutes: int
    kitchen_load: str
    rating_count: int
    cost: float
    calories: float
    protein: float
    carbs: float
    fat: float
    rating: float
    rating_source: str
    is_veg: bool


class ScheduledMealResponse(MealResponse):
    slot: str


class DayResponse(BaseModel):
    date: str
    day_name: str
    meals: list[ScheduledMealResponse]
    daily_cost: float
    daily_calories: float
    daily_protein: float


class WeekResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    week_number: int
    signature: list[str]
    objectives: list[float]
    is_feasible: bool
    days: list[DayResponse]


class PairDifferenceResponse(BaseModel):
    week_a: int
    week_b: int
    different_slots: int


class MenuResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    plan_id: str
    created_at: str
    horizon: Literal["today", "tomorrow", "next_3_days", "next_7_days", "four_weeks"]
    start_date: str
    days: list[DayResponse] | None = None
    weeks: list[WeekResponse] | None = None
    pairwise_differences: list[PairDifferenceResponse] | None = None
    monthly_summary: dict[str, Any] | None = None
    weekly_objectives: list[float] | None = None
    weekly_signature: list[str] | None = None
    is_feasible: bool
    seed: int
    settings: dict[str, Any]
    diagnostics: dict[str, Any] | None = None


class MenuEnvelopeResponse(BaseModel):
    plan: MenuResponse | None


class MealListResponse(BaseModel):
    meals: list[MealResponse]
    total: int


class HealthResponse(BaseModel):
    status: str
    timezone: str
    daily_cost_cap_inr: float
    minimum_daily_calories: float
    maximum_daily_calories: float
    calorie_target_kcal: float
    protein_target_g: float
    minimum_weekly_differing_slots: int


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "item"):
        return value.item()
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _meal_record(meal_id: str, dataset: pd.DataFrame) -> dict[str, Any]:
    meal = data_loader.get_meal_by_id(meal_id, dataset)
    return {
        "meal_id": str(meal["meal_id"]),
        "meal_name": str(meal["meal_name"]),
        "cuisine": str(meal["primary_cuisine"]),
        "meal_type": str(meal["meal_type"]),
        "suitable_meal_types": [part.strip() for part in str(meal["suitable_meal_types"]).split(";")],
        "meal_components": [part.strip() for part in str(meal["meal_components"]).split(";")],
        "allergens": str(meal["allergens"]),
        "prep_time_minutes": int(meal["prep_time_minutes"]),
        "kitchen_load": str(meal["kitchen_load"]),
        "rating_count": int(meal["rating_count"]),
        "cost": float(meal["cost_per_serving_inr"]),
        "calories": float(meal["calories_kcal"]),
        "protein": float(meal["protein_g"]),
        "carbs": float(meal["carbs_g"]),
        "fat": float(meal["fat_g"]),
        "rating": float(meal["student_rating"]),
        "rating_source": str(meal["rating_source"]),
        "is_veg": bool(meal["is_veg"]),
    }


def _day_records(signature: list[str] | tuple[str, ...], start_date: date, dataset: pd.DataFrame, daily_totals: dict[str, Any], offset: int = 0) -> list[dict[str, Any]]:
    days: list[dict[str, Any]] = []
    for day_index in range(7):
        actual_date = start_date + timedelta(days=offset + day_index)
        meal_start = day_index * len(SLOTS)
        meals = [
            {"slot": slot, **_meal_record(str(signature[meal_start + slot_index]), dataset)}
            for slot_index, slot in enumerate(SLOTS)
        ]
        days.append({
            "date": actual_date.isoformat(),
            "day_name": actual_date.strftime("%A"),
            "meals": meals,
            "daily_cost": float(daily_totals["daily_cost"][day_index]),
            "daily_calories": float(daily_totals["daily_calories"][day_index]),
            "daily_protein": float(daily_totals["daily_protein"][day_index]),
        })
    return days


def _base_plan(horizon: str, seed: int, settings: OptimizationConfig, dataset: pd.DataFrame) -> dict[str, Any]:
    today = datetime.now(APP_TIMEZONE).date()
    start_date = today if horizon == "today" else today + timedelta(days=1)
    if horizon == "four_weeks":
        monthly_settings = MonthlySchedulerConfig(seed=seed)
        monthly = schedule_monthly_menu(
            scheduler_config=monthly_settings,
            optimization_config=settings,
            dataset=dataset,
        )
        if not monthly.get("has_schedule"):
            raise RuntimeError(monthly.get("message", "No feasible four-week menu was found."))
        weeks = monthly.get("weeks", [])
        if len(weeks) != monthly_settings.weeks:
            raise RuntimeError("The monthly scheduler did not return the configured number of weeks.")
        for left_index in range(len(weeks)):
            for right_index in range(left_index + 1, len(weeks)):
                difference = weekly_slot_difference(weeks[left_index]["signature"], weeks[right_index]["signature"])
                if difference < monthly_settings.min_differing_slots:
                    raise RuntimeError("The monthly schedule did not meet its configured meal-variety rule.")
        for week_offset, week in enumerate(weeks):
            evaluated = evaluation.evaluate_menu([int(value) for value in week["chromosome"]], dataset)
            if not evaluated["is_feasible"]:
                raise RuntimeError("A generated week failed the existing feasibility evaluator.")
            week["days"] = _day_records(week["signature"], start_date + timedelta(days=7 * week_offset), dataset, evaluated["daily_totals"])
        return {
            "horizon": horizon,
            "start_date": start_date.isoformat(),
            "weeks": weeks,
            "pairwise_differences": monthly["pairwise_differences"],
            "monthly_summary": monthly["monthly_summary"],
            "settings": monthly["settings"],
            "seed": seed,
            "diagnostics": monthly["diagnostics"],
            "is_feasible": True,
        }

    result = optimize_weekly_menus(settings, dataset, seed=seed)
    solutions = result.get("pareto_solutions", [])
    if not solutions:
        raise RuntimeError(result.get("message", "No feasible weekly menu was found."))
    selected = result.get("compromise_solution") or solutions[0]
    evaluated = evaluation.evaluate_menu([int(value) for value in selected["chromosome"]], dataset)
    if not evaluated["is_feasible"]:
        raise RuntimeError("The selected weekly menu failed the existing feasibility evaluator.")
    days = _day_records(selected["signature"], start_date, dataset, evaluated["daily_totals"])
    count = {"today": 1, "tomorrow": 1, "next_3_days": 3, "next_7_days": 7}[horizon]
    return {
        "horizon": horizon,
        "start_date": start_date.isoformat(),
        "days": days[:count],
        "weekly_objectives": list(selected["objectives"]),
        "weekly_signature": list(selected["signature"]),
        "is_feasible": True,
        "settings": result["settings"],
        "seed": seed,
        "diagnostics": result["diagnostics"],
    }


def _save_plan(plan: dict[str, Any]) -> dict[str, Any]:
    plan_id = str(uuid4())
    created_at = datetime.now(APP_TIMEZONE).isoformat(timespec="seconds")
    saved = _json_safe({**plan, "plan_id": plan_id, "created_at": created_at})
    encoded = json.dumps(saved, ensure_ascii=False, indent=2)
    STORE.mkdir(parents=True, exist_ok=True)
    temporary = STORE / f".{plan_id}.tmp"
    final = STORE / f"{plan_id}.json"
    temporary.write_text(encoded, encoding="utf-8")
    temporary.replace(final)
    pointer_temp = STORE / ".current.tmp"
    pointer_temp.write_text(plan_id, encoding="utf-8")
    pointer_temp.replace(STORE / "current.txt")
    return saved


def _hydrate_plan(plan: dict[str, Any]) -> dict[str, Any] | None:
    """Refresh saved meal metadata from stable IDs, including older plan files."""
    dataset = data_loader.load_dataset()
    try:
        weeks = plan.get("weeks", [])
        if not isinstance(weeks, list):
            return None
        day_groups = [plan.get("days", [])]
        day_groups.extend(week.get("days", []) for week in weeks)
        for days in day_groups:
            if not isinstance(days, list):
                return None
            for day in days:
                if not isinstance(day, dict) or not isinstance(day.get("meals"), list):
                    return None
                for meal in day["meals"]:
                    if not isinstance(meal, dict):
                        return None
                    slot = meal.get("slot")
                    if slot not in SLOTS:
                        return None
                    details = _meal_record(str(meal["meal_id"]), dataset)
                    details["slot"] = slot
                    meal.clear()
                    meal.update(details)
    except (AttributeError, KeyError, TypeError, ValueError):
        return None
    return plan


def _read_plan(plan_id: str) -> dict[str, Any] | None:
    if not plan_id or Path(plan_id).name != plan_id:
        return None
    path = STORE / f"{plan_id}.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(value, dict):
        return None
    return _hydrate_plan(value)


def _load_current() -> dict[str, Any] | None:
    try:
        plan_id = (STORE / "current.txt").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return _read_plan(plan_id)


app = FastAPI(title="Mess Menu API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/api/health", response_model=HealthResponse)
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "timezone": str(APP_TIMEZONE),
        "daily_cost_cap_inr": config.MAX_COST_PER_DAY,
        "minimum_daily_calories": config.MIN_CALORIES_PER_DAY,
        "maximum_daily_calories": config.MAX_CALORIES_PER_DAY,
        "calorie_target_kcal": config.DEFAULT_CALORIE_TARGET,
        "protein_target_g": config.DEFAULT_PROTEIN_TARGET,
        "minimum_weekly_differing_slots": config.MIN_DIFFERING_SLOTS,
    }


@app.get("/api/meals", response_model=MealListResponse)
def list_meals(query: str = "", cuisine: str | None = None, slot: str | None = None) -> dict[str, Any]:
    dataset = data_loader.load_dataset()
    rows = dataset
    if query.strip():
        rows = rows[rows["meal_name"].astype(str).str.contains(query.strip(), case=False, na=False)]
    if cuisine:
        rows = rows[rows["primary_cuisine"] == cuisine]
    if slot:
        if slot not in SLOTS:
            raise HTTPException(status_code=422, detail="Slot must be breakfast, lunch, or dinner.")
        rows = rows[rows["suitable_meal_types"].map(lambda value: slot in {item.strip() for item in str(value).split(";")})]
    return {"meals": [_meal_record(str(meal_id), dataset) for meal_id in rows["meal_id"]], "total": int(len(rows))}


@app.get("/api/meals/{meal_id}", response_model=MealResponse)
def get_meal(meal_id: str) -> dict[str, Any]:
    try:
        return _meal_record(meal_id, data_loader.load_dataset())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Meal {meal_id} was not found.") from exc


@app.get("/api/menu/current", response_model=MenuEnvelopeResponse)
def get_current_menu() -> dict[str, Any]:
    return {"plan": _load_current()}


@app.get("/api/menu/{plan_id}", response_model=MenuEnvelopeResponse)
def get_menu(plan_id: str) -> dict[str, Any]:
    result = _read_plan(plan_id)
    if result is None:
        raise HTTPException(status_code=404, detail="This menu could not be found.")
    return {"plan": result}


@app.get("/api/menu/{plan_id}/export", response_model=MenuResponse)
def export_menu(plan_id: str) -> dict[str, Any]:
    result = _read_plan(plan_id)
    if result is None:
        raise HTTPException(status_code=404, detail="This menu could not be found.")
    return result


@app.post("/api/menu/generate", response_model=MenuEnvelopeResponse)
def generate_menu(request: GenerateRequest) -> dict[str, Any]:
    settings = OptimizationConfig(
        population_size=request.population_size,
        generations=request.generations,
        seed=request.seed,
    )
    try:
        generated = _base_plan(request.horizon, request.seed, settings, data_loader.load_dataset())
        saved = _save_plan(generated)
        return {"plan": saved}
    except (ValueError, RuntimeError) as exc:
        logger.warning("Menu generation was not completed: %s", exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # Keep implementation details out of user-facing responses.
        logger.exception("Unexpected menu generation failure")
        raise HTTPException(status_code=500, detail="Menu generation failed unexpectedly. Please try again.") from exc
