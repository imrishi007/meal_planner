"""Fast tests for the presentation layer's dataset-backed helpers."""

import json
from pathlib import Path

import pandas as pd
import pytest

from hostel_optimizer import data_loader
from hostel_optimizer.monthly_scheduler import MonthlySchedulerConfig
from hostel_optimizer.optimization import OptimizationConfig
from hostel_optimizer.ui.data import REPO_ROOT, filter_meals, load_benchmark_artifacts, monthly_csv, monthly_json, validate_monthly_result, weekly_meal_rows
from hostel_optimizer.ui.images import image_tile, load_image_manifest, local_image_path


def test_meal_filters_use_dataset_fields_and_return_copy() -> None:
    dataset = data_loader.load_dataset()
    original_ids = dataset["meal_id"].tolist()
    result = filter_meals(dataset, query="idli", meal_type="Breakfast", cost_range=(0, 50))

    assert not result.empty
    assert result["meal_name"].str.contains("idli", case=False).all()
    assert result["suitable_meal_types"].str.contains("breakfast").all()
    assert dataset["meal_id"].tolist() == original_ids


def test_image_manifest_maps_stable_ids_and_falls_back_safely(tmp_path) -> None:
    manifest = load_image_manifest()
    assert image_tile("M041", manifest) == 0
    assert image_tile("M999", manifest) is None
    assert local_image_path("M041", manifest) is None

    custom = tmp_path / "manifest.json"
    custom.write_text(json.dumps({"images": {"M041": "../../outside.png"}, "tiles": {"M041": 12}}), encoding="utf-8")
    invalid = load_image_manifest(custom)
    assert image_tile("M041", invalid) is None
    assert local_image_path("M041", invalid) is None


def test_monthly_rows_and_exports_preserve_ordered_ids() -> None:
    dataset = data_loader.load_dataset()
    signature = dataset["meal_id"].astype(str).iloc[:21].tolist()
    week = {"week_number": 1, "signature": signature, "objectives": [80.0, .2, .5]}
    rows = weekly_meal_rows(week, dataset)
    assert len(rows) == 21
    assert [row["meal_id"] for row in rows] == signature
    assert rows[0]["slot"] == "breakfast"
    assert rows[-1]["day"] == "Sunday"

    result = {"has_schedule": True, "weeks": [week], "seed": 7}
    exported = monthly_csv(result, dataset).splitlines()
    assert len(exported) == 22
    assert signature[0] in exported[1]
    assert json.loads(monthly_json(result))["weeks"][0]["signature"] == signature


def test_benchmark_artifact_loader_handles_present_and_empty(tmp_path) -> None:
    assert load_benchmark_artifacts(tmp_path) is None
    (tmp_path / "benchmark_run_001_summary.csv").write_text("method,runs\nnsga2,1\n", encoding="utf-8")
    (tmp_path / "benchmark_run_001.json").write_text(json.dumps({"runs": [{"method": "nsga2"}]}), encoding="utf-8")

    loaded = load_benchmark_artifacts(tmp_path)
    assert loaded is not None
    assert loaded["summary"].iloc[0]["method"] == "nsga2"
    assert loaded["raw"]["runs"][0]["method"] == "nsga2"


def test_benchmark_artifact_loader_skips_incomplete_pair(tmp_path) -> None:
    (tmp_path / "benchmark_run_002_summary.csv").write_text("method,runs\nnsga2,1\n", encoding="utf-8")
    assert load_benchmark_artifacts(tmp_path) is None


def test_monthly_validation_rejects_missing_or_malformed_results() -> None:
    dataset = data_loader.load_dataset()
    assert not validate_monthly_result({"has_schedule": False}, dataset)[0]
    assert not validate_monthly_result({"has_schedule": True, "weeks": []}, dataset)[0]


def test_saved_monthly_plan_revalidates_against_backend() -> None:
    path = Path(REPO_ROOT) / "results" / "monthly_final.json"
    if not path.is_file():
        pytest.skip("No saved monthly result artifact is present")
    result = json.loads(path.read_text(encoding="utf-8"))
    assert validate_monthly_result(result, data_loader.load_dataset())[0]


def test_frontend_parameters_use_backend_validation() -> None:
    with pytest.raises(ValueError):
        OptimizationConfig(population_size=1)
    with pytest.raises(ValueError):
        MonthlySchedulerConfig(min_differing_slots=22)
