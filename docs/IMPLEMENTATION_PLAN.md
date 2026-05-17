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

## Phase 1: Frontend Shell

Do not start until application scaffolding is explicitly requested.

Goals:

- Create a mobile-first Next.js app.
- Build the first user-facing food photo flow.
- Keep all analysis mocked.

Candidate tasks:

- Scaffold Next.js with TypeScript.
- Add mobile-first layout.
- Add food image selection or upload UI.
- Add mock analysis result screen.
- Add correction controls.
- Add uncertainty and safety copy.
- Add basic UI tests if test tooling exists.

Exit criteria:

- User can select an image and see a mock result.
- User can correct food items or portions.
- The result display uses structured mock data.
- No real AI call exists.

## Phase 2: Backend Shell

Goals:

- Create a FastAPI backend.
- Define API contracts for food analysis.
- Return deterministic mock analysis.
- Keep frontend/backend boundaries clean.

Candidate tasks:

- Scaffold FastAPI service.
- Define request and response schemas.
- Add `/food/analyze` mock endpoint.
- Add validation for supported media metadata.
- Add deterministic calorie recomputation for corrections.
- Add backend tests for schema and correction logic.

Exit criteria:

- Frontend can call backend mock endpoint.
- Backend responses follow documented schema.
- Invalid inputs return safe, user-readable errors.

## Phase 3: Product-Grade Mock MVP v0

Goals:

- Make the mock food-analysis experience feel credible and complete.
- Demonstrate production thinking without real AI.

Candidate tasks:

- Improve mock scenarios for common meals.
- Add low-confidence and unclear-image states.
- Add user correction loop.
- Add local-only result state.
- Add accessible loading and error states.
- Add documentation updates for any schema changes.

Exit criteria:

- MVP v0 can be demoed end to end.
- Mock status is clear to users and reviewers.
- Safety boundaries are visible in the experience.
- Documentation matches the implemented behavior.

## Phase 4: Persistence Preparation

Goals:

- Prepare for v1 data storage without prematurely expanding scope.

Candidate tasks:

- Design database entities for analyses, corrections, prompts, and model runs.
- Document retention policy.
- Add migration tooling only when backend persistence is approved.
- Add privacy notes to user-facing copy.

Candidate entities:

- User, once auth exists.
- FoodAnalysis.
- FoodItemEstimate.
- UserCorrection.
- PromptVersion.
- ModelRun.
- EvaluationExample.

Exit criteria:

- Storage design supports correction loops and evaluation.
- No raw media is stored in logs.
- Retention and deletion assumptions are documented.

## Phase 5: Real AI Food Analysis v1

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

## Phase 6: Squat Video Design

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

## Phase 7: Async Video Pipeline

Goals:

- Implement future video processing as an async workflow.

Candidate tasks:

- Add object storage integration.
- Add job table.
- Add queue.
- Add worker service.
- Add status endpoint.
- Add frontend polling or subscription.
- Add timeout and failure handling.

Exit criteria:

- Video uploads do not block request/response cycles.
- Jobs expose clear status.
- Failed jobs return useful, safe messages.
- Results are stored as structured data.

## Phase 8: Evaluation and Operations

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
