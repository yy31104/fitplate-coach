# Food Analysis Prompt Log

## 2026-05-18 - v1

- Added the initial `food_analysis.v1` prompt artifact for future multimodal food analysis.
- Defines structured JSON expectations, calorie range uncertainty, confidence, safety flags, and empty `user_corrections`.
- Not wired into the live mock route; current mock analysis remains deterministic code.

## 2026-11-05 - v2

- Removed text that was sent to the real provider but described the prompt as unused: "future multimodal food analysis model" and "This prompt is registered for future AI integration only. The current live mock route does not call this prompt."
- No change to the requested schema, calorie-range rules, confidence values or safety instructions.
- v1 is marked `deprecated` and kept so older model-run logs that record `prompt_version: v1` still resolve.

## 2026-11-05 - v3

- The model now returns only, per item: `name`, `grams`, `category` (from a fixed list) or `density_kcal_per_gram`, and `confidence`; plus `uncertainty_notes` and `safety_flags`.
- Removed the request for calorie ranges, `total_calories` and `items_count`. The server computes them with `calorie_range_from_density`, the function the correction route uses, so a model can no longer return totals that do not add up.
- The OpenAI strict JSON schema matches this shape; `category` is an enum of the server's density table plus `null`.
- v2 is marked `deprecated` and kept so model-run logs that record `prompt_version: v2` still resolve.
