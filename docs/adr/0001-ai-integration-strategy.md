# ADR 0001: AI Integration Strategy

## Status

Accepted

## Context

FitPlate Coach needs a path from deterministic mock food analysis to real AI
analysis without changing the product contract, leaking secrets to the
frontend, or storing raw media in observability systems.

## Decision

The backend keeps two separate seams:

- `FoodAnalyzer` selects the application-level analyzer for a food request.
- `AIProvider` represents the lower-level provider call used by `AIFoodAnalyzer`.

The mock route remains deterministic and is not deprecated. By default,
`FITPLATE_AI_MODE=mock` keeps current behavior unchanged. `FITPLATE_AI_MODE=ai`
uses `AIFoodAnalyzer` with `FakeAIProvider`, which validates the future provider
path without calling any real model.

`AIFoodAnalyzer` loads the registered `food_analysis` `v1` prompt, builds an
`ImageRef`, calls the provider, validates the returned dict with the
`FoodAnalysis` schema, and overrides backend-controlled fields:
`analysis_id`, `schema_version`, `mode`, and `analyzed_at`.

`ImageRef` currently carries only `content_type` and `size_bytes`. It does not
carry filename, last-modified time, real image bytes, or stored media paths. A
future upload route can replace this with an in-memory or storage-backed image
reference after upload and retention policies are explicit.

API keys are read through backend settings only. They are never sent to the
frontend, logged, or included in API responses.

## Consequences

Model run logs can record `mode`, `model`, `prompt_name`, and `prompt_version`
before real provider traffic exists. Cost remains `0.0` for the fake provider;
real cost calculation and monthly cost caps will be enforced in a later PR using
the JSONL log as the audit trail.

Real providers should use tool calling or an equivalent structured-output
mechanism so `FoodAnalysis.model_validate` remains the enforcement point. The
first real integration should also add timeout handling around the existing
30-second setting. Retry policy is intentionally deferred.

Evaluation runs through the analyzer adapter. The same fixed cases can validate
the deterministic mock analyzer and the fake-provider AI path today, then later
serve as prompt regression checks for real providers.
