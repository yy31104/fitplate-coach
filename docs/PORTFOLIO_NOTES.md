# FitPlate Coach Portfolio Engineering Summary

FitPlate Coach is a local-demo-ready, portfolio-grade food analysis project. It
is not production SaaS and it is not medical nutrition advice. The codebase is
designed to show how an AI-assisted product can be structured around contracts,
observability, cost controls, safety boundaries, and testability instead of a
single prompt wired directly to a UI.

## What This Project Demonstrates

- A Next.js frontend paired with a FastAPI backend in a small monorepo.
- A food analysis flow that supports both metadata-only mock analysis and
  multipart image upload analysis.
- A correction UI and backend correction endpoint for updating item grams and
  recomputing calorie ranges.
- Schema-first API design with explicit `FoodAnalysis`, `FoodItem`,
  `UserCorrection`, `SafetyFlag`, and `ModelRun` contracts.
- Local-demo-ready real OpenAI image analysis behind feature flags, while mock
  mode remains the default.
- Production-style boundaries without adding production infrastructure too
  early.

## Architecture Overview

The frontend lives in `apps/web` and uses Next.js, TypeScript, and Tailwind. The
backend lives in `apps/api` and uses FastAPI with Pydantic schemas.

The backend exposes a metadata-only mock route,
`POST /api/v0/food/analyze/mock`, and a multipart upload route,
`POST /api/v0/food/analyze`. Both return the same `FoodAnalysis` response
shape. The correction endpoint, `POST /api/v0/food/corrections/mock`, returns a
`UserCorrection` and keeps the correction computation server-side.

The food analyzer is selected through an adapter boundary. `MockFoodAnalyzer`
keeps deterministic local behavior. `AIFoodAnalyzer` uses an `AIProvider` seam
so fake and real providers can be exercised independently. `FakeAIProvider`
supports deterministic tests and evaluations. `OpenAIProvider` is the first
real provider implementation.

The evaluation runner can exercise `FakeAIProvider` against fixed food-analysis
cases, which gives deterministic AI-path coverage without real API calls.

## Real AI Provider Path

Real AI is opt-in through environment variables:

- `FITPLATE_AI_MODE=ai`
- `FITPLATE_AI_PROVIDER=openai`
- `FITPLATE_AI_PROVIDER_API_KEY`

The default path remains mock mode, so normal local development and CI do not
make provider calls or spend money.

The OpenAI path uses the Responses API with image input and structured JSON
output. The provider receives request-scoped image bytes through `ImageRef`,
base64-encodes them only inside the provider call, and returns structured data
for backend validation. The backend controls identity and timing fields such as
`analysis_id`, `schema_version`, `mode`, and `analyzed_at`.

## Observability And Cost Controls

Food analysis and correction routes append `model_run.v1` records to local JSONL
logs. Each record captures route, mode, model, prompt name/version, latency,
input summary, output summary, safety flags, token usage, cost, and error
fields.

The logs are summary-only. They do not store image bytes, base64 payloads, API
keys, raw provider responses, or full prompt bodies.

The backend checks a monthly cost cap from the model-run JSONL file before real
provider calls. A cap of `0.0` disables enforcement for local development; the
runbook recommends setting a small cap before real AI testing.

## Testing And CI

The backend has pytest coverage for health checks, mock analysis, multipart
upload, correction recomputation, analyzer selection, provider behavior, cost
cap logic, evaluation cases, and model-run logging.

The real OpenAI smoke test is marked `real_provider` and skips by default unless
both an API key and `FITPLATE_RUN_REAL_PROVIDER_TEST=1` are set. This keeps CI
free of provider calls and API cost.

The frontend has Playwright E2E coverage for the `/food/new` flow, including
file validation, analysis display, correction editing, and upload transport.
GitHub Actions runs web lint, web build, backend tests, and E2E tests.

## Privacy And Safety Boundaries

- Image bytes are not written to logs.
- API keys are never logged, returned, or committed.
- Uploaded image bytes are request-scoped and are not persisted.
- Model-run logs contain summaries only.
- Local CORS allows both `http://127.0.0.1:3000` and
  `http://localhost:3000` for developer ergonomics.
- Calorie estimates are ranges, not exact claims.
- The app does not present medical, dietary, or clinical advice.

## Intentional Non-Goals

- No authentication.
- No database.
- No image storage or object storage.
- No deployment configuration.
- No video pipeline.
- No production multi-provider routing.
- No retry or streaming policy.
- No claim of medically reliable nutrition advice.

These are deliberately out of scope so the project can focus on product
contracts, provider boundaries, observability, evaluation, and local demo
safety.

## Interview Talking Points

- Designed adapter boundaries so mock, fake, and real providers can be tested
  separately.
- Added opt-in real-provider smoke testing so CI never spends API money.
- Logged token, cost, latency, route, mode, model, and prompt metadata without
  storing image bytes or secrets.
- Used E2E tests to protect the upload and correction flow.
- Kept real AI behind feature flags and a monthly cost cap.
- Preserved one `FoodAnalysis` contract across mock, fake, and real provider
  paths.
- Versioned prompts and fixed evaluation cases before treating provider output
  as production behavior.
- Treated user corrections as first-class product data rather than a UI-only
  patch.
- Chose explicit non-goals instead of prematurely adding auth, database,
  storage, deployment, or video infrastructure.
