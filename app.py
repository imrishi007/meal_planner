"""Streamlit application entry point for the Hostel Mess Menu Optimizer."""

from __future__ import annotations

import html
import json
import logging
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from hostel_optimizer import config, data_loader  # noqa: E402
from hostel_optimizer.benchmarking import BaselineConfig  # noqa: E402
from hostel_optimizer.experiments import ExperimentConfig, run_benchmarks, save_benchmark_results  # noqa: E402
from hostel_optimizer.monthly_scheduler import MonthlySchedulerConfig, build_weekly_candidate_pool, schedule_monthly_menu  # noqa: E402
from hostel_optimizer.optimization import OptimizationConfig, optimize_weekly_menus  # noqa: E402
from hostel_optimizer.ui.data import (  # noqa: E402
    DATASET_PATH,
    filter_meals,
    load_benchmark_artifacts,
    monthly_csv,
    monthly_json,
    weekly_daily_totals,
    weekly_meal_rows,
    validate_monthly_result,
)
from hostel_optimizer.ui.images import image_tile, load_image_manifest, local_image_path  # noqa: E402

LOGGER = logging.getLogger("hostel_optimizer.ui")


st.set_page_config(page_title="Mess Menu Optimizer", page_icon=None, layout="wide", initial_sidebar_state="expanded")


@st.cache_data(show_spinner="Loading meal library…")
def cached_dataset() -> pd.DataFrame:
    """Cache only the validated, immutable source dataset."""
    return data_loader.load_dataset(DATASET_PATH)


@st.cache_data
def cached_manifest() -> dict:
    return load_image_manifest()


def apply_theme() -> None:
    css_path = ROOT / "src" / "hostel_optimizer" / "ui" / "theme.css"
    css = css_path.read_text(encoding="utf-8") if css_path.is_file() else ""
    sprite_rel = cached_manifest().get("sprite")
    sprite_path = (ROOT / sprite_rel).resolve() if sprite_rel else None
    if sprite_path and sprite_path.is_file():
        import base64

        data_url = "data:image/png;base64," + base64.b64encode(sprite_path.read_bytes()).decode("ascii")
        css = css.replace("__SPRITE_URL__", data_url)
    else:
        css = css.replace("__SPRITE_URL__", "none")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def meal_photo(meal_id: str, meal_name: str, height: int | None = None) -> None:
    """Render an illustrative stable-ID image or a quiet fallback tile."""
    manifest = cached_manifest()
    local = local_image_path(meal_id, manifest)
    if local:
        st.image(str(local), caption=f"{meal_name} (illustrative image)", width="stretch")
        return
    tile = image_tile(meal_id, manifest)
    name = html.escape(meal_name, quote=True)
    if tile is None:
        initials = html.escape("".join(part[0] for part in meal_name.split()[:2]).upper() or "M")
        st.markdown(f'<div class="meal-photo fallback" role="img" aria-label="No image for {name}">{initials}</div>', unsafe_allow_html=True)
        return
    x = (tile % 3) * 50
    y = (tile // 3) * 50
    style = f"--tile-x:{x}%;--tile-y:{y}%;"
    size = f"height:{height}px;aspect-ratio:auto;" if height else ""
    st.markdown(f'<div class="meal-photo" style="{style}{size}" role="img" aria-label="Illustrative image of {name}"></div>', unsafe_allow_html=True)


def header(title: str, subtitle: str, eyebrow: str | None = None) -> None:
    if eyebrow:
        st.markdown(f'<div class="eyebrow">{html.escape(eyebrow)}</div>', unsafe_allow_html=True)
    st.title(title)
    st.markdown(f'<p class="page-subtitle">{html.escape(subtitle)}</p>', unsafe_allow_html=True)


def section(title: str) -> None:
    st.markdown(f'<div class="section-title">{html.escape(title)}</div>', unsafe_allow_html=True)


def metric(label: str, value: str, note: str = "") -> None:
    st.markdown(
        '<div class="metric-panel">'
        f'<div class="metric-label">{html.escape(label)}</div>'
        f'<div class="metric-value">{html.escape(value)}</div>'
        f'<div class="metric-note">{html.escape(note)}</div></div>',
        unsafe_allow_html=True,
    )


def load_saved_month(dataset: pd.DataFrame) -> dict | None:
    path = ROOT / "results" / "monthly_final.json"
    if not path.is_file():
        return None
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
        valid, _message = validate_monthly_result(result, dataset)
        if not valid:
            return None
        return result
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None


def get_ui_settings() -> dict:
    defaults = {"seed": 42, "population": 40, "generations": 12, "crossover": 0.9, "mutation": None, "min_difference": config.MIN_DIFFERING_SLOTS, "candidate_runs": 2}
    if "ui_settings" not in st.session_state:
        st.session_state.ui_settings = defaults
    return st.session_state.ui_settings


def make_optimizer_config(settings: dict, population: int | None = None, generations: int | None = None, seed: int | None = None) -> OptimizationConfig:
    return OptimizationConfig(
        population_size=population or int(settings["population"]),
        generations=generations or int(settings["generations"]),
        seed=int(settings["seed"] if seed is None else seed),
        crossover_probability=float(settings["crossover"]),
        mutation_probability=settings["mutation"],
    )


def make_monthly_config(settings: dict, seed: int | None = None) -> MonthlySchedulerConfig:
    return MonthlySchedulerConfig(
        min_differing_slots=int(settings["min_difference"]),
        candidate_runs=int(settings["candidate_runs"]),
        seed=int(settings["seed"] if seed is None else seed),
    )


def navigate_to_monthly() -> None:
    st.session_state.page = "Monthly Planner"


def queue_weekly_candidate(solution: dict) -> None:
    st.session_state.selected_weekly_solution = solution
    st.session_state.page = "Monthly Planner"


def show_meal_detail(meal: pd.Series) -> None:
    st.markdown("---")
    left, right = st.columns([1, 1.8])
    with left:
        meal_photo(str(meal["meal_id"]), str(meal["meal_name"]), 220)
    with right:
        st.subheader(str(meal["meal_name"]))
        st.caption(f"{meal['meal_id']} | {meal['primary_cuisine']}")
        st.write(f"Suitable slots: {meal['suitable_meal_types'].replace(';', ', ')}")
        a, b, c = st.columns(3)
        a.metric("Cost", f"₹{float(meal['cost_per_serving_inr']):.0f}")
        b.metric("Calories", f"{float(meal['calories_kcal']):.0f} kcal")
        c.metric("Protein", f"{float(meal['protein_g']):.0f} g")
        st.caption(f"Rating {float(meal['student_rating']):.1f} ({meal['rating_source']}); ratings are synthetic in this dataset.")
        st.caption("Food imagery is representative and may not depict this exact recipe or hostel preparation.")


def render_overview(dataset: pd.DataFrame) -> None:
    result = st.session_state.get("monthly_result")
    header("A month planned with purpose", "Four weeks of feasible meals, balanced against cost, nutrition estimates, and variety.", "HOSTEL MESS MENU OPTIMIZER")
    if not result or not result.get("has_schedule"):
        st.info("No validated monthly plan is loaded yet. Generate one to explore the menu.")
        st.button("Open monthly planner", type="primary", key="overview_to_planner", on_click=navigate_to_monthly)
        return

    summary = result.get("monthly_summary", {})
    weeks = result["weeks"]
    totals = [weekly_daily_totals(week, dataset) for week in weeks]
    calories = [value for week in totals for value in week["daily_calories"]]
    protein = [value for week in totals for value in week["daily_protein"]]
    metrics = st.columns(6)
    values = [
        ("Monthly food cost", f"₹{summary['monthly_total_cost']:,.0f}", "84 meal servings"),
        ("Average per day", f"₹{summary['average_daily_cost']:.2f}", "21 day period"),
        ("Meals in rotation", str(summary["distinct_meal_count"]), "Distinct dataset IDs"),
        ("Feasible weeks", f"{sum(bool(w['is_feasible']) for w in weeks)} / {len(weeks)}", "All hard rules checked"),
        ("Mean daily energy", f"{np.mean(calories):,.0f} kcal", "Estimated meal totals"),
        ("Mean daily protein", f"{np.mean(protein):.1f} g", "Estimated meal totals"),
    ]
    for column, item in zip(metrics, values):
        with column:
            metric(*item)
    section("What the month looks like")
    left, right = st.columns([1.3, 1])
    with left:
        costs = [sum(weekly_daily_totals(week, dataset)["daily_cost"]) for week in weeks]
        fig = px.bar(x=[f"Week {i}" for i in range(1, len(costs) + 1)], y=costs, labels={"x": "Plan week", "y": "Food cost (₹)"}, color_discrete_sequence=["#2D63C8"])
        fig.update_layout(title="Weekly cost", margin=dict(l=10, r=10, t=48, b=10), plot_bgcolor="white", paper_bgcolor="white", showlegend=False)
        fig.update_yaxes(gridcolor="#E8EEF2", rangemode="tozero")
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    with right:
        rows = [row for week in weeks for row in weekly_meal_rows(week, dataset)]
        cuisine_counts = Counter(row["cuisine"] for row in rows)
        fig = px.pie(names=list(cuisine_counts), values=list(cuisine_counts.values()), hole=.62, color_discrete_sequence=["#2D63C8", "#16806F", "#82A7D5", "#A7C5B8", "#E3B66C", "#8D9DAA"])
        fig.update_layout(title="Meals by cuisine", margin=dict(l=10, r=10, t=48, b=10), paper_bgcolor="white", legend_title="Cuisine")
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    weekly_calories = [float(np.mean(item["daily_calories"])) for item in totals]
    weekly_protein = [float(np.mean(item["daily_protein"])) for item in totals]
    nutrition_fig = make_subplots(specs=[[{"secondary_y": True}]])
    week_labels = [f"Week {i}" for i in range(1, len(weeks) + 1)]
    nutrition_fig.add_trace(go.Bar(x=week_labels, y=weekly_calories, name="Mean calories/day", marker_color="#2D63C8"), secondary_y=False)
    nutrition_fig.add_trace(go.Scatter(x=week_labels, y=weekly_protein, name="Mean protein/day", mode="lines+markers", line={"color": "#16806F", "width": 3}), secondary_y=True)
    nutrition_fig.update_layout(title="Estimated nutrition by week", paper_bgcolor="white", plot_bgcolor="white", margin=dict(l=10, r=10, t=48, b=10), legend=dict(orientation="h", y=-.2))
    nutrition_fig.update_yaxes(title_text="Mean energy (kcal/day)", gridcolor="#E8EEF2", secondary_y=False)
    nutrition_fig.update_yaxes(title_text="Mean protein (g/day)", showgrid=False, secondary_y=True)
    st.plotly_chart(nutrition_fig, width="stretch", config={"displayModeBar": False})
    section("A few dishes in the rotation")
    featured_ids = list(dict.fromkeys(row["meal_id"] for row in [*weekly_meal_rows(weeks[0], dataset), *weekly_meal_rows(weeks[-1], dataset)]))[:4]
    cols = st.columns(4)
    meal_by_id = dataset.set_index(dataset["meal_id"].astype(str), drop=False)
    for column, meal_id in zip(cols, featured_ids):
        meal = meal_by_id.loc[meal_id]
        with column:
            meal_photo(meal_id, str(meal["meal_name"]))
            st.markdown(f'<div class="meal-name">{html.escape(str(meal["meal_name"]))}</div>', unsafe_allow_html=True)
            st.caption(f"₹{float(meal['cost_per_serving_inr']):.0f} | {float(meal['calories_kcal']):.0f} kcal | {float(meal['protein_g']):.0f} g protein")
    st.caption("Images are illustrative representations, not photographs of the exact hostel preparation.")


def render_monthly_planner(dataset: pd.DataFrame) -> None:
    settings = get_ui_settings()
    result = st.session_state.get("monthly_result")
    header("Monthly planner", "Inspect the full four-week rotation, compare weeks, and export the current plan.")
    with st.expander("Plan generation settings", expanded=False):
        left, mid, right = st.columns(3)
        seed = left.number_input("Random seed", min_value=0, max_value=2_000_000_000, value=int(settings["seed"]), key="month_seed")
        pop = mid.number_input("Population per search", min_value=10, max_value=200, value=int(settings["population"]), step=10, key="month_population")
        generations = right.number_input("Generations per search", min_value=1, max_value=200, value=int(settings["generations"]), step=1, key="month_generations")
        left, mid, right = st.columns(3)
        runs = left.number_input("Seeded candidate searches", min_value=1, max_value=8, value=int(settings["candidate_runs"]), key="month_runs", help="More independent searches may increase candidate diversity and runtime.")
        threshold = mid.number_input("Minimum differing slots", min_value=0, max_value=21, value=int(settings["min_difference"]), key="month_difference", help="Every pair of selected weeks must differ in at least this many of 21 positions.")
        right.caption(f"Daily cost cap: ₹{config.MAX_COST_PER_DAY:.0f}. Feasibility rules are not relaxed.")
        generate = st.button("Generate a new monthly plan", type="primary", key="generate_month")
        if generate:
            current = {**settings, "seed": int(seed), "population": int(pop), "generations": int(generations), "candidate_runs": int(runs), "min_difference": int(threshold)}
            try:
                with st.spinner("Searching for feasible weekly candidates and a diverse monthly combination…"):
                    monthly_config = make_monthly_config(current)
                    optimizer_config = make_optimizer_config(current)
                    selected_candidate = st.session_state.get("selected_weekly_solution")
                    if selected_candidate:
                        candidate_pool = build_weekly_candidate_pool(monthly_config, optimizer_config, dataset)["candidates"]
                        candidate_pool.append(selected_candidate)
                        generated = schedule_monthly_menu(candidate_pool, monthly_config, optimizer_config, dataset)
                    else:
                        generated = schedule_monthly_menu(
                            scheduler_config=monthly_config,
                            optimization_config=optimizer_config,
                            dataset=dataset,
                        )
                valid, validation_message = validate_monthly_result(generated, dataset)
                if valid:
                    st.session_state.monthly_result = generated
                    st.session_state.ui_settings = current
                    st.success(validation_message)
                    st.rerun()
                if generated.get("has_schedule"):
                    st.error(f"The returned plan failed validation: {validation_message}")
                else:
                    st.error(generated.get("message", validation_message))
                st.json(generated.get("diagnostics", {}))
            except Exception as exc:
                LOGGER.exception("Monthly schedule generation failed")
                st.error(f"Monthly plan generation failed ({type(exc).__name__}). The previous plan is unchanged.")
    if not result or not result.get("has_schedule"):
        st.info("No valid four-week plan is available. Generate one above; the diversity threshold will not be relaxed.")
        return

    summary = result.get("monthly_summary", {})
    minimum = int(result.get("settings", {}).get("min_differing_slots", config.MIN_DIFFERING_SLOTS))
    stats = st.columns(5)
    for col, item in zip(stats, [
        ("Month total", f"₹{summary.get('monthly_total_cost', 0):,.0f}", "84 meal servings"),
        ("Daily average", f"₹{summary.get('average_daily_cost', 0):.2f}", "cost per student"),
        ("Distinct meals", str(summary.get("distinct_meal_count", 0)), "out of 200 records"),
        ("Highest repeat", str(summary.get("maximum_meal_frequency", 0)), "servings in 4 weeks"),
        ("Week difference", f"≥ {minimum} / 21", "every pair must comply"),
    ]):
        with col:
            metric(*item)
    json_bytes = monthly_json(result).encode("utf-8")
    csv_bytes = monthly_csv(result, dataset).encode("utf-8-sig")
    c1, c2 = st.columns([1, 5])
    c1.download_button("Download JSON", json_bytes, file_name="hostel_monthly_plan.json", mime="application/json", key="month_json")
    c2.download_button("Download CSV", csv_bytes, file_name="hostel_monthly_plan.csv", mime="text/csv", key="month_csv")

    view = st.radio("Plan view", ["Weekly detail", "Month at a glance"], horizontal=True, key="monthly_view")
    if view == "Month at a glance":
        month_rows = []
        for week in result["weeks"]:
            day = weekly_daily_totals(week, dataset)
            month_rows.append({
                "Week": f"Week {week['week_number']}",
                "Cost (₹)": round(sum(day["daily_cost"]), 2),
                "Mean kcal/day": round(float(np.mean(day["daily_calories"])), 1),
                "Mean protein/day (g)": round(float(np.mean(day["daily_protein"])), 1),
                "Feasible": "Yes" if week["is_feasible"] else "No",
                "Objectives (cost, nutrition, dissatisfaction)": ", ".join(f"{x:.3f}" for x in week.get("objectives", [])),
            })
        st.dataframe(pd.DataFrame(month_rows), hide_index=True, width="stretch")
        differences = []
        weekly_metrics = {row["Week"]: row for row in month_rows}
        for pair in result.get("pairwise_differences", []):
            left = weekly_metrics.get(f"Week {pair['week_a']}", {})
            right = weekly_metrics.get(f"Week {pair['week_b']}", {})
            differences.append({
                "Week pair": f"{pair['week_a']} vs {pair['week_b']}",
                "Different slots": pair["different_slots"],
                "Meets minimum": "Yes" if pair["different_slots"] >= minimum else "No",
                "Cost difference (₹/week)": round(abs(left.get("Cost (₹)", 0) - right.get("Cost (₹)", 0)), 2),
                "Energy difference (kcal/day)": round(abs(left.get("Mean kcal/day", 0) - right.get("Mean kcal/day", 0)), 1),
                "Protein difference (g/day)": round(abs(left.get("Mean protein/day (g)", 0) - right.get("Mean protein/day (g)", 0)), 1),
            })
        if differences:
            st.dataframe(pd.DataFrame(differences), hide_index=True, width="stretch")
        frequencies = summary.get("meal_frequencies", {})
        if frequencies:
            name_map = dataset.set_index(dataset["meal_id"].astype(str))["meal_name"].to_dict()
            top = sorted(frequencies.items(), key=lambda item: (-item[1], item[0]))[:12]
            fig = px.bar(x=[name_map.get(meal_id, meal_id) for meal_id, _ in top], y=[count for _, count in top], labels={"x": "Meal", "y": "Monthly servings"}, color_discrete_sequence=["#16806F"])
            fig.update_layout(title="Most frequent meals in this plan", margin=dict(l=10, r=10, t=45, b=100), paper_bgcolor="white")
            fig.update_xaxes(tickangle=-35)
            st.plotly_chart(fig, width="stretch")
        return

    tabs = st.tabs([f"Week {i}" for i in range(1, len(result["weeks"]) + 1)])
    for tab, week in zip(tabs, result["weeks"]):
        with tab:
            rows = weekly_meal_rows(week, dataset)
            daily = weekly_daily_totals(week, dataset)
            section(f"Week {week['week_number']} objectives")
            objective_names = ["Avg daily cost", "Nutrition deviation", "Dissatisfaction"]
            cols = st.columns(3)
            for col, label, value in zip(cols, objective_names, week.get("objectives", [])):
                with col:
                    metric(label, f"{float(value):.3f}", "lower is preferred; trade-offs differ")
            for day_index, day_name in enumerate(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]):
                day_rows = rows[day_index * 3:day_index * 3 + 3]
                with st.container(border=True):
                    day_header, *meal_cols = st.columns([.72, 1, 1, 1])
                    with day_header:
                        st.markdown(f"**{day_name}**")
                        st.caption(f"₹{daily['daily_cost'][day_index]:.0f} daily")
                        st.caption(f"{daily['daily_calories'][day_index]:.0f} kcal")
                        st.caption(f"{daily['daily_protein'][day_index]:.0f} g protein")
                    for col, row in zip(meal_cols, day_rows):
                        with col:
                            meal_photo(row["meal_id"], row["meal_name"], 115)
                            st.markdown(f'<div class="slot-label">{html.escape(row["slot"])}</div><div class="meal-name">{html.escape(row["meal_name"])}</div>', unsafe_allow_html=True)
                            st.caption(f"{row['meal_id']} | ₹{row['cost']:.0f} | {row['calories']:.0f} kcal | {row['protein']:.0f} g protein")
            if week.get("constraint_violations"):
                st.warning("This saved week contains a constraint report. Review the optimizer diagnostics.")
            else:
                st.markdown("**Feasibility:** <span class='status-good'>All configured weekly constraints pass</span>", unsafe_allow_html=True)


def render_optimization_lab(dataset: pd.DataFrame) -> None:
    settings = get_ui_settings()
    header("Optimization lab", "Run the existing NSGA-II engine and inspect its feasible trade-off set.")
    st.info("The three objectives are minimized. No point is universally best: lower cost, closer nutrition estimates, and lower dissatisfaction can conflict.")
    with st.form("optimizer_form"):
        a, b, c = st.columns(3)
        population = a.number_input("Population size", 10, 300, int(settings["population"]), step=10)
        generations = b.number_input("Generations", 1, 300, int(settings["generations"]))
        seed = c.number_input("Random seed", 0, 2_000_000_000, int(settings["seed"]))
        a, b, c = st.columns(3)
        crossover = a.slider("Crossover probability", 0.0, 1.0, float(settings["crossover"]), .05)
        use_default_mutation = b.checkbox("Use optimizer mutation default", value=settings["mutation"] is None, help="The backend default is used when enabled.")
        mutation = c.slider("Mutation probability", 0.0, 1.0, float(settings["mutation"] or .05), .01, disabled=use_default_mutation)
        run_clicked = st.form_submit_button("Run NSGA-II", type="primary")
    if run_clicked:
        current = {**settings, "seed": int(seed), "population": int(population), "generations": int(generations), "crossover": float(crossover), "mutation": None if use_default_mutation else float(mutation)}
        try:
            started = time.perf_counter()
            with st.spinner(f"Evaluating {int(population)} candidates across {int(generations)} generations…"):
                result = optimize_weekly_menus(make_optimizer_config(current), dataset=dataset, seed=int(seed))
            result["runtime_seconds_ui"] = time.perf_counter() - started
            st.session_state.optimization_result = result
            st.session_state.ui_settings = current
        except Exception as exc:
            LOGGER.exception("NSGA-II optimization failed")
            st.error(f"Optimization could not complete ({type(exc).__name__}). The existing results are unchanged.")
            return
    result = st.session_state.get("optimization_result")
    if not result:
        st.info("Set a run budget above and start NSGA-II to populate this workspace.")
        return
    diagnostics = result.get("diagnostics", {})
    cols = st.columns(4)
    for col, item in zip(cols, [
        ("Runtime", f"{result.get('runtime_seconds_ui', 0):.2f} s", "this browser-triggered run"),
        ("Feasible evaluations", str(diagnostics.get("evaluated_feasible_candidates", 0)), "of evaluated chromosomes"),
        ("Pareto schedules", str(len(result.get("pareto_solutions", []))), "feasible and non-dominated"),
        ("Unique schedules", str(diagnostics.get("distinct_feasible_signatures", 0)), "in final population"),
    ]):
        with col:
            metric(*item)
    st.caption(result.get("message", ""))
    solutions = result.get("pareto_solutions", [])
    if not solutions:
        st.warning("No feasible solutions were returned. The engine did not relax any constraints.")
        st.json({key: diagnostics.get(key) for key in ("eligible_options_per_slot", "daily_feasible_options", "best_constraint_violation_per_generation")})
        return
    axis_defs = {"Average daily cost (₹)": 0, "Nutrition deviation (normalized)": 1, "Dissatisfaction": 2}
    x_name = st.selectbox("Horizontal objective", list(axis_defs), index=0, key="pareto_x")
    y_name = st.selectbox("Vertical objective", list(axis_defs), index=1, key="pareto_y")
    x_index, y_index = axis_defs[x_name], axis_defs[y_name]
    plot_data = pd.DataFrame([{"solution": i + 1, "f1": sol["objectives"][0], "f2": sol["objectives"][1], "f3": sol["objectives"][2], "signature": " / ".join(sol["signature"])} for i, sol in enumerate(solutions)])
    objective_keys = ["f1", "f2", "f3"]
    fig = px.scatter(plot_data, x=objective_keys[x_index], y=objective_keys[y_index], hover_data=["solution", "f1", "f2", "f3"], custom_data=["solution"], color_discrete_sequence=["#2D63C8"])
    fig.update_traces(marker={"size": 11, "line": {"width": 1, "color": "white"}})
    fig.update_layout(xaxis_title=x_name, yaxis_title=y_name, title="Feasible approximate Pareto front", paper_bgcolor="white", plot_bgcolor="white", margin=dict(l=10, r=10, t=48, b=10))
    fig.update_xaxes(gridcolor="#E8EEF2")
    fig.update_yaxes(gridcolor="#E8EEF2")
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key="pareto_plot")
    labels = [f"Solution {i + 1} | ₹{sol['objectives'][0]:.2f}/day | nutrition {sol['objectives'][1]:.3f} | dissatisfaction {sol['objectives'][2]:.3f}" for i, sol in enumerate(solutions)]
    picked = st.selectbox("Inspect a feasible schedule", range(len(solutions)), format_func=lambda i: labels[i], key="pareto_solution_select")
    solution = solutions[int(picked)]
    st.markdown("**Objectives:** " + " | ".join(f"f{i + 1} {value:.4f}" for i, value in enumerate(solution["objectives"])))
    fake_week = {"signature": list(solution["signature"]), "chromosome": solution["chromosome"], "is_feasible": solution["is_feasible"], "objectives": solution["objectives"]}
    totals = weekly_daily_totals(fake_week, dataset)
    for day in range(config.DAYS):
        st.markdown(f"**{config.SLOT_ORDER[day * 3].split()[0]}:** ₹{totals['daily_cost'][day]:.0f}, {totals['daily_calories'][day]:.0f} kcal, {totals['daily_protein'][day]:.0f} g protein")
    with st.expander("Constraint and run diagnostics"):
        st.json(diagnostics)
    st.button(
        "Add this week to the monthly candidate pool",
        key="use_solution_month",
        help="The monthly scheduler will still enforce its full four-week feasibility and diversity rules.",
        on_click=queue_weekly_candidate,
        args=(solution,),
    )


def render_benchmarks(dataset: pd.DataFrame) -> None:
    header("Benchmark results", "Measured comparisons from saved experiments. Runs are not launched automatically.")
    artifacts = st.session_state.get("benchmark_artifacts") or load_benchmark_artifacts()
    with st.expander("Run a small benchmark", expanded=False):
        a, b, c = st.columns(3)
        seeds = a.number_input("Number of seeds", 1, 10, 1, help="Use 10 for a multi-seed benchmark; this can take time.")
        population = b.number_input("Population", 10, 100, 20, step=10)
        generations = c.number_input("Generations", 1, 100, 3)
        random_budget = st.number_input("Random feasible candidates per seed", 1, 500, 20)
        if st.button("Run benchmark", type="primary", key="run_benchmark"):
            try:
                with st.spinner("Running requested methods and recording measured outputs…"):
                    settings = ExperimentConfig(
                        seeds=tuple(range(int(seeds))),
                        optimization=OptimizationConfig(population_size=int(population), generations=int(generations), seed=0),
                        baselines=BaselineConfig(random_candidates=int(random_budget)),
                        save_plots=True,
                    )
                    measured = run_benchmarks(settings, dataset)
                    paths = save_benchmark_results(measured, str(ROOT / "results"), save_plots=True)
                    st.session_state.benchmark_artifacts = load_benchmark_artifacts()
                    st.session_state.benchmark_saved_paths = paths
                st.success("Benchmark finished and saved without overwriting earlier runs.")
                st.rerun()
            except Exception as exc:
                LOGGER.exception("Benchmark run failed")
                st.error(f"Benchmark could not complete ({type(exc).__name__}). Existing result files are unchanged.")
    if not artifacts:
        st.info("No complete benchmark artifacts were found. Run the benchmark above or use the documented CLI command.")
        return
    summary = artifacts["summary"].copy()
    raw = artifacts["raw"]
    runs = raw.get("runs", [])
    st.caption(f"Loaded `{artifacts['summary_path'].relative_to(ROOT)}` with {len(runs)} recorded per-run observations.")
    successful = [run for run in runs if not run.get("failed")]
    cols = st.columns(4)
    method_count = summary["method"].nunique() if not summary.empty else 0
    seeds_count = len(raw.get("configuration", {}).get("seeds", []))
    for col, item in zip(cols, [
        ("Methods", str(method_count), "same evaluator and dataset"),
        ("Seed runs", str(seeds_count), "saved experiment configuration"),
        ("Successful runs", f"{sum(not run.get('failed') for run in runs)} / {len(runs)}", "failed runs retained"),
        ("Dataset rows", str(raw.get("dataset_rows", "—")), "artifact metadata"),
    ]):
        with col:
            metric(*item)
    st.dataframe(summary, hide_index=True, width="stretch")
    if not successful:
        st.warning("The saved benchmark contains no successful runs. Review recorded error messages below.")
    else:
        left, right = st.columns(2)
        runtime_frame = pd.DataFrame([{"Method": run["method"], "Runtime (s)": run["runtime_seconds"], "Seed": run["seed"]} for run in successful if run.get("runtime_seconds") is not None])
        with left:
            if not runtime_frame.empty:
                fig = px.box(runtime_frame, x="Method", y="Runtime (s)", points="all", color="Method", color_discrete_sequence=["#2D63C8", "#16806F", "#86A9D4"])
                fig.update_layout(title="Runtime by seed (recorded runs)", showlegend=False, paper_bgcolor="white", plot_bgcolor="white")
                st.plotly_chart(fig, width="stretch")
        with right:
            feasibility_frame = pd.DataFrame([{"Method": run["method"], "Feasible / generated (%)": 100 * run["feasible_candidates"] / run["generated_candidates"] if run["generated_candidates"] else 0, "Seed": run["seed"]} for run in successful])
            if not feasibility_frame.empty:
                fig = px.box(feasibility_frame, x="Method", y="Feasible / generated (%)", points="all", color="Method", color_discrete_sequence=["#2D63C8", "#16806F", "#86A9D4"])
                fig.update_layout(title="Feasible candidate proportion", showlegend=False, paper_bgcolor="white", plot_bgcolor="white")
                st.plotly_chart(fig, width="stretch")
        objective_rows = []
        pareto_rows = []
        for run in successful:
            daily = (run.get("metrics", {}).get("daily_summary") or {})
            if daily.get("mean_daily_cost_inr") is not None:
                objective_rows.append({"Method": run["method"], "Mean daily cost (₹)": daily["mean_daily_cost_inr"], "Seed": run["seed"]})
            for sol in run.get("solutions", []):
                obj = sol.get("objectives", [])
                if len(obj) == 3:
                    pareto_rows.append({"Method": run["method"], "f1 cost (₹/day)": obj[0], "f2 nutrition deviation": obj[1], "f3 dissatisfaction": obj[2], "Seed": run["seed"]})
        left, right = st.columns(2)
        with left:
            if objective_rows:
                fig = px.box(pd.DataFrame(objective_rows), x="Method", y="Mean daily cost (₹)", points="all", color="Method", color_discrete_sequence=["#2D63C8", "#16806F", "#86A9D4"])
                fig.update_layout(title="Objective quality across runs", showlegend=False, paper_bgcolor="white", plot_bgcolor="white")
                st.plotly_chart(fig, width="stretch")
        with right:
            if pareto_rows:
                fig = px.scatter(pd.DataFrame(pareto_rows), x="f1 cost (₹/day)", y="f2 nutrition deviation", color="Method", hover_data=["f3 dissatisfaction", "Seed"], color_discrete_sequence=["#2D63C8", "#16806F", "#86A9D4"])
                fig.update_layout(title="Recorded feasible candidates", paper_bgcolor="white", plot_bgcolor="white")
                st.plotly_chart(fig, width="stretch")
    failures = [run for run in runs if run.get("failed")]
    if failures:
        with st.expander(f"Failed runs ({len(failures)})"):
            st.dataframe(pd.DataFrame([{"Method": r.get("method"), "Seed": r.get("seed"), "Message": r.get("message")} for r in failures]), hide_index=True, width="stretch")
    st.warning("These measurements describe this dataset and experimental budget. They do not establish universal method superiority. Nutrition values are estimates; student ratings are synthetic.")


def render_meal_library(dataset: pd.DataFrame) -> None:
    header("Meal library", "Explore all dataset records. Browsing filters do not change optimizer eligibility or results.")
    a, b, c = st.columns([1.5, 1, 1])
    query = a.text_input("Search meal name", key="meal_query", placeholder="Try paneer, poha, dal…")
    cuisine = b.selectbox("Cuisine", ["All cuisines", *sorted(dataset["primary_cuisine"].astype(str).unique())])
    slot = c.selectbox("Suitable slot", ["All slots", "Breakfast", "Lunch", "Dinner"])
    a, b, c, d = st.columns(4)
    cost_range = a.slider("Cost range (₹)", float(dataset.cost_per_serving_inr.min()), float(dataset.cost_per_serving_inr.max()), (float(dataset.cost_per_serving_inr.min()), float(dataset.cost_per_serving_inr.max())))
    calorie_range = b.slider("Calories", float(dataset.calories_kcal.min()), float(dataset.calories_kcal.max()), (float(dataset.calories_kcal.min()), float(dataset.calories_kcal.max())))
    protein_range = c.slider("Protein (g)", float(dataset.protein_g.min()), float(dataset.protein_g.max()), (float(dataset.protein_g.min()), float(dataset.protein_g.max())))
    page_size = d.selectbox("Meals per page", [12, 24, 48], index=0)
    filtered = filter_meals(dataset, query=query, cuisine=cuisine, meal_type=slot, cost_range=cost_range, calorie_range=calorie_range, protein_range=protein_range)
    if filtered.empty:
        st.info("No meals match these filters. Widen a range or clear the search.")
        return
    page_count = max(1, int(np.ceil(len(filtered) / page_size)))
    if int(st.session_state.get("meal_page", 1)) > page_count:
        st.session_state.meal_page = 1
    page = st.number_input("Page", 1, page_count, 1, key="meal_page")
    start = (int(page) - 1) * page_size
    shown = filtered.iloc[start:start + page_size]
    st.caption(f"Showing {start + 1}–{start + len(shown)} of {len(filtered)} meals; dataset has {len(dataset)} unique IDs")
    rows = list(shown.iterrows())
    for offset in range(0, len(rows), 3):
        cols = st.columns(3)
        for col, (_, meal) in zip(cols, rows[offset:offset + 3]):
            with col:
                with st.container(border=True):
                    meal_photo(str(meal["meal_id"]), str(meal["meal_name"]))
                    st.markdown(f'<div class="meal-name">{html.escape(str(meal["meal_name"]))}</div>', unsafe_allow_html=True)
                    st.caption(f"{meal['meal_id']} | {meal['primary_cuisine']}")
                    st.write(f"₹{float(meal['cost_per_serving_inr']):.0f} | {float(meal['calories_kcal']):.0f} kcal | {float(meal['protein_g']):.0f} g protein")
                    st.caption(f"Suitable: {str(meal['suitable_meal_types']).replace(';', ', ')}")
    options = filtered["meal_id"].astype(str).tolist()
    inspect_id = st.selectbox("Inspect meal details", options, format_func=lambda meal_id: f"{meal_id} | {filtered.loc[filtered.meal_id.astype(str) == meal_id, 'meal_name'].iloc[0]}", key="inspect_meal")
    show_meal_detail(dataset.loc[dataset.meal_id.astype(str) == inspect_id].iloc[0])


def render_settings() -> None:
    settings = get_ui_settings()
    header("Settings", "These controls apply to this browser session only; they do not edit project configuration files.")
    st.markdown("#### Search and diversity")
    a, b, c = st.columns(3)
    seed = a.number_input("Default random seed", 0, 2_000_000_000, int(settings["seed"]), key="settings_seed")
    difference = b.number_input("Minimum weekly difference", 0, 21, int(settings["min_difference"]), help="Pairwise minimum out of 21 meal slots.", key="settings_difference")
    runs = c.number_input("Monthly candidate searches", 1, 8, int(settings["candidate_runs"]), key="settings_runs")
    st.markdown("#### NSGA-II budget")
    a, b, c, d = st.columns(4)
    population = a.number_input("Population size", 10, 300, int(settings["population"]), step=10, key="settings_population")
    generations = b.number_input("Generations", 1, 300, int(settings["generations"]), key="settings_generations")
    crossover = c.slider("Crossover probability", 0.0, 1.0, float(settings["crossover"]), .05, key="settings_crossover")
    mutation_default = d.checkbox("Default mutation", settings["mutation"] is None, key="settings_mutation_default")
    mutation = d.slider("Mutation probability", 0.0, 1.0, float(settings["mutation"] or .05), .01, disabled=mutation_default, key="settings_mutation")
    if st.button("Apply for this session", type="primary", key="apply_settings"):
        st.session_state.ui_settings = {"seed": int(seed), "population": int(population), "generations": int(generations), "crossover": float(crossover), "mutation": None if mutation_default else float(mutation), "min_difference": int(difference), "candidate_runs": int(runs)}
        st.success("Session settings applied. Existing plans and optimizer results remain unchanged until rerun.")
    st.markdown("#### Active feasibility configuration")
    constraints = pd.DataFrame([
        {"Rule": "Daily calorie bounds", "Active value": f"{config.MIN_CALORIES_PER_DAY:,.0f}–{config.MAX_CALORIES_PER_DAY:,.0f} kcal", "Editable here": "No"},
        {"Rule": "Daily cost cap", "Active value": f"₹{config.MAX_COST_PER_DAY:.0f}", "Editable here": "No"},
        {"Rule": "Vegetarian-only policy", "Active value": "On" if config.VEGETARIAN_ONLY else "Off", "Editable here": "No"},
        {"Rule": "Repetition window", "Active value": f"{config.REPETITION_WINDOW_DAYS} days", "Editable here": "No"},
        {"Rule": "Calorie objective target", "Active value": f"{config.DEFAULT_CALORIE_TARGET:,.0f} kcal/day", "Editable here": "No"},
        {"Rule": "Protein objective target", "Active value": f"{config.DEFAULT_PROTEIN_TARGET:.0f} g/day", "Editable here": "No"},
    ])
    st.dataframe(constraints, hide_index=True, width="stretch")
    st.caption("Feasibility and objective limits are module-level backend constants. This UI does not alter them, avoiding a display/evaluator mismatch. The ₹80 daily cap remains unchanged.")


def render_about(dataset: pd.DataFrame) -> None:
    header("About the project", "A decision-support prototype for building a varied hostel menu under explicit constraints.")
    st.markdown("### The problem")
    st.write("A week contains 21 meal choices. This project searches for menus that balance average daily meal cost, estimated calorie and protein deviation, and a dissatisfaction score while respecting slot eligibility, daily calorie and cost limits, vegetarian policy, and the existing repetition rule.")
    st.markdown("### Why several answers")
    st.write("NSGA-II explores trade-offs and returns an approximate Pareto set. A menu is non-dominated when no other returned menu is at least as good on every objective and better on one. A cheaper menu may be nutritionally farther from the configured targets, so the project does not label one schedule the single best answer.")
    st.markdown("### From week to month")
    st.write(f"The monthly layer selects four independently feasible weekly candidates and requires each pair to differ in at least {config.MIN_DIFFERING_SLOTS} of 21 slots by default. It also reports repeated-meal frequencies; the threshold is a design choice, not a scientifically established optimum.")
    st.markdown("### Technology")
    st.write("Python, pandas, NumPy, pymoo/NSGA-II, Streamlit, Plotly, and pytest. The UI calls the existing weekly optimizer, Phase 2 evaluator, experiment runner, and monthly scheduler; it does not reimplement their scoring rules.")
    st.warning("Nutrition values are estimates and have not been independently verified. Meal ratings are synthetic, not real student feedback. Benchmark results are specific to this dataset and computational budget. Images are representative illustrations, not photographs of the exact recipe or hostel preparation. This is not a clinically validated nutrition tool.")
    st.caption(f"Meal library source: {DATASET_PATH.relative_to(ROOT)}; {len(dataset)} records; {dataset.meal_id.nunique()} unique meal IDs.")


def main() -> None:
    apply_theme()
    try:
        dataset = cached_dataset()
    except Exception as exc:
        st.error(f"The validated meal dataset could not be loaded from `{DATASET_PATH.relative_to(ROOT)}`: {exc}")
        st.stop()
    if "monthly_result" not in st.session_state:
        st.session_state.monthly_result = load_saved_month(dataset)
    get_ui_settings()
    with st.sidebar:
        st.markdown('<div class="sidebar-brand">Mess Menu<br>Optimizer</div>', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-caption">Plan a month with measurable trade-offs.</div>', unsafe_allow_html=True)
        page_names = ["Overview", "Monthly Planner", "Optimization Lab", "Benchmark Results", "Meal Library", "Settings", "About"]
        current = st.session_state.get("page", "Overview")
        if current not in page_names:
            current = "Overview"
        page = st.radio("Navigation", page_names, index=page_names.index(current), label_visibility="collapsed", key="page")
        st.markdown("---")
        st.markdown('<div class="sidebar-caption">200 meals<br>21 weekly slots<br>Cost, nutrition estimates, variety</div>', unsafe_allow_html=True)
    if page == "Overview":
        render_overview(dataset)
    elif page == "Monthly Planner":
        render_monthly_planner(dataset)
    elif page == "Optimization Lab":
        render_optimization_lab(dataset)
    elif page == "Benchmark Results":
        render_benchmarks(dataset)
    elif page == "Meal Library":
        render_meal_library(dataset)
    elif page == "Settings":
        render_settings()
    else:
        render_about(dataset)


if __name__ == "__main__":
    main()
