import { useState } from "react";
import { Utensils } from "lucide-react";
import { resolveMealImage } from "./images";
import type { Meal } from "./types";

export function MealImage({ meal, className = "" }: { meal: Pick<Meal, "meal_id" | "meal_name" | "meal_type">; className?: string }) {
  const image = resolveMealImage(meal);
  const [failed, setFailed] = useState(false);
  const positions = ["0% 0%", "50% 0%", "100% 0%", "0% 50%", "50% 50%", "100% 50%", "0% 100%", "50% 100%", "100% 100%"];
  return (
    <div className={`meal-image ${className}`} role="img" aria-label={image.alt}>
      {!failed ? (
        <>
          <div
            className="meal-image__photo"
            style={{ backgroundImage: `url("${image.src}")`, backgroundPosition: positions[image.tile] }}
            aria-hidden="true"
          />
          <img className="image-preloader" src={image.src} alt="" loading="lazy" onError={() => setFailed(true)} />
        </>
      ) : (
        <div className="meal-image__fallback" aria-hidden="true"><Utensils size={25} strokeWidth={1.6} /><span>Dish illustration</span></div>
      )}
      {!image.isMapped && <span className="image-note">Illustrative</span>}
    </div>
  );
}

