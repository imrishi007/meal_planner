# React Student Interface

Phase 7 adds a small React/TypeScript/Vite application while preserving the
Python optimizer and legacy Streamlit research interface.

## Run locally

Install Python dependencies from the repository root and JavaScript
dependencies from `frontend/`:

```powershell
python -m pip install -e ".[dev]"
cd frontend
npm install
```

Start each process in its own terminal, from the repository root:

```powershell
python -m uvicorn hostel_optimizer.api:app --app-dir src --reload --host 127.0.0.1 --port 8000
```

```powershell
cd frontend
npm run dev
```

Visit the local URL Vite prints (normally `http://127.0.0.1:5173`). Its `/api`
proxy forwards requests to FastAPI at port 8000. The API uses `Asia/Kolkata`
as its planning timezone by default (`HOSTEL_MENU_TIMEZONE` can override it).
The browser uses its local date when highlighting today.

## What the app does

- Home shows today's saved meals when present, otherwise a clear no-menu state.
- Menu browses saved days and four-week plans by week and day.
- Meal Library searches all 200 records by name, cuisine, and suitable slot.
- Generation supports today, tomorrow, three days, seven days, or four weeks.
  Short horizons select days from an actual feasible NSGA-II weekly result;
  each selected day inherits that week's daily constraints. Four weeks use the
  existing monthly scheduler and its minimum seven-slot diversity rule.
- A failed generation leaves the previous saved menu unchanged.

Generated plans are atomically stored in `data/generated_plans/` as one JSON
file per plan with a current-plan pointer. This is local state, not a
multi-user production database. Do not share this writable store between
multiple instances without replacing the persistence adapter.

## API

- `GET /api/health` — status and planning timezone.
- `GET /api/meals` — dataset-backed meal list, optionally filtered by
  `query`, `cuisine`, and `slot`.
- `GET /api/meals/{meal_id}` — stable meal-ID lookup.
- `GET /api/menu/current` — saved plan or `null` when none exists.
- `POST /api/menu/generate` — a supported horizon and bounded seed/population/
  generation settings.
- `GET /api/menu/{plan_id}` and `/export` — retrieve a saved plan.

The API calls the existing evaluator, NSGA-II optimizer, and monthly scheduler;
it does not port their logic to TypeScript. Existing constraints remain
unchanged: 1,500–3,000 kcal/day and ₹80/day, plus vegetarian, slot, repetition,
and monthly diversity rules. The 2,000 kcal objective target is a soft target,
not the hard lower bound. A feasible day near 1,500 kcal can therefore remain
below the optimization target.

## Images

The existing local sprite has nine illustrative tiles mapped to stable meal IDs
in `data/meal_images.json`. Those mappings are reused. Other meal IDs receive a
slot-appropriate representative tile, visibly labelled “Illustrative”; images
are not exact meal or hostel-preparation photographs. A styled utensil fallback
appears when the local asset cannot load. Vite serves a copy of the sprite from
`frontend/public/meal-images/`. To add a dish image, add a properly licensed
local image, map its stable ID in the manifest, and verify its crop in the
reusable image component. Never add image metadata to the authoritative CSV.

Nutrition is estimated and not independently verified; ratings are synthetic.
Neither imagery nor a feasible result establishes a clinically validated diet.

## Test and build

```powershell
python -m pytest -q
cd frontend
npm test
npm run build
```

For production, serve `frontend/dist/` as static files and route the same-origin
`/api` path to FastAPI via a reverse proxy; the development proxy is not a
production deployment. The legacy interface remains available via
`streamlit run app.py`. This academic prototype does not include production API
hosting.
