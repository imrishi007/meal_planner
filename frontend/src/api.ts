import type { Horizon, Meal, MenuPlan } from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, { ...init, headers: { "Content-Type": "application/json", ...init?.headers } });
  } catch {
    throw new Error("The menu service is unavailable. Start the Python API and try again.");
  }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof body.detail === "string" ? body.detail : "Something went wrong. Please try again.";
    throw new Error(detail);
  }
  return body as T;
}

export const menuApi = {
  health: () => request<{
    status: string;
    timezone: string;
    daily_cost_cap_inr: number;
    minimum_daily_calories: number;
    maximum_daily_calories: number;
    calorie_target_kcal: number;
    protein_target_g: number;
    minimum_weekly_differing_slots: number;
  }>("/api/health"),
  meals: () => request<{ meals: Meal[]; total: number }>("/api/meals"),
  meal: (id: string) => request<Meal>(`/api/meals/${encodeURIComponent(id)}`),
  current: () => request<{ plan: MenuPlan | null }>("/api/menu/current"),
  generate: (horizon: Horizon, seed: number) => request<{ plan: MenuPlan }>("/api/menu/generate", {
    method: "POST",
    body: JSON.stringify({ horizon, seed, population_size: 40, generations: 12 }),
  }),
};

