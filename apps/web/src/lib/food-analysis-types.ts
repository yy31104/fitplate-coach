export const safetyFlags = [
  "low_confidence",
  "poor_media_quality",
  "non_food_image",
  "nsfw_or_sensitive_image",
  "unsupported_food_image",
  "extreme_calorie_restriction",
  "medical_concern",
  "eating_disorder_concern",
  "injury_or_pain_concern",
  "treatment_request",
  "unsafe_exercise_instruction",
  "unsupported_exercise",
  "schema_validation_failed",
] as const;

export type SafetyFlag = (typeof safetyFlags)[number];
export type Confidence = "high" | "medium" | "low";

export interface FoodAnalyzeMockRequest {
  filename: string;
  content_type: string;
  size_bytes: number;
  last_modified_ms: number;
}

export interface CalorieRange {
  min: number;
  max: number;
  point_estimate: number;
}

export interface PortionEstimate {
  description: string;
  grams_estimate: number;
  assumptions: string[];
}

export interface FoodItem {
  item_id: string;
  name: string;
  portion: PortionEstimate;
  calories: CalorieRange;
  calorie_density_kcal_per_gram: number;
  confidence: Confidence;
}

export interface UserCorrection {
  correction_id: string;
  item_id: string;
  original_name: string;
  corrected_name: string;
  original_grams: number;
  corrected_grams: number;
  original_calories: CalorieRange;
  corrected_calories: CalorieRange;
  correction_timestamp: string;
  correction_source: "user";
}

export interface FoodAnalysis {
  analysis_id: string;
  schema_version: "food_analysis.v1";
  mode: "mock";
  analyzed_at: string;
  items_count: number;
  items: FoodItem[];
  total_calories: CalorieRange;
  uncertainty_notes: string[];
  safety_flags: SafetyFlag[];
  user_corrections: UserCorrection[];
}

export function isFoodAnalysis(value: unknown): value is FoodAnalysis {
  if (!isRecord(value)) {
    return false;
  }

  return (
    isString(value.analysis_id) &&
    value.schema_version === "food_analysis.v1" &&
    value.mode === "mock" &&
    isString(value.analyzed_at) &&
    isNumber(value.items_count) &&
    Array.isArray(value.items) &&
    value.items.every(isFoodItem) &&
    isCalorieRange(value.total_calories) &&
    isStringArray(value.uncertainty_notes) &&
    Array.isArray(value.safety_flags) &&
    value.safety_flags.every(isSafetyFlag) &&
    Array.isArray(value.user_corrections)
  );
}

function isFoodItem(value: unknown): value is FoodItem {
  if (!isRecord(value)) {
    return false;
  }

  return (
    isString(value.item_id) &&
    isString(value.name) &&
    isPortionEstimate(value.portion) &&
    isCalorieRange(value.calories) &&
    isNumber(value.calorie_density_kcal_per_gram) &&
    isConfidence(value.confidence)
  );
}

function isPortionEstimate(value: unknown): value is PortionEstimate {
  if (!isRecord(value)) {
    return false;
  }

  return (
    isString(value.description) &&
    isNumber(value.grams_estimate) &&
    isStringArray(value.assumptions)
  );
}

function isCalorieRange(value: unknown): value is CalorieRange {
  if (!isRecord(value)) {
    return false;
  }

  return isNumber(value.min) && isNumber(value.max) && isNumber(value.point_estimate);
}

function isSafetyFlag(value: unknown): value is SafetyFlag {
  return isString(value) && safetyFlags.includes(value as SafetyFlag);
}

function isConfidence(value: unknown): value is Confidence {
  return value === "high" || value === "medium" || value === "low";
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every(isString);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isString(value: unknown): value is string {
  return typeof value === "string";
}

function isNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}
