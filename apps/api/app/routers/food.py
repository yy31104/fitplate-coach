from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.mock.food_analyzer import analyze_food_metadata
from app.schemas.food import ErrorResponse, FoodAnalysis, FoodAnalyzeMockRequest

router = APIRouter(prefix="/api/v0/food", tags=["food"])

ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024


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
    validation_error = _validate_metadata(payload)
    if validation_error is not None:
        status_code, error = validation_error
        return JSONResponse(status_code=status_code, content=error.model_dump())

    try:
        return analyze_food_metadata(payload)
    except Exception:
        error = ErrorResponse(
            code="analysis_failed",
            message="Analysis unavailable. Please try again.",
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
