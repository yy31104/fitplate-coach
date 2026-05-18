# Architecture

## Overview

FitPlate Coach is planned as a mobile-first web app with a Next.js frontend and FastAPI backend. The first implementation milestone will use mock food analysis only, while preserving interfaces that can later support real AI calls, persistence, evaluation, and async video processing.

The architecture should keep these concerns separate:

- User experience.
- Backend API contracts.
- AI provider integration.
- Schema validation.
- Safety checks.
- Model run logging.
- User corrections.
- Future async media processing.

## Current Repository State

The repository currently contains the first minimal monorepo scaffold:

- `apps/web`: static Next.js, TypeScript, Tailwind home page.
- `apps/api`: FastAPI app exposing `GET /api/v0/health`.
- `apps/web`: `/food/new` metadata-only mock food analysis route.
- `apps/api`: `POST /api/v0/food/analyze/mock` and multipart `POST /api/v0/food/analyze`.

There is no AI integration, database, authentication, real file upload, file storage, video processing, Docker setup, or environment secret requirement.

## Planned High-Level System

```text
Mobile browser
  -> Next.js frontend
  -> FastAPI backend
  -> Analysis service boundary
  -> Mock analyzer in v0
  -> Real AI provider in v1+
```

Future persistence and operations:

```text
FastAPI backend
  -> Database
  -> Object storage
  -> Model run log table
  -> Evaluation dataset
  -> Cost and latency tracking
```

Future video processing:

```text
Frontend video upload
  -> FastAPI creates analysis job
  -> Object storage stores source video
  -> Queue receives job
  -> Worker performs video processing
  -> Results stored by job id
  -> Frontend polls for status
```

## Frontend Responsibilities

Future Next.js responsibilities:

- Mobile-first upload and correction flows.
- Clear display of uncertainty and confidence.
- Food item and portion correction controls.
- Safe, non-medical copy.
- Loading, error, and low-confidence states.
- Result rendering from structured API responses.

Frontend should not:

- Contain AI provider secrets.
- Treat unvalidated AI output as trusted.
- Present estimates as exact.
- Hide safety or uncertainty fields returned by the backend.

## Backend Responsibilities

Future FastAPI responsibilities:

- Define stable API contracts.
- Validate request payloads and response schemas.
- Route v0 requests to mock analyzers.
- Route v1+ requests to AI provider adapters.
- Apply safety checks.
- Log model runs when real AI is introduced.
- Store user corrections when persistence is introduced.
- Keep provider-specific details behind service boundaries.

## API Versioning

All first backend endpoints should live under `/api/v0/`. The initial scaffold endpoint is `GET /api/v0/health`. Food analysis currently exposes both the metadata-only mock endpoint `POST /api/v0/food/analyze/mock` and the multipart upload transport `POST /api/v0/food/analyze`. Future production food analysis and correction endpoints should use the same version prefix.

Do not expose unversioned endpoints. If request or response schemas change incompatibly later, introduce a new API version instead of silently changing `/api/v0/` behavior.

For local development, the API allows CORS from `http://127.0.0.1:3000` only. Do not use wildcard CORS for this app.

## Secret Management

Future AI provider keys and storage credentials must come from environment variables or a managed secret store. Secrets must never be committed, bundled into frontend code, returned in API responses, or written to logs.

## Food Mock Metadata

The mock food milestone sends JSON file metadata only to `POST /api/v0/food/analyze/mock`. The frontend validates one selected image file locally and sends filename, content type, size in bytes, and last modified time. Image bytes are not uploaded or stored.

The backend returns structured mock `FoodAnalysis` JSON and validates metadata with the same type and size boundaries. The endpoint must not use `UploadFile`, `multipart/form-data`, storage, AI calls, authentication, or database writes.

## Image Upload Route

`POST /api/v0/food/analyze` accepts a direct `multipart/form-data` request with one file field named `image`. This route is the upload transport for food analysis, while `/api/v0/food/analyze/mock` remains the metadata-only deterministic test endpoint and is not deprecated.

The upload route uses a multipart spool threshold above the 10 MB app-level cap, so accepted uploads within that cap stay in memory at the framework parser layer. Application code then reads bytes synchronously with a hard size cap, validates the declared content type and actual byte count, and discards the byte buffer at request scope end. It never persists image bytes and never writes them to disk, model-run logs, responses, or errors. Filenames are not used as filesystem paths and are truncated before logging.

In this PR, the analyzer still receives a metadata-shaped `FoodAnalyzeMockRequest` built from the upload: filename, content type, actual byte count, and `last_modified_ms=0`. `ImageRef` is not extended with bytes yet, and no real provider receives image content. Future production versions may move to signed object-storage uploads when media retention, user accounts, and larger files are intentionally introduced.

## Food Analysis Contract

Food analysis should use structured JSON. A future schema should include:

```json
{
  "analysis_id": "string",
  "schema_version": "food_analysis.v1",
  "mode": "mock|ai",
  "analyzed_at": "ISO-8601 string",
  "items_count": 0,
  "items": [
    {
      "item_id": "string",
      "name": "string",
      "portion": {
        "description": "string",
        "grams_estimate": 0,
        "assumptions": ["string"]
      },
      "calories": {
        "min": 0,
        "max": 0,
        "point_estimate": 0
      },
      "calorie_density_kcal_per_gram": 0,
      "confidence": "low|medium|high"
    }
  ],
  "total_calories": {
    "min": 0,
    "max": 0,
    "point_estimate": 0
  },
  "uncertainty_notes": ["string"],
  "safety_flags": ["low_confidence"],
  "user_corrections": [
    {
      "correction_id": "string",
      "item_id": "string",
      "original_name": "string",
      "corrected_name": "string",
      "original_grams": 0,
      "corrected_grams": 0,
      "original_calories": {
        "min": 0,
        "max": 0,
        "point_estimate": 0
      },
      "corrected_calories": {
        "min": 0,
        "max": 0,
        "point_estimate": 0
      },
      "correction_timestamp": "ISO-8601 string",
      "correction_source": "user"
    }
  ]
}
```

MVP v0 can use deterministic mock data that follows this shape. The schema should be treated as the product contract even before real AI exists.

Mock endpoint errors use a structured envelope:

```json
{
  "code": "invalid_file_type",
  "message": "Only JPEG, PNG, WebP, and HEIC images are supported."
}
```

## Correction Object Sub-Schema

The correction object is the canonical contract for v0 food corrections.

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `correction_id` | string | yes | Client- or server-created id for the correction event. |
| `item_id` | string | yes | Stable id of the food item being corrected. |
| `original_name` | string | yes | Food name before correction. |
| `corrected_name` | string | yes | User-confirmed food name. If unchanged, repeat `original_name`. |
| `original_grams` | number | yes | Portion estimate before correction. |
| `corrected_grams` | number | yes | User-confirmed portion estimate in grams. |
| `original_calories` | object | yes | Calorie range before correction. |
| `corrected_calories` | object | yes | Calorie range after deterministic recomputation. |
| `correction_timestamp` | string | yes | ISO-8601 timestamp. |
| `correction_source` | string | yes | For v0, always `user`. |

Future versions may add optional fields for prompt version, model id, or evaluation consent. Do not add those to MVP v0 because v0 has no real AI call, auth, or database.

## Mock Calorie Recalculation

MVP v0 recomputation must be deterministic and local to the mock analysis flow.

Algorithm:

1. Each mock food item includes `calorie_density_kcal_per_gram`.
2. If the user changes only grams, keep the existing density.
3. If the user changes the food name, look up a density from a small static mock table. If no match exists, use `generic_mixed_food`.
4. Compute `point_estimate = corrected_grams * calorie_density_kcal_per_gram`.
5. Compute the range from confidence:
   - `high`: point estimate plus or minus 10%.
   - `medium`: point estimate plus or minus 20%.
   - `low`: point estimate plus or minus 30%.
6. Sum item ranges to produce `total_calories`.
7. Store integer calorie values in the contract and display rounded ranges in the UI.

Initial static density table:

| Key | kcal per gram |
| --- | ---: |
| `rice_cooked` | 1.30 |
| `chicken_breast` | 1.65 |
| `mixed_salad` | 0.35 |
| `avocado` | 1.60 |
| `pasta_cooked` | 1.55 |
| `generic_mixed_food` | 1.50 |

This is not a nutrition database. It is a mock calculation rule so the frontend and backend do not invent different correction behavior.

## Safety Flags Enum

Use only these code-ready `safety_flags` values unless this document and the schema are updated together.

| Flag | When emitted |
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
| `unsupported_exercise` | Exercise analysis receives a movement other than the supported squat scope. |
| `schema_validation_failed` | AI or mock output fails the expected structured schema. |

## User Correction Loop

Corrections are a core product feature, not a secondary edit screen.

The correction object sub-schema above is the canonical shape for food corrections. Other docs should reference that schema instead of redefining correction fields.

Production uses:

- Improve user trust.
- Build evaluation examples.
- Detect recurring model failure modes.
- Estimate model error by food category.

## Prompt Versioning

When real AI is introduced, prompts should be versioned like application code.

Each AI request should record:

- Prompt name.
- Prompt version.
- Schema version.
- Model name.
- Provider.
- Runtime parameters.
- Safety policy version.

Prompt changes should be evaluated against fixed examples before being promoted.

## Prompt Registry

The API contains an internal prompt registry for future AI adapters. Prompt
artifacts live under `apps/api/prompts/`, and `app.ai.prompts.get_prompt`
loads registered prompt records with name, version, target schema version,
status, creation date, and prompt body.

The initial `food_analysis` `v1` prompt targets `food_analysis.v1` but is not
used by the live mock food route. It exists so real AI integration can start
from a versioned prompt contract instead of an ad hoc string.

Fixed food-analysis evaluation cases live under `apps/api/evaluation/` and run
against the deterministic mock analyzer today. Future AI adapters should use
the same case structure for prompt regression checks before promotion.

## Analyzer Adapter

Food analysis routes call a selected analyzer through a backend adapter
boundary instead of calling provider or mock logic directly. The current
selector reads `FITPLATE_AI_MODE` through cached backend settings and defaults
to `mock`, which keeps existing local behavior unchanged. By default those
settings are process-local via `get_settings()`.

`MockFoodAnalyzer` delegates to the deterministic mock analyzer. `AIFoodAnalyzer`
uses the prompt registry and an `AIProvider` boundary, but the only current
provider implementation is fake and local. Setting `FITPLATE_AI_MODE=ai` returns
a schema-validated fake `FoodAnalysis` with `mode: "ai"` so the integration
contract can be exercised without calling a real provider.

### Provider Adapter

The provider seam is separate from the analyzer seam. `AIFoodAnalyzer` owns
application-level behavior such as loading the registered food-analysis prompt,
building an `ImageRef`, validating provider output with the `FoodAnalysis`
schema, and overriding backend-controlled fields (`analysis_id`,
`schema_version`, `mode`, and `analyzed_at`). `AIProvider` implementations own
only the provider call shape.

`FakeAIProvider` is not real AI. It never reads API keys, never performs network
calls, and never receives image bytes. Its `ImageRef` currently contains only
`content_type` and `size_bytes`, which lets backend tests and evaluation cases
exercise the future provider path while preserving the v0 privacy boundary.

Real provider integration remains future work. It should use settings-backed
credentials, the same prompt registry record, tool-calling or equivalent
structured output guarantees, model run logging with prompt name and version,
timeout handling, and cost controls before any public product behavior depends
on it.

## Model Run Logs

Current food analysis and correction routes write append-only model run logs to
`apps/api/logs/model_runs.jsonl`. Each line is one `model_run.v1` JSON object
with route, mode, model, timing, summarized inputs, summarized outputs, safety
flags, token placeholders, cost placeholders, and error details when a route
fails unexpectedly.

The log exists before real AI integration so prompt observability, latency
tracking, cost tracking, and schema validation can attach to an existing
contract later. Current mock runs use `model: "mock"`, zero token counts, and
zero cost.

Privacy boundary: model run logs store summaries only. They must not store raw
media, raw full request bodies, raw full responses, secrets, or provider keys.
For multipart food uploads, logs include filename, content type, transport, and
actual byte count only.

## Cost Tracking

Cost tracking should be added before real AI usage is open-ended.

Track:

- Cost per analysis.
- Cost by model.
- Cost by feature.
- Failed-call cost.
- Average cost per active user.
- Monthly budget thresholds.

## Privacy and Data Handling

Food photos and exercise videos are health-adjacent personal data. Future implementation should treat them carefully even if the app is not medical.

Privacy expectations:

- Minimize retention by default.
- Store media in object storage, not directly in logs.
- Use references in model run logs.
- Provide deletion paths once users and persistence exist.
- Avoid using uploaded media for evaluation unless users opt in or the project explicitly documents the policy.
- Keep secrets out of the frontend.
- Treat GDPR/CCPA-style access and deletion requirements as a future production concern once accounts or persistent personal data exist.

## Future Async Video Pipeline

Video processing should be async because files can be large and analysis can be slow.

Planned flow:

1. Frontend uploads video through the future approved upload mechanism.
2. Backend stores metadata and creates a job.
3. Job starts with status `queued`.
4. Worker retrieves video from object storage.
5. Worker extracts frames or pose data.
6. Worker runs squat-specific analysis.
7. Worker stores structured result.
8. Backend exposes job status and result.
9. Frontend polls the job status endpoint until completion, failure, or expiry.

The first async video implementation should use polling, not SSE or WebSockets. A reasonable starting point is `GET /api/v0/video/jobs/{job_id}` every 2-5 seconds with a retry limit and job expiry. SSE or WebSockets may replace polling later only if production requirements justify persistent connections.

Job states:

- `queued`
- `processing`
- `completed`
- `failed`
- `expired`

Video result contract should include:

- Movement type.
- Rep count or phase observations, if reliable.
- Frame-quality warnings.
- Technique observations.
- Confidence.
- Non-clinical feedback.
- Safety disclaimers.

MVP v0 must not implement this pipeline.

## Error Handling

Expected future error classes:

- Invalid upload.
- Unsupported file type.
- Low image or video quality.
- AI schema validation failure.
- AI provider timeout.
- Safety policy block.
- Job failure.

Errors should be user-readable without exposing internals.

## Testing and Evaluation Strategy

Future test layers:

- Unit tests for deterministic calorie recomputation.
- Schema validation tests.
- API contract tests.
- UI state tests for loading, error, correction, and low-confidence states.
- Prompt regression tests.
- Evaluation runs against fixed datasets.

AI evaluation should track:

- Valid JSON rate.
- Safety compliance.
- Estimate error after user correction.
- Low-confidence calibration.
- Regression by prompt version.
