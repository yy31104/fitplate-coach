[![CI](https://github.com/yy31104/fitplate-coach/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/yy31104/fitplate-coach/actions/workflows/ci.yml)

# FitPlate Coach

FitPlate Coach is a mobile-first food photo calorie estimation app that treats AI-style output as uncertain, structured, and user-correctable instead of pretending a model can return exact nutrition facts.

## Project Overview

The current app lets a user select one food image in the browser. The frontend validates the file locally, sends metadata only to the backend, and never uploads or stores image bytes. The backend returns a deterministic mock `FoodAnalysis` JSON response with food items, portion assumptions, calorie ranges, confidence levels, and safety flags.

After the mock result appears, the user can correct an item's portion in grams. The backend mock correction endpoint recomputes that item's calorie range from corrected grams, the original calorie density, and the original confidence margin, then the frontend updates the display from the returned `UserCorrection`.

There is no real model call yet. That is intentional: the project is built around the production contract first, so a future AI integration can sit behind the same schema and safety boundaries instead of forcing a UI rewrite.

## Engineering Discipline Over Demo Shortcuts

- **Schema-first AI contract:** `FoodAnalysis` is a versioned JSON-shaped contract with `schema_version: "food_analysis.v1"`, `mode`, `confidence`, `uncertainty_notes`, `safety_flags`, and `user_corrections`.
- **Uncertainty is explicit:** calorie estimates are ranges with `min`, `max`, and `point_estimate`. Confidence maps to deterministic range widths instead of vague prose.
- **Mock mode is observable:** the endpoint is explicitly named `POST /api/v0/food/analyze/mock`, and every response includes `mode: "mock"`.
- **Corrections are product data:** `UserCorrection` records original and corrected values, timestamps, item IDs, and source. In v0 it stays in React state; later it becomes evaluation data.
- **Model runs are observable:** current mock food routes append summary-only `model_run.v1` records to local JSONL logs without storing raw media or full responses.
- **Prompts and evals are versioned early:** a future food-analysis prompt registry and fixed mock evaluation cases are in place before any real AI provider call exists.
- **Safety is typed:** safety flags are named schema values, not unstructured UI copy.
- **CI checks the basics:** GitHub Actions runs web lint, web build, backend API tests, and Playwright E2E tests on every push.

## Current Features

- `/food/new` mobile-first food photo selection flow.
- Local validation for image type, size, and empty files.
- Metadata-only request containing filename, content type, size in bytes, and last modified time.
- `POST /api/v0/food/analyze/mock` returning structured mock `FoodAnalysis` JSON.
- Food item display with portion estimates, calorie ranges, confidence, assumptions, and safety flags.
- Grams-only correction flow with original estimate preserved beside the corrected estimate.
- `POST /api/v0/food/corrections/mock` recomputing corrected calorie ranges from corrected grams, original density, and confidence margin.
- Append-only JSONL model run logs for food mock analysis and correction routes.
- GitHub Actions CI for `npm run lint:web`, `npm run build:web`, `npm run test:api`, and `npm run test:e2e`.

## Architecture

FitPlate Coach is a small monorepo:

- `apps/web`: Next.js frontend using TypeScript and Tailwind.
- `apps/api`: FastAPI backend using Pydantic models.

The browser sends JSON metadata to the API; it does not send multipart image data in v0. API routes are versioned under `/api/v0/`, and `FoodAnalysis` is the integration contract between the frontend and backend.

Correction recomputation is handled by the backend mock correction endpoint. It uses `calorie_density_kcal_per_gram`, corrected grams, and the original confidence margin for high, medium, or low confidence. CORS is restricted to `http://127.0.0.1:3000` in local development.

For the full system design, see [Architecture](docs/ARCHITECTURE.md).

## Safety And Privacy Boundaries

FitPlate Coach is not a medical device and does not provide medical, dietary, clinical, or treatment advice.

The system is designed not to:

- Claim exact calorie counts.
- Diagnose eating disorders, injuries, or medical conditions.
- Provide treatment plans.
- Encourage extreme dieting, dehydration, purging, or overtraining.
- Process images classified as sensitive or NSFW.

Privacy in v0 is deliberately narrow: image bytes are never sent to the backend or stored. There are no user accounts, no database persistence, no session storage, and no analytics.

The future exercise feedback track follows the same safety policy: non-clinical technique cues only, with escalation language for pain or injury concerns.

## What The AI Layer Will And Will Not Do

Current mode is mock. The backend returns deterministic structured data derived from request metadata; no AI provider is called.

The next AI-related work is AI-readiness, not simply "turn on a model." Before a real multimodal endpoint exists, the project needs prompt versioning, model run logging, an evaluation set, and cost tracking.

A later real endpoint can return `mode: "ai"` using the same `FoodAnalysis` schema. Estimates should still be ranges, not exact numbers, and user corrections should continue to use the same `UserCorrection` contract.

## Tech Stack

- **Frontend:** Next.js 16, TypeScript, Tailwind CSS. App Router, mobile-first UI, no component library dependency.
- **Backend:** FastAPI, Python 3.12, Pydantic. Pydantic models define request and response contracts.
- **Monorepo:** npm workspaces at the root, with a Python virtual environment in `apps/api/.venv`.
- **CI:** GitHub Actions with Node 22 and Python 3.12.

No database, authentication, AI provider, upload storage, Docker, or video processing exists in v0. Those are deferred until the schema contract and correction loop are stable.

## Local Development

Prerequisites:

- Node 22 or newer.
- Python 3.12.

Install frontend dependencies:

```bash
npm ci
```

Create the backend virtual environment and install API dependencies:

```bash
python -m venv apps/api/.venv
apps/api/.venv/bin/python -m pip install -e "apps/api[dev]"
```

Run the frontend:

```bash
npm run dev:web
```

Frontend URL:

```text
http://127.0.0.1:3000
```

Run the backend:

```bash
npm run dev:api
```

Backend URL:

```text
http://127.0.0.1:8000
```

Health check:

```bash
curl http://127.0.0.1:8000/api/v0/health
```

Expected response:

```json
{"status":"ok","service":"fitplate-api","version":"0.1.0"}
```

Food mock analysis:

```text
http://127.0.0.1:3000/food/new
```

Real AI is opt-in and requires explicit local environment configuration. See
[Real AI Local Runbook](docs/runbooks/real-ai-local.md) before using the OpenAI
path locally.

## Tests And CI

Run all checks:

```bash
npm run lint:web
npm run build:web
npm run test:api
npm run test:e2e
```

CI runs the same commands on every push and on pull requests to `main`. See [.github/workflows/ci.yml](.github/workflows/ci.yml).

The backend currently has pytest coverage for health, mock food analysis, mock correction, and model run logging. Playwright E2E covers the current `/food/new` browser flow with mocked API calls.

## Current Limitations

- **Mock analysis only:** calorie values come from deterministic mock scenarios and a small static density table, not from image recognition or nutrition databases.
- **No persistence:** analyses and corrections live in React state. A page reload clears them.
- **No authentication:** API requests are not associated with users.
- **No image content analysis:** the backend receives metadata only and cannot verify whether the selected image actually contains food.
- **Grams-only correction:** users can correct portion size in grams, but not the food name. Name correction needs a density lookup flow.
- **No exercise feedback:** squat video feedback is documented as a future track but not implemented.

## Roadmap

Next:

- AI-readiness work: prompt versioning, model run logging, evaluation examples, and cost tracking.
- A separate real multimodal food analysis endpoint that can return `mode: "ai"` without changing the `FoodAnalysis` contract.

Near-term:

- Database storage for analyses, corrections, and model runs.
- Authentication for associating analyses with users.
- Food name correction with density lookup by corrected name.
- Image upload and storage design with explicit retention rules.

Future:

- Squat video feedback with short video upload, frame extraction, structured form analysis JSON, and non-clinical technique cues.
- Evaluation dashboard for correction rate, confidence calibration, and model comparison across prompt versions.
- Async job queue for video processing.

## Why This Codebase Is Structured This Way

The `FoodAnalysis` response schema was defined before the UI depended on it. The frontend TypeScript types and backend Pydantic models use the same field names and versioning, so a future model integration does not change the frontend contract.

The mock endpoint is explicitly named, and `mode` is present in every response. Mock behavior is visible at runtime rather than hidden behind deployment configuration.

User corrections are modeled as first-class data with item IDs, original values, corrected values, timestamps, and a source field. That matters because corrections are the strongest signal for evaluating and improving food estimation.

Calorie estimates are ranges by design. Returning `min`, `max`, and `point_estimate` forces the product to represent uncertainty directly, and the backend mock analysis and correction paths use the same confidence margins.

Safety flags are typed schema values. A backend can emit a safety flag and the frontend can respond structurally, which leaves room for future moderation and safety classifiers without changing the UI contract.

## Documentation Map

- [Product Requirements](docs/PRD.md)
- [API Contract](docs/API_CONTRACT.md)
- [Architecture](docs/ARCHITECTURE.md)
- [AI Safety](docs/AI_SAFETY.md)
- [Real AI Local Runbook](docs/runbooks/real-ai-local.md)
- [Implementation Plan](docs/IMPLEMENTATION_PLAN.md)
