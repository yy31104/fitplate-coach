# Implementation Plan

## Phase 0: Project Foundation

Status: current phase.

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

Do not start until application scaffolding is explicitly requested.

This phase still preserves the v0 rule: no auth, no database, no real AI call, no video processing, and no native mobile app.

Goals:

- Create a mobile-first Next.js app.
- Build the first user-facing food photo flow.
- Keep all analysis mocked.
- Make the frontend-to-backend handoff explicit without expanding scope.

Ordered tasks:

1. Transition governance:
   - Update `AGENTS.md`, `CLAUDE.md`, and this plan to show that the approved implementation phase has started.
   - Keep the not-allowed list explicit: no auth, database, real AI, or video processing.
2. Frontend shell with hardcoded mock data:
   - Scaffold Next.js with TypeScript only after approval.
   - Add mobile-first layout.
   - Add food image selection UI.
   - Use hardcoded in-memory mock analysis data only.
   - Do not call a backend yet.
3. Frontend correction loop:
   - Use the canonical correction object from [Architecture](ARCHITECTURE.md#correction-object-sub-schema).
   - Use the deterministic mock recomputation algorithm from [Architecture](ARCHITECTURE.md#mock-calorie-recalculation).
   - Display rounded calorie ranges.
   - Add uncertainty and safety copy.
4. Backend mock boundary:
   - Scaffold FastAPI only after backend work is explicitly approved.
   - Add `/api/v0/food/analyze` as a mock endpoint.
   - Accept direct `multipart/form-data` image upload.
   - Return the same structured response shape used by the frontend mock.
   - Validate supported media metadata and basic file constraints.
5. Frontend/backend handoff:
   - Replace hardcoded frontend analysis with calls to `/api/v0/food/analyze`.
   - Keep deterministic mock behavior identical across frontend and backend.
   - Preserve local-only correction state unless persistence is separately approved.
6. Product polish:
   - Add low-confidence and unclear-image states.
   - Add accessible loading and error states.
   - Add documentation updates for any schema changes.
   - Add focused tests only after test tooling exists.

Exit criteria:

- User can select an image and see a mock result.
- User can correct food items or portions.
- The result display uses structured mock data.
- Frontend-only mock behavior and backend mock behavior follow the same documented schema and recomputation rule.
- No real AI call exists.
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

Goals:

- Replace mock food analysis with a real AI provider behind the same service boundary.
- Preserve structured outputs and safety checks.

Candidate tasks:

- Add AI provider adapter.
- Define prompt templates.
- Add prompt versioning.
- Validate AI JSON responses.
- Add model run logging.
- Add cost and latency tracking.
- Add fallback behavior for invalid AI output.
- Create a small evaluation set.

Exit criteria:

- AI output passes schema validation.
- Prompt and model versions are logged.
- Cost per analysis is visible.
- Safety checks can block or soften unsafe output.
- User corrections are stored for future evaluation.

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
