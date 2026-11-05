# Food Analysis Prompt Log

## 2026-05-18 - v1

- Added the initial `food_analysis.v1` prompt artifact for future multimodal food analysis.
- Defines structured JSON expectations, calorie range uncertainty, confidence, safety flags, and empty `user_corrections`.
- Not wired into the live mock route; current mock analysis remains deterministic code.

## 2026-11-05 - v2

- Removed text that was sent to the real provider but described the prompt as unused: "future multimodal food analysis model" and "This prompt is registered for future AI integration only. The current live mock route does not call this prompt."
- No change to the requested schema, calorie-range rules, confidence values or safety instructions.
- v1 is marked `deprecated` and kept so older model-run logs that record `prompt_version: v1` still resolve.
