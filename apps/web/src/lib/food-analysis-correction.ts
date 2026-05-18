import type {
  CalorieRange,
  Confidence,
  FoodItem,
  UserCorrection,
} from "./food-analysis-types";

export const CONFIDENCE_MARGIN: Record<Confidence, number> = {
  high: 0.1,
  medium: 0.2,
  low: 0.3,
};

export function recomputeCalorieRange(
  correctedGrams: number,
  density: number,
  confidence: Confidence,
): CalorieRange {
  const point_estimate = Math.round(correctedGrams * density);
  const margin = CONFIDENCE_MARGIN[confidence];

  return {
    min: Math.round(point_estimate * (1 - margin)),
    max: Math.round(point_estimate * (1 + margin)),
    point_estimate,
  };
}

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
