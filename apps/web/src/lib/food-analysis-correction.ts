import type {
  CalorieRange,
  FoodItem,
  UserCorrection,
} from "./food-analysis-types";

export function sumCalorieRanges(ranges: CalorieRange[]): CalorieRange {
  return ranges.reduce(
    (total, range) => ({
      min: total.min + range.min,
      max: total.max + range.max,
      point_estimate: total.point_estimate + range.point_estimate,
    }),
    { min: 0, max: 0, point_estimate: 0 },
  );
}

export function buildCorrectedTotal(
  items: FoodItem[],
  corrections: Record<string, UserCorrection>,
): CalorieRange {
  return sumCalorieRanges(
    items.map((item) => corrections[item.item_id]?.corrected_calories ?? item.calories),
  );
}
