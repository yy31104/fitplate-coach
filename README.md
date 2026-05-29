[![CI](https://github.com/yy31104/fitplate-coach/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/yy31104/fitplate-coach/actions/workflows/ci.yml)

# FitPlate Coach

FitPlate Coach is a mobile-first food photo calorie estimation app that treats AI-style output as uncertain, structured, and user-correctable instead of pretending a model can return exact nutrition facts.

## Project Overview

The current app lets a user select one food image in the browser. The default development flow uses deterministic mock and fake-provider paths, while an explicit local upload flow can send image bytes to the backend for analysis. The backend returns a structured `FoodAnalysis` JSON response with food items, portion assumptions, calorie ranges, confidence levels, and safety flags.

After the mock result appears, the user can correct an item's portion in grams. The backend mock correction endpoint recomputes that item's calorie range from corrected grams, the original calorie density, and the original confidence margin, then the frontend updates the display from the returned `UserCorrection`.

Real OpenAI image analysis is available for local demos behind explicit feature flags and a server-side API key. Normal CI does not call OpenAI or spend API money, and the project remains local-demo-ready rather than production SaaS.

## Engineering Discipline Over Demo Shortcuts

- **Schema-first AI contract:** `FoodAnalysis` is a versioned JSON-shaped contract with `schema_version: "food_analysis.v1"`, `mode`, `confidence`, `uncertainty_notes`, `safety_flags`, and `user_corrections`.
- **Uncertainty is explicit:** calorie estimates are ranges with `min`, `max`, and `point_estimate`. Confidence maps to deterministic range widths instead of vague prose.
- **Mock mode is observable:** the endpoint is explicitly named `POST /api/v0/food/analyze/mock`, and every response includes `mode: "mock"`.
- **Corrections are product data:** `UserCorrection` records original and corrected values, timestamps, item IDs, and source. In v0 it stays in React state; later it becomes evaluation data.
- **Model runs are observable:** current mock food routes append summary-only `model_run.v1` records to local JSONL logs without storing raw media or full responses.
- **Prompts and evals are versioned early:** the food-analysis prompt registry and fixed evaluation cases are in place before production AI is treated as default behavior.
- **Safety is typed:** safety flags are named schema values, not unstructured UI copy.
- **CI checks the basics:** GitHub Actions runs web lint, web build, backend API tests, deterministic API evaluation, and Playwright E2E tests on every push.

## Current Features

- `/food/new` mobile-first food photo selection flow.
- Local validation for image type, size, and empty files.
- Metadata-only request containing filename, content type, size in bytes, and last modified time.
- `POST /api/v0/food/analyze/mock` returning structured mock `FoodAnalysis` JSON.
- `POST /api/v0/food/analyze` accepting one request-scoped multipart image without persistence.
- Food item display with portion estimates, calorie ranges, confidence, assumptions, and safety flags.
- Grams-only correction flow with original estimate preserved beside the corrected estimate.
- `POST /api/v0/food/corrections/mock` recomputing corrected calorie ranges from corrected grams, original density, and confidence margin.
- Append-only JSONL model run logs for food mock analysis and correction routes.
- Deterministic local evaluation evidence for mock and fake-provider paths.
- GitHub Actions CI for `npm run lint:web`, `npm run build:web`, `npm run test:api`, `npm run eval:api`, and `npm run test:e2e`.

## Architecture

FitPlate Coach is a small monorepo:

- `apps/web`: Next.js frontend using TypeScript and Tailwind.
- `apps/api`: FastAPI backend using Pydantic models.

The browser can send JSON metadata to the mock endpoint or one multipart image to the upload endpoint. API routes are versioned under `/api/v0/`, and `FoodAnalysis` is the integration contract between the frontend and backend.

Correction recomputation is handled by the backend mock correction endpoint. It uses `calorie_density_kcal_per_gram`, corrected grams, and the original confidence margin for high, medium, or low confidence. CORS allows `http://127.0.0.1:3000` and `http://localhost:3000` in local development.

For the full system design, see [Architecture](docs/ARCHITECTURE.md).

## Safety And Privacy Boundaries

FitPlate Coach is not a medical device and does not provide medical, dietary, clinical, or treatment advice.

The system is designed not to:

- Claim exact calorie counts.
- Diagnose eating disorders, injuries, or medical conditions.
- Provide treatment plans.
- Encourage extreme dieting, dehydration, purging, or overtraining.
- Process images classified as sensitive or NSFW.

Privacy in v0 is deliberately narrow: metadata-only mock requests send no image bytes, multipart upload bytes are request-scoped and discarded, and there are no user accounts, database persistence, session storage, or analytics.

The future exercise feedback track follows the same safety policy: non-clinical technique cues only, with escalation language for pain or injury concerns.

## What The AI Layer Will And Will Not Do

Default development mode is mock. The backend can return deterministic structured data without calling a paid provider, and fake-provider paths exercise the AI adapter without network calls.

Real OpenAI analysis is available behind explicit local feature flags, a server-side API key, and cost controls. Normal CI does not call OpenAI or spend API money.

Real and mock paths use the same `FoodAnalysis` schema. Estimates should still be ranges, not exact numbers, and user corrections should continue to use the same `UserCorrection` contract.

## Tech Stack

- **Frontend:** Next.js 16, TypeScript, Tailwind CSS. App Router, mobile-first UI, no component library dependency.
- **Backend:** FastAPI, Python 3.12, Pydantic. Pydantic models define request and response contracts.
- **Monorepo:** npm workspaces at the root, with a Python virtual environment in `apps/api/.venv`.
- **CI:** GitHub Actions with Node 22 and Python 3.12.

No database, authentication, upload storage, Docker, video processing, or production deployment exists in v0. The real AI provider path is local-demo-only behind explicit flags, a server-side key, and cost controls.

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
npm run eval:api
npm run test:e2e
```

CI runs the same commands on every push and on pull requests to `main`. See [.github/workflows/ci.yml](.github/workflows/ci.yml).

The backend currently has pytest coverage for health, mock food analysis, multipart upload, mock correction, analyzer/provider seams, cost cap, prompt registry, model run logging, and evaluation. Playwright E2E covers the current `/food/new` browser flow with mocked API calls.

## Current Limitations

- **Mock-first development:** normal development and CI use deterministic mock and fake-provider paths; production image recognition is not enabled by default.
- **No persistence:** analyses and corrections live in React state. A page reload clears them.
- **No authentication:** API requests are not associated with users.
- **No production image content analysis:** default mock and fake-provider paths do not verify whether the selected image actually contains food. Real OpenAI image analysis is local-demo-only.
- **Grams-only correction:** users can correct portion size in grams, but not the food name. Name correction needs a density lookup flow.
- **No exercise feedback:** squat video feedback is documented as a future track but not implemented.

## Roadmap

Next:

- M1 eval/privacy/governance evidence: deterministic evaluation report, data map, and governance alignment.
- Keep real AI local-demo-only while privacy, auth, storage, and production controls remain deferred.

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
- [Portfolio Engineering Summary](docs/PORTFOLIO_NOTES.md)
- [Portfolio Walkthrough](docs/PORTFOLIO_WALKTHROUGH.md)
- [API Contract](docs/API_CONTRACT.md)
- [Architecture](docs/ARCHITECTURE.md)
- [AI Safety](docs/AI_SAFETY.md)
- [Data Map](docs/DATA_MAP.md)
- [Evaluation Maintenance Runbook](docs/runbooks/eval-maintenance.md)
- [Real AI Local Runbook](docs/runbooks/real-ai-local.md)
- [Implementation Plan](docs/IMPLEMENTATION_PLAN.md)
