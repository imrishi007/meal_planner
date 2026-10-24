import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "./App";
import { MealImage } from "./MealImage";
import type { Meal } from "./types";

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

function meal(overrides: Partial<Meal> = {}): Meal {
  return {
    meal_id: "M001", meal_name: "Roti + Dal Tadka", cuisine: "North Indian", meal_type: "lunch",
    suitable_meal_types: ["lunch", "dinner"], meal_components: ["Roti", "Dal Tadka"], allergens: "wheat/gluten", prep_time_minutes: 28, kitchen_load: "medium", rating_count: 0, cost: 22, calories: 420, protein: 18, carbs: 52, fat: 14,
    rating: 4.2, rating_source: "synthetic", is_veg: true, ...overrides,
  };
}

function day(date: string) {
  return { date, day_name: "Monday", meals: ["breakfast", "lunch", "dinner"].map((slot) => ({ ...meal(), slot })), daily_cost: 70, daily_calories: 1850, daily_protein: 62 };
}

function ok(body: unknown) { return Promise.resolve(new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } })); }

describe("student menu application", () => {
  it("renders a real saved day and opens meal details", async () => {
    const today = new Date().toISOString().slice(0, 10);
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const path = String(input);
      if (path.endsWith("/api/health")) return ok({ status: "ok", timezone: "Asia/Kolkata", daily_cost_cap_inr: 80 });
      if (path.endsWith("/api/menu/current")) return ok({ plan: { plan_id: "plan-1", horizon: "today", days: [day(today)], is_feasible: true, seed: 42, settings: {} } });
      return ok({ meals: [], total: 0 });
    }));

    render(<App />);
    expect((await screen.findAllByText("Roti + Dal Tadka")).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: /view roti \+ dal tadka, breakfast/i }));
    expect(await screen.findByRole("dialog")).toHaveTextContent("North Indian · M001");
  });

  it("filters actual meal records by search", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const path = String(input);
      if (path.endsWith("/api/health")) return ok({ status: "ok", timezone: "Asia/Kolkata", daily_cost_cap_inr: 80 });
      if (path.endsWith("/api/menu/current")) return ok({ plan: null });
      return ok({ meals: [meal(), meal({ meal_id: "M002", meal_name: "Poha", meal_type: "breakfast", suitable_meal_types: ["breakfast"] })], total: 2 });
    }));

    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Meal library" }));
    expect(await screen.findByText("Poha")).toBeInTheDocument();
    fireEvent.change(screen.getByRole("textbox", { name: "Search meals" }), { target: { value: "poha" } });
    expect(screen.getByText("Poha")).toBeInTheDocument();
    expect(screen.queryByText("Roti + Dal Tadka")).not.toBeInTheDocument();
  });

  it("shows the generation choices and preserves an error state", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path.endsWith("/api/health")) return ok({ status: "ok", timezone: "Asia/Kolkata", daily_cost_cap_inr: 80 });
      if (path.endsWith("/api/menu/current")) {
        const date = new Date();
        const today = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
        return ok({ plan: { plan_id: "saved-menu", horizon: "today", days: [day(today)], is_feasible: true, seed: 1, settings: {} } });
      }
      if (path.endsWith("/api/menu/generate") && init?.method === "POST") return Promise.resolve(new Response(JSON.stringify({ detail: "No feasible menu was found." }), { status: 422 }));
      return ok({ meals: [], total: 0 });
    }));

    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: /plan meals/i }));
    expect(screen.getByRole("radio", { name: /next 3 days/i })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("radio", { name: /next 3 days/i }));
    fireEvent.click(screen.getByRole("button", { name: /generate my menu/i }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("No feasible menu was found."));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getAllByText("Roti + Dal Tadka").length).toBeGreaterThan(0);
  });

  it("replaces the empty state only after generation succeeds", async () => {
    const date = new Date();
    const today = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path.endsWith("/api/health")) return ok({ status: "ok", timezone: "Asia/Kolkata", daily_cost_cap_inr: 80 });
      if (path.endsWith("/api/menu/current")) return ok({ plan: null });
      if (path.endsWith("/api/menu/generate") && init?.method === "POST") return ok({ plan: { plan_id: "new-menu", created_at: new Date().toISOString(), horizon: "today", start_date: today, days: [day(today)], is_feasible: true, seed: 42, settings: {} } });
      return ok({ meals: [], total: 0 });
    }));

    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: /generate today's menu/i }));
    fireEvent.click(screen.getByRole("button", { name: /generate my menu/i }));

    expect(await screen.findByText("Your new menu is ready.")).toBeInTheDocument();
    expect((await screen.findAllByText("Roti + Dal Tadka")).length).toBeGreaterThan(0);
  });

  it("shows a designed fallback when the local sprite fails", () => {
    const { container } = render(<MealImage meal={meal()} />);
    fireEvent.error(container.querySelector(".image-preloader")!);
    expect(screen.getByText("Dish illustration")).toBeInTheDocument();
  });
});
