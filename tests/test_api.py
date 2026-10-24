"""Tests for the HTTP adapter around the existing optimizer."""

from fastapi.testclient import TestClient
import numpy as np

from hostel_optimizer import api


def test_json_safe_converts_numpy_and_tuple_values() -> None:
    assert api._json_safe({"values": (np.int64(7), np.float64(1.5))}) == {"values": [7, 1.5]}


def test_saved_menu_metadata_is_hydrated_by_stable_id() -> None:
    saved = {"days": [{"meals": [{"meal_id": "M001", "slot": "lunch"}]}], "weeks": []}

    hydrated = api._hydrate_plan(saved)

    assert hydrated is not None
    meal = hydrated["days"][0]["meals"][0]
    assert meal["meal_id"] == "M001"
    assert meal["meal_name"]
    assert meal["meal_components"]
    assert meal["slot"] == "lunch"


def test_health_and_meal_library_use_real_dataset() -> None:
    client = TestClient(api.app)
    health = client.get("/api/health")
    meals = client.get("/api/meals")

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert health.json()["daily_cost_cap_inr"] == 80
    assert meals.status_code == 200
    assert meals.json()["total"] == 200
    assert meals.json()["meals"][0]["meal_id"]


def test_meal_detail_and_unknown_id() -> None:
    client = TestClient(api.app)

    response = client.get("/api/meals/M001")
    assert response.status_code == 200
    assert response.json()["meal_id"] == "M001"
    assert response.json()["cost"] == 22
    assert client.get("/api/meals/M999").status_code == 404


def test_menu_generation_saves_successful_result_and_keeps_history(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(api, "STORE", tmp_path)
    monkeypatch.setattr(api, "_base_plan", lambda horizon, seed, settings, dataset: {
        "horizon": horizon,
        "start_date": "2026-10-23",
        "seed": seed,
        "is_feasible": True,
        "days": [],
        "settings": {"population_size": settings.population_size},
    })
    client = TestClient(api.app)

    first = client.post("/api/menu/generate", json={"horizon": "tomorrow", "seed": 73, "population_size": 4, "generations": 1})
    second = client.post("/api/menu/generate", json={"horizon": "today", "seed": 74, "population_size": 4, "generations": 1})

    assert first.status_code == second.status_code == 200
    first_plan = first.json()["plan"]
    second_plan = second.json()["plan"]
    assert first_plan["plan_id"] != second_plan["plan_id"]
    assert client.get(f"/api/menu/{first_plan['plan_id']}").json()["plan"] == first_plan
    assert client.get("/api/menu/current").json()["plan"] == second_plan
    assert len(list(tmp_path.glob("*.json"))) == 2


def test_menu_generation_validates_horizon_and_parameters() -> None:
    client = TestClient(api.app)

    invalid_horizon = client.post("/api/menu/generate", json={"horizon": "month"})
    invalid_population = client.post("/api/menu/generate", json={"horizon": "today", "population_size": 2})

    assert invalid_horizon.status_code == 422
    assert invalid_population.status_code == 422


def test_generation_failure_does_not_replace_existing_plan(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(api, "STORE", tmp_path)
    monkeypatch.setattr(api, "_base_plan", lambda *args: {"horizon": "today", "start_date": "2026-10-22", "seed": 1, "is_feasible": True, "settings": {}})
    client = TestClient(api.app)
    existing = client.post("/api/menu/generate", json={"horizon": "today"}).json()["plan"]
    monkeypatch.setattr(api, "_base_plan", lambda *args: (_ for _ in ()).throw(RuntimeError("No feasible weekly menu was found.")))

    response = client.post("/api/menu/generate", json={"horizon": "four_weeks"})

    assert response.status_code == 422
    assert client.get("/api/menu/current").json()["plan"] == existing
