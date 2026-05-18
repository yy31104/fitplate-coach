import { formatCalories } from "../../../../lib/food-analysis-format";
import type { FoodItem } from "../../../../lib/food-analysis-types";

export function FoodItemRow({ item }: { item: FoodItem }) {
  return (
    <div className="rounded-md border border-stone-200 bg-stone-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-medium text-stone-950">{item.name}</p>
          <p className="mt-1 text-sm text-stone-600">
            {item.portion.description} · {formatCalories(item.calories)}
          </p>
        </div>
        <span className="rounded-full border border-stone-300 bg-white px-3 py-1 text-xs font-medium text-stone-700">
          {item.confidence} confidence
        </span>
      </div>
    </div>
  );
}
