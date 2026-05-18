from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.ai.analyzer import select_food_analyzer
from app.mock.density import calorie_range_from_density
from app.observability.log_writer import write_model_run
from app.observability.model_run import build_model_run, now_utc
from app.schemas.food import (
    CalorieRange,
    ErrorResponse,
    FoodAnalysis,
    FoodAnalyzeMockRequest,
    FoodCorrectionMockRequest,
    UserCorrection,
)

router = APIRouter(prefix="/api/v0/food", tags=["food"])

ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
ANALYZE_MOCK_ROUTE = "POST /api/v0/food/analyze/mock"
CORRECTION_MOCK_ROUTE = "POST /api/v0/food/corrections/mock"


@router.post(
    "/analyze/mock",
    response_model=FoodAnalysis,
    responses={
        400: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        422: {"description": "Invalid request body"},
        500: {"model": ErrorResponse},
    },
)
def analyze_food_mock(payload: FoodAnalyzeMockRequest) -> FoodAnalysis | JSONResponse:
    request_id = str(uuid4())
    started_at = now_utc()
    input_summary = _analyze_input_summary(payload)
    validation_error = _validate_metadata(payload)
    if validation_error is not None:
        status_code, error = validation_error
        write_model_run(
            build_model_run(
                request_id=request_id,
                route=ANALYZE_MOCK_ROUTE,
                started_at=started_at,
                input_summary=input_summary,
                output_summary={},
                error_code=error.code,
                error_message=error.message,
            )
        )
        return JSONResponse(status_code=status_code, content=error.model_dump())

    analyzer_mode = "mock"
    analyzer_model = "mock"

    try:
        analyzer = select_food_analyzer()
        analyzer_mode = analyzer.mode
        analyzer_model = analyzer.model
        analysis = analyzer.analyze(payload)
        write_model_run(
            build_model_run(
                request_id=request_id,
                route=ANALYZE_MOCK_ROUTE,
                mode=analyzer_mode,
                model=analyzer_model,
                started_at=started_at,
                input_summary=input_summary,
                output_summary=_analyze_output_summary(analysis),
                safety_flags=analysis.safety_flags,
            )
        )
        return analysis
    except Exception:
        error = ErrorResponse(
            code="analysis_failed",
            message="Analysis unavailable. Please try again.",
        )
        write_model_run(
            build_model_run(
                request_id=request_id,
                route=ANALYZE_MOCK_ROUTE,
                mode=analyzer_mode,
                model=analyzer_model,
                started_at=started_at,
                input_summary=input_summary,
                output_summary={},
                error_code=error.code,
                error_message=error.message,
            )
        )
        return JSONResponse(status_code=500, content=error.model_dump())


@router.post(
    "/corrections/mock",
    response_model=UserCorrection,
    responses={
        422: {"description": "Invalid request body"},
        500: {"model": ErrorResponse},
    },
)
def correct_food_mock(payload: FoodCorrectionMockRequest) -> UserCorrection | JSONResponse:
    # Pydantic 422 validation happens before this handler, so those failures
    # do not emit ModelRun records.
    request_id = str(uuid4())
    started_at = now_utc()
    input_summary = _correction_input_summary(payload)

    try:
        corrected_calories = calorie_range_from_density(
            grams=payload.corrected_grams,
            density=payload.calorie_density_kcal_per_gram,
            confidence=payload.confidence,
        )

        correction = UserCorrection(
            correction_id=str(uuid4()),
            item_id=payload.item_id,
            original_name=payload.original_name,
            corrected_name=payload.original_name,
            original_grams=payload.original_grams,
            corrected_grams=payload.corrected_grams,
            original_calories=payload.original_calories,
            corrected_calories=corrected_calories,
            correction_timestamp=datetime.now(UTC),
            correction_source="user",
        )
        write_model_run(
            build_model_run(
                request_id=request_id,
                route=CORRECTION_MOCK_ROUTE,
                started_at=started_at,
                input_summary=input_summary,
                output_summary=_correction_output_summary(correction),
            )
        )
        return correction
    except Exception:
        error = ErrorResponse(
            code="correction_failed",
            message="Correction unavailable. Please try again.",
        )
        write_model_run(
            build_model_run(
                request_id=request_id,
                route=CORRECTION_MOCK_ROUTE,
                started_at=started_at,
                input_summary=input_summary,
                output_summary={},
                error_code=error.code,
                error_message=error.message,
            )
        )
        return JSONResponse(status_code=500, content=error.model_dump())


def _validate_metadata(
    payload: FoodAnalyzeMockRequest,
) -> tuple[int, ErrorResponse] | None:
    if payload.content_type not in ALLOWED_IMAGE_TYPES:
        return (
            400,
            ErrorResponse(
                code="invalid_file_type",
                message="Only JPEG, PNG, WebP, and HEIC images are supported.",
            ),
        )

    if payload.size_bytes == 0:
        return (
            400,
            ErrorResponse(code="empty_file", message="The selected file appears to be empty."),
        )

    if payload.size_bytes > MAX_FILE_SIZE_BYTES:
        return (
            413,
            ErrorResponse(
                code="file_too_large",
                message="Photo must be under 10 MB.",
            ),
        )

    return None


def _analyze_input_summary(payload: FoodAnalyzeMockRequest) -> dict[str, object]:
    return {
        "filename": payload.filename,
        "content_type": payload.content_type,
        "size_bytes": payload.size_bytes,
    }


def _analyze_output_summary(analysis: FoodAnalysis) -> dict[str, object]:
    return {
        "analysis_id": analysis.analysis_id,
        "items_count": analysis.items_count,
        "total_calories": _calorie_range_summary(analysis.total_calories),
        "safety_flags": analysis.safety_flags,
    }


def _correction_input_summary(payload: FoodCorrectionMockRequest) -> dict[str, object]:
    return {
        "item_id": payload.item_id,
        "original_name": payload.original_name,
        "original_grams": payload.original_grams,
        "corrected_grams": payload.corrected_grams,
        "confidence": payload.confidence,
    }


def _correction_output_summary(correction: UserCorrection) -> dict[str, object]:
    return {
        "correction_id": correction.correction_id,
        "item_id": correction.item_id,
        "corrected_grams": correction.corrected_grams,
        "corrected_calories": _calorie_range_summary(correction.corrected_calories),
    }


def _calorie_range_summary(calories: CalorieRange) -> dict[str, int]:
    return {
        "min": calories.min,
        "max": calories.max,
        "point_estimate": calories.point_estimate,
    }
