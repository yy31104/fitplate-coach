import type { CalorieRange, SafetyFlag } from "./food-analysis-types";

export function formatCalories(range: CalorieRange): string {
  return `${range.min}-${range.max} kcal`;
}

export function formatFlag(flag: SafetyFlag): string {
  return flag.replaceAll("_", " ");
}
