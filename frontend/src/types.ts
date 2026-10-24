export type Slot = "breakfast" | "lunch" | "dinner";
export type Horizon = "today" | "tomorrow" | "next_3_days" | "next_7_days" | "four_weeks";

export interface Meal {
  meal_id: string;
  meal_name: string;
  cuisine: string;
  meal_type: Slot;
  suitable_meal_types: Slot[];
  meal_components: string[];
  allergens: string;
  prep_time_minutes: number;
  kitchen_load: string;
  rating_count: number;
  cost: number;
  calories: number;
  protein: number;
  carbs: number;
  fat: number;
  rating: number;
  rating_source: string;
  is_veg: boolean;
}

export interface MenuDay {
  date: string;
  day_name: string;
  meals: (Meal & { slot: Slot })[];
  daily_cost: number;
  daily_calories: number;
  daily_protein: number;
}

export interface MenuWeek {
  week_number: number;
  signature: string[];
  objectives: number[];
  is_feasible: boolean;
  days: MenuDay[];
}

export interface MenuPlan {
  plan_id: string;
  created_at: string;
  horizon: Horizon;
  start_date: string;
  days?: MenuDay[];
  weeks?: MenuWeek[];
  pairwise_differences?: { week_a: number; week_b: number; different_slots: number }[];
  monthly_summary?: {
    monthly_total_cost: number;
    average_daily_cost: number;
    average_daily_calories: number;
    average_daily_protein: number;
    distinct_meal_count: number;
    maximum_meal_frequency: number;
    repeated_meal_occurrences: number;
  };
  weekly_objectives?: number[];
  weekly_signature?: string[];
  is_feasible: boolean;
  seed: number;
  settings: Record<string, unknown>;
}

