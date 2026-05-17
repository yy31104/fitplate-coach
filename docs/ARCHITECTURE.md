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

The repository currently contains documentation and governance files only.

There is no application code, package manifest, framework scaffold, backend service, database, or dependency installation.

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
  -> Frontend polls or subscribes for status
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

## Food Analysis Contract

Food analysis should use structured JSON. A future schema should include:

```json
{
  "analysis_id": "string",
  "schema_version": "food_analysis.v1",
  "mode": "mock|ai",
  "items": [
    {
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
      "confidence": "low|medium|high"
    }
  ],
  "total_calories": {
    "min": 0,
    "max": 0,
    "point_estimate": 0
  },
  "uncertainty_notes": ["string"],
  "safety_flags": ["string"],
  "user_corrections": []
}
```

MVP v0 can use deterministic mock data that follows this shape. The schema should be treated as the product contract even before real AI exists.

## User Correction Loop

Corrections are a core product feature, not a secondary edit screen.

Future correction data should capture:

- Original item name and portion estimate.
- User-corrected item name or portion.
- Recomputed calories.
- Timestamp.
- Schema version.
- Prompt version, once real AI is introduced.
- Model identifier, once real AI is introduced.

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

## Model Run Logs

Future model run logs should include:

- Request id.
- User id, if auth exists.
- Analysis id.
- Prompt version.
- Schema version.
- Model and provider.
- Input media reference, not raw media.
- Output JSON.
- Validation result.
- Safety flags.
- Latency.
- Token usage, if applicable.
- Cost estimate.
- Error details.

Logs should avoid storing unnecessary sensitive data.

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

## Future Async Video Pipeline

Video processing should be async because files can be large and analysis can be slow.

Planned flow:

1. Frontend uploads video or requests a signed upload URL.
2. Backend stores metadata and creates a job.
3. Job starts with status `queued`.
4. Worker retrieves video from object storage.
5. Worker extracts frames or pose data.
6. Worker runs squat-specific analysis.
7. Worker stores structured result.
8. Backend exposes job status and result.
9. Frontend polls or receives updates.

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
