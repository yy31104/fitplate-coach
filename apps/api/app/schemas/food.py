from datetime import datetime
from typing import Literal, get_args

from pydantic import BaseModel, Field

AnalysisMode = Literal["mock"]
Confidence = Literal["high", "medium", "low"]
SafetyFlag = Literal[
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
]
ErrorCode = Literal[
    "invalid_file_type",
    "file_too_large",
    "empty_file",
    "analysis_failed",
    "correction_failed",
]

KNOWN_SAFETY_FLAGS: set[str] = set(get_args(SafetyFlag))


class CalorieRange(BaseModel):
    min: int
    max: int
    point_estimate: int


class FoodAnalyzeMockRequest(BaseModel):
    filename: str
    content_type: str
    size_bytes: int = Field(ge=0)
    last_modified_ms: int


class FoodCorrectionMockRequest(BaseModel):
    item_id: str = Field(min_length=1)
    original_name: str = Field(min_length=1)
    original_grams: int = Field(ge=1)
    corrected_grams: int = Field(ge=1, le=2000)
    calorie_density_kcal_per_gram: float = Field(gt=0)
    confidence: Confidence
    original_calories: CalorieRange


class ErrorResponse(BaseModel):
    code: ErrorCode
    message: str


class PortionEstimate(BaseModel):
    description: str
    grams_estimate: int
    assumptions: list[str]


class FoodItem(BaseModel):
    item_id: str
    name: str
    portion: PortionEstimate
    calories: CalorieRange
    calorie_density_kcal_per_gram: float
    confidence: Confidence


class UserCorrection(BaseModel):
    correction_id: str
    item_id: str
    original_name: str
    corrected_name: str
    original_grams: int
    corrected_grams: int
    original_calories: CalorieRange
    corrected_calories: CalorieRange
    correction_timestamp: datetime
    correction_source: Literal["user"]


class FoodAnalysis(BaseModel):
    analysis_id: str
    schema_version: Literal["food_analysis.v1"]
    mode: AnalysisMode
    analyzed_at: datetime
    items_count: int
    items: list[FoodItem]
    total_calories: CalorieRange
    uncertainty_notes: list[str]
    safety_flags: list[SafetyFlag]
    user_corrections: list[UserCorrection]
