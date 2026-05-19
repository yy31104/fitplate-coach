# ADR 0003: Real AI Provider

Status: Accepted

## Context

FitPlate Coach already has a food analyzer adapter, provider seam, prompt
registry, model-run JSONL logs, upload transport, and fixed evaluation cases.
The next integration gap is allowing one real multimodal provider without
changing public API response shapes or making CI spend money.

## Decision

OpenAI is the first real provider. It is enabled only when all of these are
true:

- `FITPLATE_AI_MODE=ai`
- `FITPLATE_AI_PROVIDER=openai`
- `FITPLATE_AI_PROVIDER_API_KEY` is set on the backend

The provider uses the OpenAI Responses API with image input and Structured
Outputs JSON Schema enforcement for model-produced `FoodAnalysis` fields. The
backend still controls `analysis_id`, `schema_version`, `mode`, `analyzed_at`,
and `user_corrections`.

Image bytes are base64-encoded only inside the provider call. They are not
stored, returned, logged, or written to disk by application code. HEIC and HEIF
are rejected at the OpenAI seam for this PR; supported upload types for OpenAI
match the backend image allowlist minus HEIC/HEIF.

API keys are server-side only. Model-run logs record summaries, token counts,
cost, model, prompt name/version, and errors, but never API keys, base64 image
data, raw provider responses, or full prompt bodies.

The route checks month-to-date AI cost from `apps/api/logs/model_runs.jsonl`
against `FITPLATE_MONTHLY_COST_CAP_USD` before provider calls. A cap of `0.0`
disables enforcement. Provider calls use the configured request timeout. There
are no retries or streaming in this PR.

ModelRun entries for cost-cap short-circuits use `model: "cost-cap"` as a
sentinel value, not as a real model name. The OpenAI Responses API and
Structured Outputs integration depends on SDK/API behavior and should be
re-tested on SDK upgrades.

## Consequences

Normal tests and CI remain free of real network calls and API cost. A
`real_provider` pytest marker exists for an opt-in local smoke test that skips
unless an API key is present and `FITPLATE_RUN_REAL_PROVIDER_TEST=1` is set.

Deferred work includes multi-provider routing, persistent cost accounting,
retry policy, object storage, EXIF handling, auth, database-backed model runs,
and any frontend real-AI UX changes.
