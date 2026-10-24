import type { Meal } from "./types";
import imageManifest from "../../data/meal_images.json";

const spriteUrl = "/meal-images/indian_vegetarian_sprite.png";
const mappedTiles = imageManifest.tiles as Record<string, number>;

export function resolveMealImage(meal: Pick<Meal, "meal_id" | "meal_name" | "meal_type">) {
  const tile = mappedTiles[meal.meal_id] ?? (meal.meal_type === "breakfast" ? 2 : 8);
  return {
    src: spriteUrl,
    tile,
    alt: `${meal.meal_name} — representative illustrative dish image`,
    isMapped: Object.prototype.hasOwnProperty.call(mappedTiles, meal.meal_id),
  };
}

