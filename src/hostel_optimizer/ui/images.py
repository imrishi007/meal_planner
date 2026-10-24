"""Stable-ID image manifest lookup and safe local image paths."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .data import REPO_ROOT

MANIFEST_PATH = REPO_ROOT / "data" / "meal_images.json"


def load_image_manifest(path: Path | str = MANIFEST_PATH) -> dict[str, Any]:
    """Load image mappings; a missing manifest is a supported empty state."""
    manifest_path = Path(path)
    if not manifest_path.is_file():
        return {"sprite": None, "tiles": {}, "images": {}}
    try:
        content = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"sprite": None, "tiles": {}, "images": {}}
    return {
        "sprite": content.get("sprite"),
        "tiles": content.get("tiles", {}),
        "images": content.get("images", {}),
    }


def image_tile(meal_id: str, manifest: dict[str, Any]) -> int | None:
    """Resolve an explicit stable meal-ID mapping to a 3×3 sprite tile."""
    tile = manifest.get("tiles", {}).get(str(meal_id))
    return tile if isinstance(tile, int) and 0 <= tile < 9 else None


def local_image_path(meal_id: str, manifest: dict[str, Any]) -> Path | None:
    """Resolve an optional per-meal local image without allowing path escape."""
    relative = manifest.get("images", {}).get(str(meal_id))
    if not isinstance(relative, str) or not relative.strip():
        return None
    candidate = (REPO_ROOT / relative).resolve()
    try:
        candidate.relative_to(REPO_ROOT.resolve())
    except ValueError:
        return None
    return candidate if candidate.is_file() else None

