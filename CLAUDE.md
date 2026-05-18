# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Repository Purpose

FitPlate Coach is a mobile-first web app concept for:

1. Food photo calorie estimation with uncertainty and user correction.
2. Exercise form feedback from short videos, starting with squat only.

The project should feel like a production-style portfolio project, not an AI toy. Favor explicit product decisions, structured contracts, safety boundaries, and a credible path from mock behavior to production AI workflows.

## Current Scope

The food photo mock analysis milestone is approved for implementation. Keep it limited to a metadata-only mock flow with a static file selection UI and a structured mock backend response.

Allowed now:

- Documentation.
- Repo rules.
- Product requirements.
- Architecture notes.
- AI safety constraints.
- Implementation planning.
- `apps/web`: Next.js, TypeScript, Tailwind home page only.
- `apps/api`: FastAPI backend with `GET /api/v0/health` only.
- `apps/web`: `/food/new` route for one-image metadata selection, local validation, mock result display, and inline error/loading states.
- `apps/api`: `POST /api/v0/food/analyze/mock` accepting JSON file metadata only.
- Backend tests for the mock food analysis endpoint.
- Real OpenAI calls only when explicitly requested and all required flags are set:
  `FITPLATE_AI_MODE=ai`, `FITPLATE_AI_PROVIDER=openai`, a server-side
  `FITPLATE_AI_PROVIDER_API_KEY`, and a local testing cost cap.

Do not create:

- Database schema.
- Auth flows.
- Unapproved real AI calls.
- Real image upload bytes or `multipart/form-data`.
- File storage.
- Video processing pipeline.
- Native mobile app.
- Docker.
- Extra UI libraries, shadcn, Supabase, or environment secrets.
- Frontend test framework.
- Correction UI or recompute endpoint.

Real AI remains forbidden unless the user explicitly approves that work for the
current task. Even when real AI is approved, do not add auth, a database, file
storage, video processing, async pipelines, or frontend real-AI UX redesign
unless those are separately requested.

## Transition to Implementation

When scaffolding or implementation is explicitly approved, update this file before creating code. The update should state which phase is now active, which artifacts are allowed, and which boundaries still apply.

Approval must be interpreted narrowly. Frontend approval does not automatically approve backend work; backend approval does not approve auth, a database, real AI calls, or video processing.

For MVP v0, keep these constraints unless the user explicitly changes them:

- No authentication.
- No database.
- No real AI API call.
- No video processing.
- No native mobile app.

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
- Separate mock analysis from real AI integration.
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
