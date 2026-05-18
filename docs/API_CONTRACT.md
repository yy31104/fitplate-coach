# API Contract

This document describes the current FastAPI contract for FitPlate Coach. It is source-aligned documentation for the live backend endpoints, not a roadmap or OpenAPI replacement.

Current live endpoints:

- `GET /api/v0/health`
- `POST /api/v0/food/analyze/mock`
- `POST /api/v0/food/corrections/mock`

The food analysis endpoint accepts file metadata only. It does not accept image bytes, upload files, store files, authenticate users, or call a real AI model. By default it uses deterministic mock analysis; when `FITPLATE_AI_MODE=ai`, it uses a local fake provider path for AI-readiness testing.

## Base URL and Versioning

Local development base URL:

```text
http://127.0.0.1:8000
```

All current API routes are versioned under `/api/v0/`.

Do not rely on unversioned routes. Incompatible request or response changes should use a new API version rather than changing `/api/v0/` behavior silently.

## CORS Policy

Local CORS configuration allows:

- Origin: `http://127.0.0.1:3000`
- Methods: `GET`, `POST`
- Credentials: disabled
- Headers: all request headers

Do not deploy this API with wildcard CORS origins.

## Authentication

There is no authentication in v0. Current endpoints accept requests without user identity, sessions, tokens, cookies, or API keys.

Do not expose this API on a public host until authentication and abuse controls are intentionally added.

## Request and Response Format

The API uses JSON request and response bodies for the current food mock endpoint.

The current mock endpoint is metadata-only:

- The client sends filename, MIME type, file size, and last-modified timestamp.
- The client does not send image bytes.
- The backend does not store image files.
- The backend does not inspect image content.

Datetime values in responses are ISO-8601 strings with timezone information.

## Error Envelope

Project-defined food endpoint errors use this envelope:

```json
{
  "code": "invalid_file_type",
  "message": "Only JPEG, PNG, WebP, and HEIC images are supported."
}
```

Current `ErrorResponse.code` values are:

- `invalid_file_type`
- `file_too_large`
- `empty_file`
- `analysis_failed`
- `correction_failed`

FastAPI request validation errors return HTTP `422 Unprocessable Entity` using FastAPI's standard validation response body. They are not wrapped in the project `ErrorResponse` envelope.

## Endpoints

### GET /api/v0/health

Purpose: report whether the API process is reachable.

Authentication: none.

#### Request

Content-Type: none required.

Request body: none.

```http
GET /api/v0/health HTTP/1.1
Host: 127.0.0.1:8000
```

#### Response

Success status: `200 OK`

Response schema:

| Field | Type | Description |
| --- | --- | --- |
| `status` | string literal `"ok"` | Health status. |
| `service` | string | Service identifier. |
| `version` | string | API version string. |

Success example:

```json
{
  "status": "ok",
  "service": "fitplate-api",
  "version": "0.1.0"
}
```

#### Error Responses

This endpoint does not define project-specific error responses.

Examples from the current FastAPI routing layer:

- `404 Not Found` for unknown routes such as `GET /api/v0/nonexistent`.
- `405 Method Not Allowed` for unsupported methods such as `POST /api/v0/health`.

404 example:

```json
{
  "detail": "Not Found"
}
```

405 example:

```json
{
  "detail": "Method Not Allowed"
}
```

These responses use FastAPI's default error body, not `ErrorResponse`.

#### Notes

This endpoint is intentionally small and does not perform dependency checks.

### POST /api/v0/food/analyze/mock

Purpose: return deterministic mock food analysis JSON from file metadata.

Authentication: none.

#### Request

Content-Type: `application/json`

Body schema: `FoodAnalyzeMockRequest`

Fields:

| Field | Type | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `filename` | string | yes | Non-empty is not currently enforced by schema. | Original filename of the selected file. |
| `content_type` | string | yes | Must be one of `image/jpeg`, `image/png`, `image/webp`, `image/heic`, `image/heif` to pass endpoint validation. | Browser-provided MIME type. |
| `size_bytes` | integer | yes | Pydantic requires `>= 0`; endpoint validation requires `> 0` and `<= 10485760`. | File size in bytes. |
| `last_modified_ms` | integer | yes | No additional range constraint. | File last-modified time as Unix milliseconds. |

Request example:

```http
POST /api/v0/food/analyze/mock HTTP/1.1
Host: 127.0.0.1:8000
Content-Type: application/json

{
  "filename": "lunch-photo.jpg",
  "content_type": "image/jpeg",
  "size_bytes": 345678,
  "last_modified_ms": 1710000000000
}
```

#### Response

Success status: `200 OK`

Response schema: `FoodAnalysis`

Standard food response example:

```json
{
  "analysis_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "schema_version": "food_analysis.v1",
  "mode": "mock",
  "analyzed_at": "2026-05-18T12:00:00Z",
  "items_count": 3,
  "items": [
    {
      "item_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
      "name": "Chicken breast",
      "portion": {
        "description": "~150g",
        "grams_estimate": 150,
        "assumptions": ["Portion estimated from visible plate size."]
      },
      "calories": {
        "min": 198,
        "max": 298,
        "point_estimate": 248
      },
      "calorie_density_kcal_per_gram": 1.65,
      "confidence": "medium"
    },
    {
      "item_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
      "name": "Steamed rice",
      "portion": {
        "description": "~200g",
        "grams_estimate": 200,
        "assumptions": ["Portion estimated from visible plate size."]
      },
      "calories": {
        "min": 234,
        "max": 286,
        "point_estimate": 260
      },
      "calorie_density_kcal_per_gram": 1.3,
      "confidence": "high"
    },
    {
      "item_id": "d4e5f6a7-b8c9-0123-defa-234567890123",
      "name": "Mixed salad",
      "portion": {
        "description": "~80g",
        "grams_estimate": 80,
        "assumptions": ["Portion estimated from visible plate size."]
      },
      "calories": {
        "min": 20,
        "max": 36,
        "point_estimate": 28
      },
      "calorie_density_kcal_per_gram": 0.35,
      "confidence": "low"
    }
  ],
  "total_calories": {
    "min": 452,
    "max": 620,
    "point_estimate": 536
  },
  "uncertainty_notes": [
    "Portions are estimated from visible image context.",
    "Cooking method is assumed to be standard."
  ],
  "safety_flags": [],
  "user_corrections": []
}
```

Non-food response example:

```json
{
  "analysis_id": "e5f6a7b8-c9d0-1234-efab-345678901234",
  "schema_version": "food_analysis.v1",
  "mode": "mock",
  "analyzed_at": "2026-05-18T12:00:00Z",
  "items_count": 0,
  "items": [],
  "total_calories": {
    "min": 0,
    "max": 0,
    "point_estimate": 0
  },
  "uncertainty_notes": [
    "No food was detected in this mock scenario."
  ],
  "safety_flags": ["non_food_image"],
  "user_corrections": []
}
```

#### Error Responses

Validation order:

1. Pydantic validates the request body structure and field constraints.
2. `content_type` is checked against the allowlist.
3. `size_bytes == 0` is checked.
4. `size_bytes > 10485760` is checked.
5. Mock analysis runs.

`400 Bad Request` with `invalid_file_type`:

```json
{
  "code": "invalid_file_type",
  "message": "Only JPEG, PNG, WebP, and HEIC images are supported."
}
```

Emitted when `content_type` is not one of:

- `image/jpeg`
- `image/png`
- `image/webp`
- `image/heic`
- `image/heif`

`400 Bad Request` with `empty_file`:

```json
{
  "code": "empty_file",
  "message": "The selected file appears to be empty."
}
```

Emitted when `size_bytes` is `0`.

`413 Payload Too Large` with `file_too_large`:

```json
{
  "code": "file_too_large",
  "message": "Photo must be under 10 MB."
}
```

Emitted when `size_bytes` is greater than `10485760`.

`422 Unprocessable Entity` for invalid request body:

```json
{
  "detail": [
    {
      "type": "greater_than_equal",
      "loc": ["body", "size_bytes"],
      "msg": "Input should be greater than or equal to 0",
      "input": -1,
      "ctx": {
        "ge": 0
      }
    }
  ]
}
```

FastAPI emits this for schema validation failures such as missing required fields, wrong field types, or `size_bytes < 0`. This response is not wrapped in `ErrorResponse`.

`500 Internal Server Error` with `analysis_failed`:

```json
{
  "code": "analysis_failed",
  "message": "Analysis unavailable. Please try again."
}
```

Emitted only if an unexpected exception occurs during mock analysis.

#### Notes

- This endpoint is explicitly mock-only.
- The request body contains file metadata only.
- Image bytes are not transmitted to or stored by the backend.
- The backend does not verify that the selected image contains food.
- `analysis_id` and `item_id` values are generated UUID strings and change on every call.

### POST /api/v0/food/corrections/mock

Purpose: recompute one corrected food item calorie range and return a `UserCorrection`.

Authentication: none.

#### Request

Content-Type: `application/json`

Body schema: `FoodCorrectionMockRequest`

Fields:

| Field | Type | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `item_id` | string | yes | `min_length=1` | Item identifier from the original `FoodItem`. |
| `original_name` | string | yes | `min_length=1` | Food name from the original `FoodItem`. |
| `original_grams` | integer | yes | `>= 1` | Original estimated portion in grams. |
| `corrected_grams` | integer | yes | `>= 1` and `<= 2000` | User-corrected portion in grams. |
| `calorie_density_kcal_per_gram` | number | yes | `> 0` | Density returned by the original `FoodItem`. |
| `confidence` | string | yes | `"high"`, `"medium"`, or `"low"` | Original item confidence used to preserve the uncertainty margin. |
| `original_calories` | `CalorieRange` | yes | Must match `CalorieRange` shape. | Original item calorie range, passed through unchanged. |

Request example:

```http
POST /api/v0/food/corrections/mock HTTP/1.1
Host: 127.0.0.1:8000
Content-Type: application/json

{
  "item_id": "test-item-id-001",
  "original_name": "Chicken breast",
  "original_grams": 150,
  "corrected_grams": 200,
  "calorie_density_kcal_per_gram": 1.65,
  "confidence": "medium",
  "original_calories": {
    "min": 198,
    "max": 298,
    "point_estimate": 248
  }
}
```

#### Response

Success status: `200 OK`

Response schema: `UserCorrection`

Success example:

```json
{
  "correction_id": "f6a7b8c9-d0e1-2345-fabc-456789012345",
  "item_id": "test-item-id-001",
  "original_name": "Chicken breast",
  "corrected_name": "Chicken breast",
  "original_grams": 150,
  "corrected_grams": 200,
  "original_calories": {
    "min": 198,
    "max": 298,
    "point_estimate": 248
  },
  "corrected_calories": {
    "min": 264,
    "max": 396,
    "point_estimate": 330
  },
  "correction_timestamp": "2026-05-18T12:00:00Z",
  "correction_source": "user"
}
```

#### Error Responses

`422 Unprocessable Entity` for invalid request body:

```json
{
  "detail": [
    {
      "type": "greater_than_equal",
      "loc": ["body", "corrected_grams"],
      "msg": "Input should be greater than or equal to 1",
      "input": 0,
      "ctx": {
        "ge": 1
      }
    }
  ]
}
```

FastAPI emits this for schema validation failures such as missing fields, empty `item_id`, empty `original_name`, `corrected_grams < 1`, `corrected_grams > 2000`, `calorie_density_kcal_per_gram <= 0`, invalid `confidence`, or invalid `original_calories` shape. This response is not wrapped in `ErrorResponse`.

`500 Internal Server Error` with `correction_failed`:

```json
{
  "code": "correction_failed",
  "message": "Correction unavailable. Please try again."
}
```

Emitted only if an unexpected exception occurs during correction computation.

#### Notes

- This endpoint corrects one item only.
- `corrected_name` is always equal to `original_name`; food name correction is not implemented.
- The confidence margin is preserved from the original item.
- `correction_id` is a fresh UUID per call and is not stable across identical requests.
- No correction data is persisted.
- `analysis_id` is not included in the request. This mock endpoint does not associate corrections with a persisted analysis record.
- The response does not include total calories. Callers sum item ranges if needed.

## Schema Reference

### FoodAnalyzeMockRequest

| Field | Type | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `filename` | string | yes | No explicit Pydantic length constraint. | Original filename of the selected file. |
| `content_type` | string | yes | Must pass endpoint allowlist validation. | Browser-provided MIME type. |
| `size_bytes` | integer | yes | Pydantic `>= 0`; endpoint requires `> 0` and `<= 10485760`. | File size in bytes. |
| `last_modified_ms` | integer | yes | No explicit range constraint. | File last-modified time as Unix milliseconds. |

### FoodCorrectionMockRequest

| Field | Type | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `item_id` | string | yes | `min_length=1` | Item identifier from the original `FoodItem`. |
| `original_name` | string | yes | `min_length=1` | Food name from the original `FoodItem`. |
| `original_grams` | integer | yes | `>= 1` | Original estimated portion in grams. |
| `corrected_grams` | integer | yes | `>= 1` and `<= 2000` | User-corrected portion in grams. |
| `calorie_density_kcal_per_gram` | number | yes | `> 0` | Density returned by the original `FoodItem`. |
| `confidence` | `"high"`, `"medium"`, or `"low"` | yes | Must be a valid `Confidence` value. | Original confidence used to choose the uncertainty margin. |
| `original_calories` | `CalorieRange` | yes | Must match `CalorieRange` shape. | Original item calorie range, passed through unchanged. |

### FoodAnalysis

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `analysis_id` | string | yes | UUID string generated fresh per response. |
| `schema_version` | string literal `"food_analysis.v1"` | yes | Food analysis schema version. |
| `mode` | string literal `"mock"` or `"ai"` | yes | Analysis mode. Default mock analyzer responses use `"mock"`; the local fake-provider AI-readiness path uses `"ai"`. |
| `analyzed_at` | ISO-8601 datetime string | yes | Time the mock analysis was generated. |
| `items_count` | integer | yes | Equals the number of entries in `items`. |
| `items` | array of `FoodItem` | yes | Estimated food items. May be empty. |
| `total_calories` | `CalorieRange` | yes | Sum of all item calorie ranges. Zero range when `items` is empty. |
| `uncertainty_notes` | array of strings | yes | Notes explaining mock assumptions or uncertainty. |
| `safety_flags` | array of `SafetyFlag` | yes | Structured safety flags. May be empty. |
| `user_corrections` | array of `UserCorrection` | yes | Always empty in mock responses. |

### FoodItem

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `item_id` | string | yes | UUID string generated fresh per item per response. |
| `name` | string | yes | Human-readable food item name. |
| `portion` | `PortionEstimate` | yes | Portion estimate and assumptions. |
| `calories` | `CalorieRange` | yes | Calorie range for this item. |
| `calorie_density_kcal_per_gram` | number | yes | Density used to compute this item's range. Clients should use this for correction recomputation. |
| `confidence` | `"high"`, `"medium"`, or `"low"` | yes | Confidence level used to choose the uncertainty margin. |

### PortionEstimate

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `description` | string | yes | Human-readable portion description, such as `"~150g"`. |
| `grams_estimate` | integer | yes | Estimated portion weight in grams. |
| `assumptions` | array of strings | yes | Assumptions made for this portion estimate. |

### CalorieRange

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `min` | integer | yes | Lower bound of the calorie estimate. |
| `max` | integer | yes | Upper bound of the calorie estimate. |
| `point_estimate` | integer | yes | Central estimate. Do not display this as an exact claim. |

### UserCorrection

`UserCorrection` is present in the contract but `user_corrections` is always an empty array in current mock responses.

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `correction_id` | string | yes | UUID string for the correction event. |
| `item_id` | string | yes | References `FoodItem.item_id`. |
| `original_name` | string | yes | Food name before correction. |
| `corrected_name` | string | yes | User-confirmed food name. If unchanged, repeat `original_name`. |
| `original_grams` | integer | yes | Portion estimate before correction. |
| `corrected_grams` | integer | yes | User-confirmed portion estimate in grams. |
| `original_calories` | `CalorieRange` | yes | Calorie range before correction. |
| `corrected_calories` | `CalorieRange` | yes | Calorie range after recomputation. |
| `correction_timestamp` | ISO-8601 datetime string | yes | Time the correction was created. |
| `correction_source` | string literal `"user"` | yes | Source of the correction. |

### ErrorResponse

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `code` | error code string | yes | One of `invalid_file_type`, `file_too_large`, `empty_file`, `analysis_failed`, `correction_failed`. |
| `message` | string | yes | Human-readable message suitable for display. |

## Safety Flags Reference

The current schema defines 13 safety flag values:

| Flag | Description |
| --- | --- |
| `low_confidence` | Analysis confidence is too low for a strong estimate. |
| `poor_media_quality` | Image or video is blurry, dark, occluded, or badly framed. |
| `non_food_image` | Food analysis receives an image that does not appear to contain food. |
| `nsfw_or_sensitive_image` | Upload appears NSFW or too sensitive to analyze. |
| `unsupported_food_image` | Image type or content is outside supported food-analysis scope. |
| `extreme_calorie_restriction` | User request or generated output points toward unsafe restriction. |
| `medical_concern` | Request asks for medical diagnosis, clinical interpretation, or disease advice. |
| `eating_disorder_concern` | Request suggests eating disorder diagnosis, screening, or unsafe compensatory behavior. |
| `injury_or_pain_concern` | Exercise request includes pain, injury, or diagnosis concerns. |
| `treatment_request` | User asks for treatment, rehabilitation, medication, or clinical plan. |
| `unsafe_exercise_instruction` | Output or request encourages training through pain or unsafe loading. |
| `unsupported_exercise` | Exercise analysis receives a movement outside the supported scope. |
| `schema_validation_failed` | AI or mock output fails the expected structured schema. |

In current mock mode, only these safety flags are emitted:

- `low_confidence`
- `non_food_image`

The full set exists in the v0 schema so clients can handle future safety flags without a breaking schema change.

## Mock Mode Behavior

The live food analysis endpoint is explicitly named `/analyze/mock`. Default deterministic mock responses include `mode: "mock"`; the opt-in fake-provider AI-readiness path uses the same schema with `mode: "ai"` and still makes no real provider call.

Mock scenario selection is deterministic per filename:

1. The backend computes SHA-256 of the filename string.
2. It reads the first byte.
3. It computes that byte modulo `10`.
4. The result selects a scenario bucket.

The same filename always selects the same scenario. `analysis_id`, `item_id`, and `analyzed_at` still change on every call.

Scenarios:

| Bucket | Scenario | Items | Safety flags |
| --- | --- | --- | --- |
| `0`-`6` | Standard | Chicken breast, steamed rice, mixed salad | none |
| `7` | Low confidence | Mixed entree, avocado | `low_confidence` |
| `8` | Non-food | none | `non_food_image` |
| `9` | Complex | Salmon, pasta, beans, fried egg, tortilla | none |

`user_corrections` is always an empty array in mock responses. The correction schema exists now to avoid a breaking contract change when persisted corrections are introduced later.

Clients that recompute calories after a user correction should use the returned `calorie_density_kcal_per_gram` value for that item.

Calorie computation:

```text
point_estimate = round(grams * calorie_density_kcal_per_gram)
margin = confidence margin
min = round(point_estimate * (1 - margin))
max = round(point_estimate * (1 + margin))
```

Confidence margins:

| Confidence | Margin |
| --- | ---: |
| `high` | `0.10` |
| `medium` | `0.20` |
| `low` | `0.30` |

`total_calories` is the sum of all item `min`, `max`, and `point_estimate` values independently. All calorie values are integers.

## Safety and Privacy Notes

FitPlate Coach does not provide medical, clinical, dietary, or therapeutic advice. Calorie estimates are reflective aids, not medical claims.

Clients must not present `point_estimate` as an exact calorie count. The `min` and `max` values in `CalorieRange` are the appropriate primary display values.

This API does not receive image bytes. The request body contains file metadata only, and no image content is transmitted to or stored by the server.

The API has no authentication in v0. It must not be exposed on a public host until authentication is added.

CORS is restricted to `http://127.0.0.1:3000` in the development configuration. Do not deploy with wildcard CORS origins.

## Planned Endpoints

These endpoints are planned but not implemented. Their contracts are intentionally not defined here.

- `POST /api/v0/food/analyze`: real AI-backed food analysis. Expected to use the `FoodAnalysis` response schema with `mode: "ai"`.
- `POST /api/v0/food/corrections`: persisted correction endpoint. Not yet implemented. Will store corrections in a database.
- `POST /api/v0/exercise/analyze/mock`: mock squat form feedback.
