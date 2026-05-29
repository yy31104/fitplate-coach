# Evaluation Maintenance Runbook

Use this runbook when the deterministic food-analysis evaluation needs to stay
aligned with intentional product or contract changes.

## When To Update Cases

Update `apps/api/evaluation/food_analysis/cases.json` when an intentional change
affects expected food-analysis behavior:

- Prompt version changes that should alter fake-provider or future regression expectations.
- Mock scenario changes, including item names, calorie ranges, confidence, or scenario buckets.
- Safety flag changes, including new flags or changed emission rules.
- `FoodAnalysis` schema changes that affect required fields or validation.

Keep cases small and reviewable. Do not widen calorie bounds just to hide a
regression; change expectations only when the product behavior is intentionally
different.

## Run And Regenerate

Run the deterministic evaluation:

```bash
npm run eval:api
```

This regenerates both committed evidence files:

- `docs/evaluation/REPORT.md`
- `apps/api/evaluation/report.json`

Then run the backend test suite:

```bash
npm run test:api
```

Before committing, review the report summary and commit the case changes,
`REPORT.md`, and `report.json` together.

CI reruns `npm run eval:api` and fails if either generated report has an
uncommitted diff.

## Hard Boundaries

Evaluation must remain local, deterministic, and free to run:

- Do not make real OpenAI calls.
- Do not require `FITPLATE_AI_PROVIDER_API_KEY`.
- Do not route evaluation through normal provider selection or environment flags.
- Do not add `real_provider` tests to normal CI.

CI should continue to run `npm run test:api` and `npm run eval:api` without
credentials. Real-provider smoke testing belongs only in the explicit local
runbook path, not the deterministic evaluation system.
