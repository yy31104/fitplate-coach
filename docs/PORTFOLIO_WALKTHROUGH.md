# FitPlate Coach Portfolio Walkthrough

A concise, interview-ready walkthrough of FitPlate Coach as a production-style
AI product case study.

FitPlate Coach is **local-demo-ready, not production SaaS**, and it is **not
medical or nutrition advice**. The point of the project is to show how an
AI-assisted product can be built around contracts, uncertainty, evaluation,
observability, cost control, privacy, and safety boundaries — instead of wiring
a single prompt directly into a UI.

For deeper references see [Portfolio Engineering Summary](PORTFOLIO_NOTES.md),
[Architecture](ARCHITECTURE.md), [API Contract](API_CONTRACT.md),
[AI Safety](AI_SAFETY.md), [Data Map](DATA_MAP.md), and the committed
[Evaluation Report](evaluation/REPORT.md).

## Problem

Food calorie tracking is slow and brittle when users search databases by hand,
and naive AI calorie apps present a single number that looks authoritative even
though portion estimation from a photo is inherently uncertain. That false
precision is both a product problem (users distrust it once it's wrong) and a
safety problem (calorie numbers can feed disordered eating).

FitPlate's bet: treat AI output as an **uncertain, structured, user-correctable
estimate**, not a fact. Show ranges, expose assumptions, and make correction a
first-class flow rather than an error path.

## Constraints

Deliberate constraints kept the project honest and reviewable:

- Local-demo-ready only — no production SaaS claims.
- No authentication, database, persistent image storage, or video pipeline.
- Real OpenAI calls are opt-in behind local feature flags and a server-side key.
- No real provider execution in CI (CI must never spend API money).
- Mock and fake-provider paths must stay deterministic.
- Non-medical, non-clinical product language only.

These are enforced as documented non-goals, not just intentions — see
[Implementation Plan](IMPLEMENTATION_PLAN.md) and [Data Map](DATA_MAP.md).

## Architecture

A small monorepo with a clear front-of-house / back-of-house split:

- `apps/web`: Next.js (App Router), TypeScript, Tailwind, mobile-first. The
  `/food/new` flow does local file validation, calls the backend, renders
  structured results, and supports a grams correction flow.
- `apps/api`: FastAPI + Pydantic (Python 3.12). Pydantic models are the
  request/response contracts.

Live endpoints (versioned under `/api/v0/`):

- `GET  /api/v0/health`
- `POST /api/v0/food/analyze/mock` — JSON metadata only (no image bytes).
- `POST /api/v0/food/analyze` — one multipart image, 10 MB cap, bytes are
  request-scoped and discarded; never persisted or logged.
- `POST /api/v0/food/corrections/mock` — recomputes one item's calorie range.

The integration contract is a single versioned schema, `FoodAnalysis`
(`schema_version: "food_analysis.v1"`), shared by mock, fake, and real paths.
Calorie estimates are always ranges (`min`, `max`, `point_estimate`), and
confidence maps to deterministic margins (high 10%, medium 20%, low 30%). See
[API Contract](API_CONTRACT.md) for the full schema.

## AI Boundary

The system separates two seams so each can be tested independently:

- **Analyzer seam** — `MockFoodAnalyzer` (deterministic) vs `AIFoodAnalyzer`
  (prompt registry + provider validation). Selected by `FITPLATE_AI_MODE`,
  which defaults to `mock`.
- **Provider seam** — `FakeAIProvider` (offline, deterministic) vs
  `OpenAIProvider` (real). `AIFoodAnalyzer` owns app logic (load the versioned
  prompt, build an `ImageRef`, validate provider output against `FoodAnalysis`,
  and overwrite backend-controlled fields `analysis_id`, `schema_version`,
  `mode`, `analyzed_at`). Providers own only the call shape.

Real OpenAI is gated behind **all** of: `FITPLATE_AI_MODE=ai`,
`FITPLATE_AI_PROVIDER=openai`, a server-side `FITPLATE_AI_PROVIDER_API_KEY`, and
a monthly cost cap (`FITPLATE_MONTHLY_COST_CAP_USD`). It uses the OpenAI
Responses API with Structured Outputs and is **local-demo-only** — see the
[Real AI Local Runbook](runbooks/real-ai-local.md) and
[ADR 0003](adr/0003-real-ai-provider.md). Prompts are versioned in a registry
(`apps/api/prompts/food_analysis/v1.txt`) before any provider call is treated as
default behavior.

## Evaluation Evidence

Fixed cases live in `apps/api/evaluation/food_analysis/cases.json` (four
scenarios: standard, low-confidence, non-food, complex). A generator
(`npm run eval:api`) runs them against the **mock analyzer and the
`FakeAIProvider`** and writes two committed evidence artifacts:
[`docs/evaluation/REPORT.md`](evaluation/REPORT.md) and
`apps/api/evaluation/report.json`.

Latest result: **8/8 cases pass** (4 mock + 4 fake), all outputs validate
against `FoodAnalysis`, and cost/latency are 0 because no real provider runs.
The generator is pinned directly to `MockFoodAnalyzer` and `FakeAIProvider`: it
does **not** call `select_food_analyzer()` and does **not** read `FITPLATE_AI_*`
env, so it cannot accidentally reach OpenAI. Maintenance rules are in the
[Evaluation Maintenance Runbook](runbooks/eval-maintenance.md).

## Privacy / Data Map

Privacy is treated as a first-class boundary even without accounts. Full detail
in [Data Map](DATA_MAP.md); the essentials:

- Image bytes (multipart route) are request-scoped and discarded; the metadata
  mock route sends no bytes at all.
- `model_run.v1` JSONL logs are **summary-only** and capture route, mode, model,
  prompt name/version, latency, input/output summaries, safety flags, tokens,
  cost, and errors. Filenames are truncated to 255 characters before logging.
- Never logged: raw image bytes, base64 payloads, API keys, raw provider
  responses, or full prompt bodies.
- Nothing is persisted server-side. Frontend state is in-memory only; logs are
  local, gitignored, and retained until a developer deletes them.
- With no accounts or database there is no per-user deletion/export obligation
  yet; GDPR/CCPA-style obligations are explicitly flagged as triggered by
  accounts or persistent personal data.

## Safety Boundaries

FitPlate is a reflective wellness tool, not a medical device. Boundaries are
documented in [AI Safety](AI_SAFETY.md) and enforced structurally:

- Calorie output is always a range, never an exact claim.
- `safety_flags` is a **typed enum** (13 values) so the backend can signal and
  the frontend can respond without ad-hoc UI copy; mock mode emits
  `low_confidence` and `non_food_image`.
- No diagnosis (medical, eating-disorder, or injury), no treatment plans, no
  extreme-restriction or rapid-weight-loss language.
- Correction is framed as expected and non-judgmental, not as a failure.

## Testing / CI

- Backend `pytest`: health, mock analysis, multipart upload, correction,
  analyzer/provider seams, cost cap, prompt registry, model-run logging, and
  evaluation. Current run: **139 passed, 1 skipped**.
- The one skip is the `real_provider` OpenAI smoke test, which skips unless both
  an API key and `FITPLATE_RUN_REAL_PROVIDER_TEST=1` are set — so CI never
  spends money.
- Frontend Playwright E2E covers the `/food/new` flow (validation, analysis
  display, correction, upload transport) with mocked API calls.
- GitHub Actions runs `lint:web`, `build:web`, `test:api`, `eval:api`, and
  `test:e2e` on Node 22 / Python 3.12, with no OpenAI credentials.

## Trade-offs and Non-Goals

- **Mock-first, not model-first.** Determinism and a stable contract were worth
  more early than real recognition accuracy. Real AI plugs into the same schema
  without a frontend rewrite.
- **Metadata-only mock + request-scoped upload** instead of object storage. Keeps
  the privacy story simple until retention and accounts are intentionally added.
- **Grams-only correction.** Food-name correction needs a density-lookup flow and
  was deferred.
- **Committed eval report, generated not gated.** CI regenerates the report but
  does not hard-fail on drift, trading a strict freshness gate for fewer brittle
  build failures.
- **Explicit non-goals:** no auth, database, object storage, deployment/IaC,
  video pipeline, production multi-provider routing, retries/streaming, or real
  provider calls in CI.

## What I Would Improve Next

- Add a CI freshness check (or scheduled regeneration) so a stale committed
  evaluation report cannot drift silently from `cases.json`.
- Expand evaluation beyond shape checks toward confidence calibration and
  correction-magnitude metrics once persisted corrections exist.
- Introduce persistence (analyses, corrections, model runs) behind a deletion
  path, which unlocks real evaluation data and a correction-rate dashboard.
- Add authentication and abuse controls as the prerequisite for any public host.
- Design the squat video track (async job + polling) per the documented
  [Architecture](ARCHITECTURE.md) plan, keeping feedback non-clinical.

## Interview Questions and Answers

**1. Why ranges instead of a single calorie number?**
Portion estimation from a photo is genuinely uncertain. A single number invites
false trust and can reinforce disordered eating. Ranges with explicit confidence
margins represent uncertainty honestly and make correction feel normal.

**2. How do you keep real AI from running in CI or by accident?**
Real OpenAI requires `FITPLATE_AI_MODE=ai`, `FITPLATE_AI_PROVIDER=openai`, a
server-side key, and a cost cap. CI sets none of these, the `real_provider` test
skips without an explicit flag, and the evaluation generator is pinned to the
mock and fake providers — it never reads `FITPLATE_AI_*` or calls
`select_food_analyzer()`.

**3. Why two seams (analyzer and provider) instead of one?**
The analyzer seam swaps product behavior (mock vs AI orchestration); the provider
seam swaps the network call (fake vs OpenAI). Splitting them lets the AI
orchestration path be tested deterministically with a fake provider, with no
network and no cost.

**4. What stays the same when you move from mock to real AI?**
The `FoodAnalysis` contract (`food_analysis.v1`), the calorie-range shape, the
correction contract, and the typed safety flags. The backend always overwrites
identity/timing fields and validates provider output against the schema, so the
frontend contract doesn't change.

**5. How do you handle cost?**
Every analysis writes a `model_run.v1` record with token counts and cost. Before
a real provider call, the route sums month-to-date AI cost from the JSONL log and
blocks with a `cost_cap_exceeded` error if the configured cap is reached. A cap
of `0.0` disables enforcement for local dev.

**6. What's your privacy posture without a database?**
Image bytes are request-scoped and discarded; the metadata route sends no bytes.
Logs are summary-only with filenames truncated and secrets/raw payloads excluded.
Nothing is persisted server-side, so there is no per-user deletion obligation
yet — and the doc explicitly states what would trigger one.

**7. How do you keep the product from drifting into medical advice?**
Safety is a typed enum the backend emits and the frontend renders structurally,
plus documented language rules: estimates not facts, no diagnosis, no treatment,
no extreme-restriction language, and professional-escalation copy for medical
concerns.

**8. What does your evaluation actually prove today?**
That every scenario validates against the schema and that mock and fake-provider
outputs are deterministic and within expected calorie bounds and safety flags. It
is a regression and contract guard, not yet an accuracy benchmark — that needs
real labeled data.

**9. Why is the evaluation report committed to the repo?**
So it is reviewable evidence in a PR and a portfolio without running anything.
It is regenerated by `npm run eval:api` and intentionally timestamp-free so it
stays diffable.

**10. What's the single biggest thing standing between this and production?**
Persistence with a deletion path. It unlocks real correction data and evaluation
metrics, but it also pulls in auth, storage retention, and privacy obligations —
which is exactly why it's deferred rather than half-built.

## Portfolio Resume Bullets (draft)

- Designed a schema-first AI food-analysis API (`FoodAnalysis` v1) shared across
  mock, fake-provider, and real-OpenAI paths, so a real model integrates behind a
  stable contract without a frontend rewrite.
- Built analyzer/provider adapter seams enabling deterministic, offline testing of
  the AI orchestration path and keeping real provider calls behind feature flags,
  a server-side key, and a monthly cost cap.
- Added summary-only model-run logging (route, mode, tokens, cost, latency, safety
  flags) with strict exclusion of image bytes, secrets, and raw provider
  responses, plus a documented privacy/data map.
- Created a deterministic, credential-free evaluation harness producing committed
  Markdown/JSON evidence (8/8 cases) and wired it into CI alongside lint, build,
  backend tests, and Playwright E2E with no API spend.
- Encoded product safety as a typed safety-flag enum and uncertainty-as-ranges UX,
  keeping the tool non-medical and user-correctable by design.
