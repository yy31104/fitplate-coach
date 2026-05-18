from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse

from app.ai.analyzer import AIAnalysisError, select_food_analyzer
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
UPLOAD_READ_CHUNK_BYTES = 64 * 1024
MAX_LOGGED_FILENAME_LENGTH = 255
ANALYZE_UPLOAD_ROUTE = "POST /api/v0/food/analyze"
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
    analyzer_prompt_name = None
    analyzer_prompt_version = None

    try:
        analyzer = select_food_analyzer()
        analyzer_mode = analyzer.mode
        analyzer_model = analyzer.model
        analyzer_prompt_name = getattr(analyzer, "prompt_name", None)
        analyzer_prompt_version = getattr(analyzer, "prompt_version", None)
        analysis = analyzer.analyze(payload)
        write_model_run(
            build_model_run(
                request_id=request_id,
                route=ANALYZE_MOCK_ROUTE,
                mode=analyzer_mode,
                model=analyzer_model,
                prompt_name=analyzer_prompt_name,
                prompt_version=analyzer_prompt_version,
                started_at=started_at,
                input_summary=input_summary,
                output_summary=_analyze_output_summary(analysis),
                safety_flags=analysis.safety_flags,
            )
        )
        return analysis
    except AIAnalysisError as exc:
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
                prompt_name=analyzer_prompt_name,
                prompt_version=analyzer_prompt_version,
                started_at=started_at,
                input_summary=input_summary,
                output_summary={},
                safety_flags=exc.safety_flags,
                error_code=error.code,
                error_message=error.message,
            )
        )
        return JSONResponse(status_code=500, content=error.model_dump())
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
                prompt_name=analyzer_prompt_name,
                prompt_version=analyzer_prompt_version,
                started_at=started_at,
                input_summary=input_summary,
                output_summary={},
                error_code=error.code,
                error_message=error.message,
            )
        )
        return JSONResponse(status_code=500, content=error.model_dump())


@router.post(
    "/analyze",
    response_model=FoodAnalysis,
    responses={
        400: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        422: {"description": "Invalid request body"},
        500: {"model": ErrorResponse},
    },
)
async def analyze_food_upload(
    image: UploadFile = File(...),
) -> FoodAnalysis | JSONResponse:
    request_id = str(uuid4())
    started_at = now_utc()
    filename = _truncate_filename(image.filename)
    content_type = image.content_type or ""
    input_summary = _upload_input_summary(
        filename=filename,
        content_type=content_type,
        size_bytes=0,
    )

    content_type_error = _validate_upload_content_type(image.content_type)
    if content_type_error is not None:
        write_model_run(
            build_model_run(
                request_id=request_id,
                route=ANALYZE_UPLOAD_ROUTE,
                started_at=started_at,
                input_summary=input_summary,
                output_summary={},
                error_code=content_type_error.code,
                error_message=content_type_error.message,
            )
        )
        return JSONResponse(status_code=400, content=content_type_error.model_dump())

    uploaded_bytes, size_bytes, exceeded = await _read_upload_bytes_bounded(image)
    input_summary = _upload_input_summary(
        filename=filename,
        content_type=content_type,
        size_bytes=size_bytes,
    )

    if exceeded:
        error = ErrorResponse(
            code="file_too_large",
            message="Photo must be under 10 MB.",
        )
        write_model_run(
            build_model_run(
                request_id=request_id,
                route=ANALYZE_UPLOAD_ROUTE,
                started_at=started_at,
                input_summary=input_summary,
                output_summary={},
                error_code=error.code,
                error_message=error.message,
            )
        )
        return JSONResponse(status_code=413, content=error.model_dump())

    if size_bytes == 0:
        error = ErrorResponse(
            code="empty_file",
            message="The selected file appears to be empty.",
        )
        write_model_run(
            build_model_run(
                request_id=request_id,
                route=ANALYZE_UPLOAD_ROUTE,
                started_at=started_at,
                input_summary=input_summary,
                output_summary={},
                error_code=error.code,
                error_message=error.message,
            )
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    payload = FoodAnalyzeMockRequest(
        filename=image.filename or "",
        content_type=content_type,
        size_bytes=size_bytes,
        last_modified_ms=0,
    )
    uploaded_bytes.clear()

    analyzer_mode = "mock"
    analyzer_model = "mock"
    analyzer_prompt_name = None
    analyzer_prompt_version = None

    try:
        analyzer = select_food_analyzer()
        analyzer_mode = analyzer.mode
        analyzer_model = analyzer.model
        analyzer_prompt_name = getattr(analyzer, "prompt_name", None)
        analyzer_prompt_version = getattr(analyzer, "prompt_version", None)
        analysis = analyzer.analyze(payload)
        write_model_run(
            build_model_run(
                request_id=request_id,
                route=ANALYZE_UPLOAD_ROUTE,
                mode=analyzer_mode,
                model=analyzer_model,
                prompt_name=analyzer_prompt_name,
                prompt_version=analyzer_prompt_version,
                started_at=started_at,
                input_summary=input_summary,
                output_summary=_analyze_output_summary(analysis),
                safety_flags=analysis.safety_flags,
            )
        )
        return analysis
    except AIAnalysisError as exc:
        error = ErrorResponse(
            code="analysis_failed",
            message="Analysis unavailable. Please try again.",
        )
        write_model_run(
            build_model_run(
                request_id=request_id,
                route=ANALYZE_UPLOAD_ROUTE,
                mode=analyzer_mode,
                model=analyzer_model,
                prompt_name=analyzer_prompt_name,
                prompt_version=analyzer_prompt_version,
                started_at=started_at,
                input_summary=input_summary,
                output_summary={},
                safety_flags=exc.safety_flags,
                error_code=error.code,
                error_message=error.message,
            )
        )
        return JSONResponse(status_code=500, content=error.model_dump())
    except Exception:
        error = ErrorResponse(
            code="analysis_failed",
            message="Analysis unavailable. Please try again.",
        )
        write_model_run(
            build_model_run(
                request_id=request_id,
                route=ANALYZE_UPLOAD_ROUTE,
                mode=analyzer_mode,
                model=analyzer_model,
                prompt_name=analyzer_prompt_name,
                prompt_version=analyzer_prompt_version,
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


def _truncate_filename(name: str | None, limit: int = MAX_LOGGED_FILENAME_LENGTH) -> str:
    return (name or "")[:limit]


def _upload_input_summary(
    *,
    filename: str,
    content_type: str,
    size_bytes: int,
) -> dict[str, object]:
    return {
        "transport": "multipart",
        "filename": filename,
        "content_type": content_type,
        "size_bytes": size_bytes,
    }


def _validate_upload_content_type(content_type: str | None) -> ErrorResponse | None:
    if not content_type or content_type not in ALLOWED_IMAGE_TYPES:
        return ErrorResponse(
            code="invalid_file_type",
            message="Only JPEG, PNG, WebP, and HEIC images are supported.",
        )

    return None


async def _read_upload_bytes_bounded(
    image: UploadFile,
) -> tuple[bytearray, int, bool]:
    uploaded_bytes = bytearray()
    total_bytes = 0

    while True:
        chunk = await image.read(UPLOAD_READ_CHUNK_BYTES)
        if not chunk:
            return uploaded_bytes, total_bytes, False

        total_bytes += len(chunk)
        if total_bytes > MAX_FILE_SIZE_BYTES:
            uploaded_bytes.clear()
            return uploaded_bytes, total_bytes, True

        uploaded_bytes.extend(chunk)


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
