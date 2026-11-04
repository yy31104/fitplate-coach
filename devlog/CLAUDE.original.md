# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Repository Purpose

FitPlate Coach is a mobile-first web app concept for:

1. Food photo calorie estimation with uncertainty and user correction.
2. Exercise form feedback from short videos, starting with squat only.

The project should feel like a production-style portfolio project, not an AI toy. Favor explicit product decisions, structured contracts, safety boundaries, and a credible path from mock behavior to production AI workflows.

## Current Scope

The current repository state is local-demo-ready AI, not production SaaS. Default behavior is deterministic mock analysis; the fake provider exercises the AI adapter without network calls; real OpenAI image analysis is local-demo-only behind explicit flags, a server-side API key, and a cost cap.

Implemented and allowed now:

- Documentation.
- Repo rules.
- Product requirements.
- Architecture notes.
- AI safety constraints.
- Implementation planning.
- `apps/web`: Next.js, TypeScript, Tailwind home page and `/food/new`.
- `apps/web`: one-image selection, local validation, mock analysis display, multipart upload transport, grams correction UI, inline error/loading states, and Playwright E2E coverage.
- `apps/api`: FastAPI backend with `GET /api/v0/health`.
- `apps/api`: `POST /api/v0/food/analyze/mock` accepting JSON file metadata only.
- `apps/api`: `POST /api/v0/food/analyze` accepting one request-scoped multipart image, validating it, and discarding bytes without persistence.
- `apps/api`: `POST /api/v0/food/corrections/mock` returning deterministic `UserCorrection` data.
- Analyzer adapter boundary with mock, fake AI, and OpenAI provider implementations.
- Versioned prompt registry under `apps/api/prompts/`.
- Append-only local `model_run.v1` JSONL logs with summary fields only.
- Monthly cost cap checks before real provider calls.
- Deterministic food-analysis evaluation cases and local evidence reports using mock and fake-provider paths only.
- Backend tests for the mock food analysis endpoint.
- Real OpenAI calls only when explicitly requested and all required flags are set:
  `FITPLATE_AI_MODE=ai`, `FITPLATE_AI_PROVIDER=openai`, a server-side
  `FITPLATE_AI_PROVIDER_API_KEY`, and a local testing cost cap.

Do not create:

- Authentication flows.
- Database schema.
- Persistent image storage or object storage.
- Production SaaS hosting, deployment/IaC, public API exposure, abuse controls, billing, or multi-tenant operations.
- Video processing pipeline.
- Native mobile app.
- Docker.
- Extra UI libraries, shadcn, Supabase, or environment secrets.
- Frontend test framework.
- Real provider calls in CI.
- Real provider tests in CI.
- Unflagged or client-side AI provider calls.
- Raw image bytes, base64 payloads, API keys, raw provider responses, or full prompt bodies in logs.

Real AI remains forbidden unless the user explicitly approves that work for the
current task. Even when real AI is approved, it remains local-demo-only behind
flags, server-side key handling, and cost controls. Do not add auth, a database,
persistent file storage, video processing, async pipelines, production hosting,
or frontend real-AI UX redesign unless those are separately requested.

## Transition to Implementation

When scaffolding or implementation is explicitly approved, update this file before creating code. The update should state which phase is now active, which artifacts are allowed, and which boundaries still apply.

Approval must be interpreted narrowly. Frontend approval does not automatically approve backend work; backend approval does not approve auth, a database, real AI calls, or video processing.

For MVP v0, keep these constraints unless the user explicitly changes them:

- No authentication.
- No database.
- No real AI in CI.
- Real AI is local-demo-only behind explicit flags, a server-side key, and a cost cap.
- No video processing.
- No native mobile app.
- No production SaaS scope.

Approved first code milestone:

- Minimal monorepo structure only.
- `apps/web`: Next.js, TypeScript, Tailwind home page only.
- `apps/api`: FastAPI backend with `GET /api/v0/health` only.
- Root npm workspace scripts for running and testing the web and API apps.
- No frontend API integration yet.
- No upload flow, food analysis mock, correction loop, AI, database, auth, or video routes.

Approved food photo mock analysis milestone:

- Frontend route: `/food/new`.
- Backend endpoint: `POST /api/v0/food/analyze/mock`.
- Frontend sends JSON metadata only: filename, content type, size in bytes, and last modified time.
- Backend returns mocked `FoodAnalysis` JSON with `mode: "mock"` and `schema_version: "food_analysis.v1"`.
- Frontend displays calorie ranges, items, confidence, assumptions, safety flags, and a calm nutrition disclaimer.
- No real file upload, storage, AI, database, auth, video processing, Docker, extra UI library, correction UI, or recompute endpoint.

Approved local-demo AI milestone:

- Multipart `POST /api/v0/food/analyze` with request-scoped bytes only.
- Mock correction endpoint and frontend grams correction flow.
- Analyzer adapter with mock, fake AI, and OpenAI provider implementations.
- Versioned prompt registry and prompt log.
- Summary-only `model_run.v1` JSONL logging.
- Monthly cost cap for real provider calls.
- Real OpenAI provider local-demo-only behind flags and server-side key.
- No real provider calls in CI and no production SaaS expansion.

Approved M1 eval/privacy/governance milestone:

- Align governance docs with implemented local-demo-ready AI state.
- Add `docs/DATA_MAP.md`.
- Add deterministic local evaluation evidence using only mock analyzer and `FakeAIProvider`.
- Add `npm run eval:api` and CI evaluation step without OpenAI credentials.

## Planned Stack

The intended future stack is:

- Frontend: Next.js, TypeScript, mobile-first responsive UI.
- Backend: FastAPI, Python.
- AI integration: structured JSON outputs with versioned prompts and logged model runs.
- Future async processing: job queue and object storage for video workflows.
- Future persistence: database for users, analyses, corrections, model runs, and evaluation data.

These are documented intentions, not current implementation requirements.

## Product Principles

- Show uncertainty clearly.
- Invite user correction instead of pretending AI estimates are exact.
- Keep AI output structured and auditable.
- Separate mock analysis, fake-provider tests/evals, and local-demo real AI integration.
- Keep safety language visible but calm.
- Treat privacy, cost, evaluation, and observability as first-class production concerns.

## Safety Rules

FitPlate Coach must not provide medical diagnosis, treatment advice, injury diagnosis, or extreme dieting guidance.

Use safe wording:

- "Estimate" instead of "exact calories."
- "May help you reflect" instead of "you should."
- "Consider a qualified professional if you have pain or medical concerns" instead of diagnosing.

Avoid unsafe wording:

- Claims that the system can detect eating disorders, injuries, or disease.
- Specific treatment plans.
- Extreme calorie targets.
- Promises of rapid weight loss.
- Exercise feedback that claims to prevent or diagnose injury.

## AI Contract Expectations

Future AI outputs should be schema-first JSON with explicit uncertainty. Free-form generated text may be used for user-facing summaries, but only after structured data is available.

Document prompt changes, schema changes, and model behavior changes. Future production work should include:

- Prompt versioning.
- Model run logs.
- Evaluation sets.
- Cost tracking.
- User correction loops.
- Privacy review.

## Working Instructions

- Before editing, inspect the relevant file contents.
- Preserve existing user work.
- Keep documentation consistent across README, PRD, architecture, safety, and implementation plan.
- Do not introduce code or dependencies unless the user explicitly asks for implementation.
- When implementation begins later, keep mock behavior clearly separate from production AI integration.

## AI Agent Working Principles

- Think before coding: state assumptions, surface ambiguity, and ask before expanding scope.
- Simplicity first: implement the minimum code needed for the approved milestone.
- Surgical changes: touch only files required by the current task; no drive-by refactors.
- Goal-driven execution: every task must define verification commands and pass them before completion.
- If a task is ambiguous, stop and ask instead of guessing.
