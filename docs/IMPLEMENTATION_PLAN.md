# Implementation Plan

## Phase 0: Project Foundation

Status: complete.

Goals:

- Establish repository governance.
- Define product scope.
- Define architecture direction.
- Define AI safety boundaries.
- Define implementation milestones.

Deliverables:

- `.gitignore`
- `AGENTS.md`
- `CLAUDE.md`
- `README.md`
- `docs/PRD.md`
- `docs/ARCHITECTURE.md`
- `docs/AI_SAFETY.md`
- `docs/IMPLEMENTATION_PLAN.md`

Exit criteria:

- A reviewer can understand the project without application code.
- MVP v0 boundaries are explicit.
- Future production AI concerns are documented.

## Phase 1: MVP v0 Implementation

Status: complete for the approved local-demo MVP.

The minimal scaffold, food photo mock flow, multipart upload transport,
correction loop, analyzer adapter, fake-provider path, local-demo OpenAI seam,
prompt registry, model-run logging, cost cap, and deterministic evaluation cases
have been delivered.

This phase still preserves the v0 rule: no auth, no database, no persistent
image storage, no video processing, no native mobile app, no production SaaS
scope, and no real provider calls in CI. Real AI is local-demo-only behind
explicit flags, a server-side key, and a cost cap.

Goals:

- Create a mobile-first Next.js app.
- Build the first user-facing food photo flow.
- Keep all analysis mocked.
- Make the frontend-to-backend handoff explicit without expanding scope.

Delivered tasks:

1. Transition governance:
   - Update `AGENTS.md`, `CLAUDE.md`, and this plan to show that the approved implementation phase has started.
   - Keep the not-allowed list explicit: no auth, database, persistent storage, video processing, production SaaS, or real provider calls in CI.
2. Minimal monorepo scaffold:
   - Create `apps/web` with Next.js, TypeScript, Tailwind, and a static home page only.
   - Create `apps/api` with FastAPI and `GET /api/v0/health` only.
   - Add root run/test scripts.
   - Do not add frontend API calls, uploads, AI, auth, database, video processing, Docker, or extra UI libraries.
3. Frontend shell with hardcoded mock data:
   - Add `/food/new`.
   - Add mobile-first one-image selection UI.
   - Validate file metadata locally.
   - Send JSON metadata only to `POST /api/v0/food/analyze/mock`.
   - Display structured mock analysis results from the backend.
   - Do not upload image bytes or use storage.
4. Frontend correction loop:
   - Use the canonical correction object from [Architecture](ARCHITECTURE.md#correction-object-sub-schema).
   - Use the deterministic mock recomputation algorithm from [Architecture](ARCHITECTURE.md#mock-calorie-recalculation).
   - Display rounded calorie ranges.
   - Add uncertainty and safety copy.
5. Backend mock and upload boundary:
   - Add `POST /api/v0/food/analyze/mock` as the metadata-only deterministic endpoint.
   - Add `POST /api/v0/food/analyze` as the request-scoped multipart upload transport.
   - Return the same structured `FoodAnalysis` shape from both routes.
   - Validate supported media metadata and basic file constraints.
   - Keep accepted bytes in memory for request scope only; do not persist media.
6. Frontend/backend handoff:
   - Replace hardcoded frontend analysis with backend calls.
   - Keep deterministic mock behavior identical across frontend and backend.
   - Preserve local-only correction state unless persistence is separately approved.
7. Real-AI seam for local demo:
   - Add analyzer adapter boundary.
   - Add `MockFoodAnalyzer`, `AIFoodAnalyzer`, `FakeAIProvider`, and `OpenAIProvider`.
   - Add prompt registry and `food_analysis` prompt `v1`.
   - Add summary-only `model_run.v1` JSONL logs.
   - Add monthly cost cap checks before real provider calls.
   - Keep OpenAI local-demo-only behind flags, server-side key, and cost cap.
8. Product polish:
   - Add low-confidence and unclear-image states.
   - Add accessible loading and error states.
   - Add documentation updates for any schema changes.
   - Add focused pytest and Playwright coverage.

Exit criteria:

- User can select an image and see a mock result.
- User can correct food items or portions.
- The result display uses structured mock data.
- Frontend-only mock behavior and backend mock behavior follow the same documented schema and recomputation rule.
- No real provider call runs in CI.
- Local-demo real AI requires explicit flags, a server-side key, and the cost cap.
- MVP v0 can be demoed end to end.
- Mock status is clear to users and reviewers.
- Safety boundaries are visible in the experience.
- Documentation matches the implemented behavior.

## Phase 2: v1 Persistence Preparation

Do not implement persistence in MVP v0.

Goals:

- Prepare for v1 data storage without prematurely expanding scope.

Candidate tasks:

- Design database entities for analyses and corrections.
- Document retention policy.
- Add migration tooling only when backend persistence is approved.
- Add privacy notes to user-facing copy.

Candidate entities:

- FoodAnalysis.
- FoodItemEstimate.
- UserCorrection.

Deferred entities:

- User, once auth exists.
- PromptVersion, once real AI exists.
- ModelRun, once real AI exists.
- EvaluationExample, once persisted corrections and consent rules exist.

Exit criteria:

- Storage design supports correction loops and evaluation.
- No raw media is stored in logs.
- Retention and deletion assumptions are documented.

## Phase 3: Real AI Food Analysis v1

Status: partially delivered as a local-demo seam; production v1 remains deferred.

Goals:

- Replace mock food analysis with a real AI provider behind the same service boundary.
- Preserve structured outputs and safety checks.

Delivered local-demo pieces:

- AI provider adapter.
- Prompt template and prompt registry.
- Prompt versioning for `food_analysis` `v1`.
- `FoodAnalysis` schema validation for provider output.
- Summary-only model run logging.
- Token, cost, and latency fields in `model_run.v1`.
- Cost cap before real provider calls.
- Fallback error handling for invalid provider output.
- Small deterministic evaluation set using mock and fake-provider paths.

Still deferred for production v1:

- Authenticated user flows.
- Database persistence for analyses, corrections, model runs, or evaluation data.
- Persistent media storage.
- Public deployment, abuse controls, rate limits, and operational monitoring.
- CI real-provider tests.
- Production prompt promotion workflow.

Exit criteria:

- AI output passes schema validation.
- Prompt and model versions are logged.
- Cost per analysis is visible.
- Safety checks can block or soften unsafe output.
- User corrections are stored for future evaluation.

## M1: Eval, Privacy, and Governance Evidence

Status: delivered in the M1 PR.

Goals:

- Align governance docs with the implemented local-demo-ready AI state.
- Document current data handling, logging, retention, deletion/export triggers, and boundaries.
- Produce deterministic local evaluation evidence without credentials or real provider calls.
- Add CI coverage for the deterministic evaluation command.

Deliverables:

- `AGENTS.md` and `CLAUDE.md` reflect multipart upload, mock corrections, analyzer adapter, fake and OpenAI providers, prompt registry, `model_run.v1` logs, cost cap, and eval cases.
- `docs/DATA_MAP.md`.
- `apps/api/app/evaluation/__main__.py`.
- `docs/evaluation/REPORT.md`.
- `apps/api/evaluation/report.json`.
- Root `npm run eval:api`.
- CI step running `npm run eval:api` after API tests.

Boundaries:

- Evaluation pins `MockFoodAnalyzer` and `FakeAIProvider` directly.
- Evaluation does not call `select_food_analyzer()`.
- Evaluation does not read `FITPLATE_AI_*` env vars.
- CI does not receive OpenAI credentials and does not run real-provider tests.

## Phase 4: Squat Video Design

Goals:

- Design squat-only form feedback before implementation.
- Keep feedback non-clinical and confidence-aware.

Candidate tasks:

- Define squat video result schema.
- Define upload constraints.
- Define job states.
- Define frame-quality warnings.
- Define safe feedback categories.
- Create copy guidelines for pain and injury concerns.

Exit criteria:

- Async video architecture is documented.
- Result schema includes uncertainty and safety flags.
- Product copy avoids diagnosis and treatment advice.

## Phase 5: Async Video Pipeline

Goals:

- Implement future video processing as an async workflow.

Candidate tasks:

- Add object storage integration.
- Add job table.
- Add queue.
- Add worker service.
- Add status endpoint.
- Add frontend polling for job status.
- Add timeout and failure handling.

Exit criteria:

- Video uploads do not block request/response cycles.
- Jobs expose clear status.
- Failed jobs return useful, safe messages.
- Results are stored as structured data.

## Phase 6: Evaluation and Operations

Goals:

- Make AI behavior measurable and maintainable.

Candidate tasks:

- Build evaluation dataset from approved examples.
- Add prompt regression checks.
- Track schema validation rate.
- Track safety flag rate.
- Track correction magnitude.
- Track cost and latency.
- Add developer dashboard or reports.

Exit criteria:

- Prompt changes can be compared.
- Model behavior regressions are visible.
- Cost growth can be monitored.
- Corrections inform quality review.

## Ongoing Documentation Rules

Update documentation whenever:

- MVP scope changes.
- API schemas change.
- Safety boundaries change.
- Prompt versions or model behavior change.
- Data retention assumptions change.
- New infrastructure is added.

Documentation should stay close to the implementation and avoid speculative promises that the product does not support.
