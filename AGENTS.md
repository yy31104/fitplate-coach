# AGENTS.md

Guidance for Codex and other agentic coding assistants working in this repository.

## Project Identity

FitPlate Coach is a mobile-first web app for food photo calorie estimation and exercise form feedback. It should read as a production-style portfolio project: disciplined scope, clear safety boundaries, structured AI contracts, and practical architecture notes.

The MVP v0 is local-demo-ready and still intentionally small:

- Food photo analysis is implemented with deterministic mock behavior by default.
- A local fake AI provider exercises the AI adapter without network calls.
- Real OpenAI image analysis is available only for local demos behind explicit flags, a server-side key, and a cost cap.
- Squat feedback is documented as a future direction only.
- There is no authentication, database, persistent image storage, video pipeline, native mobile app, or production SaaS deployment.

## Current Repository Rule

The current repository state is local-demo-ready AI, not production SaaS. Keep all work inside the approved local demo boundary unless the user explicitly changes scope.

Implemented and allowed in the current phase:

- Governance files.
- Product documentation.
- Architecture documentation.
- Safety documentation.
- Implementation planning.
- `apps/web`: Next.js, TypeScript, Tailwind home page and `/food/new`.
- `apps/web`: one-image selection, local validation, metadata mock analysis, multipart upload transport, result display, grams correction UI, inline error/loading states, and Playwright E2E coverage.
- `apps/api`: FastAPI backend with `GET /api/v0/health`.
- `apps/api`: `POST /api/v0/food/analyze/mock` accepting JSON file metadata only.
- `apps/api`: `POST /api/v0/food/analyze` accepting one request-scoped multipart image, validating it, and discarding bytes without persistence.
- `apps/api`: `POST /api/v0/food/corrections/mock` returning deterministic `UserCorrection` data.
- Analyzer adapter boundary with `MockFoodAnalyzer`, `AIFoodAnalyzer`, `FakeAIProvider`, and `OpenAIProvider`.
- Real OpenAI path only when explicitly configured with `FITPLATE_AI_MODE=ai`, `FITPLATE_AI_PROVIDER=openai`, a server-side `FITPLATE_AI_PROVIDER_API_KEY`, and the monthly cost cap.
- Versioned prompt registry under `apps/api/prompts/`.
- Append-only local `model_run.v1` JSONL logs with summary fields only.
- Cost cap checks before real provider calls.
- Deterministic food-analysis evaluation cases and local evidence reports using mock and fake-provider paths only.
- Backend tests for health, food analysis, multipart upload, correction, analyzer/provider seams, cost cap, prompt registry, model-run logging, and evaluation.

Explicit boundaries for the current phase:

- Authentication.
- Database setup.
- Persistent image storage or object storage.
- Production SaaS hosting, deployment/IaC, public API exposure, abuse controls, billing, or multi-tenant operations.
- Video processing implementation.
- Docker.
- Extra UI libraries, shadcn, Supabase, or environment secrets.
- Frontend test framework.
- Real provider calls in CI.
- Real provider tests in CI.
- Unflagged or client-side AI provider calls.
- Raw image bytes, base64 payloads, API keys, raw provider responses, or full prompt bodies in logs.

## Transition to Implementation

When the user explicitly approves scaffolding or implementation, update this file before creating code. The update must name the approved phase, move only the approved work into the allowed list, and keep the remaining v0 prohibitions visible.

Approval for one layer does not imply approval for all layers. For example, approval to adjust deterministic evaluation does not approve authentication, a database, persistent media storage, production deployment, video processing, or new real-provider paths.

During MVP v0 implementation, preserve these rules unless the user explicitly changes scope:

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
- Root npm workspace scripts for web and API run/test commands.
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

## Engineering Principles

- Keep the app mobile-first, pragmatic, and portfolio-grade.
- Prefer typed, structured contracts over free-form text for AI-style outputs.
- Treat AI output as uncertain, user-correctable, and auditable.
- Preserve clear separation between product behavior, AI contracts, safety policy, and infrastructure.
- Avoid adding abstractions before the codebase needs them.
- Keep future production concerns visible: evaluation, prompt versioning, model run logs, cost tracking, privacy, and correction loops.

## Safety Boundaries

FitPlate Coach is not a medical device, dietitian, clinician, or physical therapist.

Do not implement or document behavior that:

- Diagnoses disease, eating disorders, injuries, or medical conditions.
- Gives treatment advice.
- Encourages extreme dieting, purging, dehydration, or unsafe weight loss.
- Presents calorie estimates as exact.
- Presents form feedback as a clinical or injury diagnosis.

Use language that supports reflection and safer habits, not prescriptive medical claims.

## AI Output Requirements

All future AI-facing features should use structured JSON schemas. Avoid relying on unstructured prose as the primary integration contract.

Food analysis outputs should include:

- Food item candidates.
- Portion assumptions.
- Calorie estimate ranges.
- Confidence or uncertainty.
- User correction fields.
- Safety flags where relevant.

Exercise feedback outputs should include:

- Movement type.
- Rep or phase observations.
- Confidence.
- Non-clinical technique cues.
- Safety disclaimers.
- Escalation guidance for pain or injury concerns.

## Working Style

- Read relevant docs before making changes.
- Keep edits tightly scoped to the requested files.
- Do not overwrite user work without checking current file contents.
- If implementation is requested later, update docs when architecture or safety assumptions change.
- Prefer concise, high-signal documentation over broad speculative detail.

## Verification

For the current local-demo-ready AI and M1 evidence milestone, verify with:

- `git status`
- `rg --files`
- `npm run test:api`
- `npm run lint:web`
- `npm run build:web`
- `npm run test:e2e`
- `npm run eval:api`

Confirm `apps/api/logs/model_runs.jsonl` is not staged. Do not add package manager or framework commands beyond the approved milestone scope.

## AI Agent Working Principles

- Think before coding: state assumptions, surface ambiguity, and ask before expanding scope.
- Simplicity first: implement the minimum code needed for the approved milestone.
- Surgical changes: touch only files required by the current task; no drive-by refactors.
- Goal-driven execution: every task must define verification commands and pass them before completion.
- If a task is ambiguous, stop and ask instead of guessing.
