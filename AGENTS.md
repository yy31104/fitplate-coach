# Contributing

Use Node.js 22+ and Python 3.12.
Install web dependencies with `npm ci`.
Create `apps/api/.venv` and install `apps/api[dev]` there.
Run `npm run dev:web` and `npm run dev:api` in separate terminals.
The web app uses port 3000 and the API uses port 8000.

Check changes with:
```bash
npm run lint:web
npm run build:web
npm run test:api
npm run eval:api
npm run metrics:api
npm exec --workspace apps/web playwright install chromium
npm run test:e2e
git diff --check
```

- Keep the default demo and CI on mock/fake providers.
- Preserve the FoodAnalysis and UserCorrection contracts.
- Keep calorie recomputation in the API and original estimates visible.
- Keep provider keys server-side and image bytes request-scoped.
- Keep logs summary-only; exclude images, prompts, secrets, and full responses.
- Add no accounts, persistence, or video features as part of cleanup work.
- Update matching TypeScript/Pydantic contracts together when behavior changes.
