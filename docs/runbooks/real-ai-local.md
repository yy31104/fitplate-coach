# Real AI Local Runbook

## Overview

The real OpenAI path is opt-in and off by default. Normal local development uses
deterministic mock analysis, makes no provider calls, and costs nothing.

Running real AI spends real money through your OpenAI API key. Use this runbook
only for intentional local smoke tests, and set a low local monthly cost cap
before starting the backend.

For the design decision behind the provider integration, see
[ADR 0003: Real AI Provider](../adr/0003-real-ai-provider.md).

## Prerequisites

- Python 3.12.
- A backend virtual environment at `apps/api/.venv`.
- An OpenAI API key with access to the configured model.
- Backend running locally at `http://127.0.0.1:8000`.
- Confirm quota and billing limits in the OpenAI console before testing.

## Environment Variables

| Variable | Purpose | Default | Safe local value | Notes |
| --- | --- | --- | --- | --- |
| `FITPLATE_AI_MODE` | Selects mock or AI analyzer mode. | `mock` | `ai` | Leave unset for normal mock development. |
| `FITPLATE_AI_PROVIDER` | Selects the AI provider when AI mode is enabled. | `fake` | `openai` | `fake` makes no network calls. |
| `FITPLATE_AI_PROVIDER_API_KEY` | Server-side OpenAI API key. | unset | `sk-...` | Never commit a real key. Use a shell export only. |
| `FITPLATE_AI_MODEL` | OpenAI model name used by the provider. | `gpt-5.4-mini` | `gpt-5.4-mini` | Check OpenAI docs for current model support. |
| `FITPLATE_MONTHLY_COST_CAP_USD` | Local month-to-date AI cost cap from JSONL logs. | `0.0` | `1.00` | `0.0` disables enforcement. Set a cap before real testing. |
| `FITPLATE_AI_REQUEST_TIMEOUT_SECONDS` | Provider request timeout. | `30` | `30` | Timeout failures return the existing analysis failure envelope. |

Do not copy pricing numbers into this runbook. OpenAI pricing changes; check the
current OpenAI pricing page before running anything expensive.

## API Key Safety Rules

- Use shell exports for local testing.
- Do not commit API keys.
- Do not write API keys to tracked files.
- The app does not load `.env` automatically.
- If you create a local `.env`, confirm it is gitignored before writing any key.
- Rotate the key immediately if it is exposed.
- Set OpenAI console hard usage limits as a backstop.

## ModelRun JSONL Safety

Model run logs are append-only JSONL at:

```text
apps/api/logs/model_runs.jsonl
```

The log records summaries only. It does not contain API keys, raw image bytes,
or base64 image data. Do not commit this file.

The log directory is already ignored by the root `.gitignore`; verify with
`git status` before committing.

For a clean local baseline, move or remove the log:

```bash
mv apps/api/logs/model_runs.jsonl apps/api/logs/model_runs.backup.jsonl
# or
rm apps/api/logs/model_runs.jsonl
```

## Setup Commands

Create and activate the backend virtual environment if needed:

```bash
python -m venv apps/api/.venv
source apps/api/.venv/bin/activate
```

Install API dependencies:

```bash
apps/api/.venv/bin/python -m pip install -e "apps/api[dev]"
```

Export real-AI local environment variables:

```bash
export FITPLATE_AI_MODE=ai
export FITPLATE_AI_PROVIDER=openai
export FITPLATE_AI_PROVIDER_API_KEY="sk-..."
export FITPLATE_AI_MODEL=gpt-5.4-mini
export FITPLATE_MONTHLY_COST_CAP_USD=1.00
export FITPLATE_AI_REQUEST_TIMEOUT_SECONDS=30
```

Start the backend:

```bash
cd apps/api
./.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Real AI Smoke Test

Option 1: run the skip-by-default real provider pytest test:

Export the environment variables from the setup section in the same shell before
running this command.

```bash
cd apps/api
./.venv/bin/pytest -m real_provider
```

Without `FITPLATE_AI_PROVIDER_API_KEY`, this test skips. With a key, it makes a
real provider call and may spend money.

Option 2: run a manual multipart upload:

```bash
IMAGE_PATH="/path/to/local-food-photo.jpg"

curl -sS -X POST "http://127.0.0.1:8000/api/v0/food/analyze" \
  -F "image=@${IMAGE_PATH};type=image/jpeg" \
  | python3 -m json.tool
```

The response should include:

```json
"mode": "ai"
```

## Return To Mock Mode

Unset real-AI environment variables:

```bash
unset FITPLATE_AI_MODE
unset FITPLATE_AI_PROVIDER
unset FITPLATE_AI_PROVIDER_API_KEY
unset FITPLATE_AI_MODEL
unset FITPLATE_MONTHLY_COST_CAP_USD
unset FITPLATE_AI_REQUEST_TIMEOUT_SECONDS
```

Restart `uvicorn` after unsetting variables.

Verify mock mode:

```bash
curl -sS -X POST "http://127.0.0.1:8000/api/v0/food/analyze/mock" \
  -H "Content-Type: application/json" \
  -d '{"filename":"lunch-photo.jpg","content_type":"image/jpeg","size_bytes":345678,"last_modified_ms":1710000000000}' \
  | python3 -m json.tool
```

The response should include:

```json
"mode": "mock"
```

Normal pytest works without real-AI environment variables and skips the
`real_provider` test automatically.

## Inspect ModelRun Logs Safely

Run these commands from the repository root.

Tail the latest record:

```bash
tail -n 1 apps/api/logs/model_runs.jsonl
```

Pretty-print it:

```bash
tail -n 1 apps/api/logs/model_runs.jsonl | python3 -m json.tool
```

Show mode, model, cost, and error fields:

```bash
tail -n 1 apps/api/logs/model_runs.jsonl | python3 -c '
import json, sys
r = json.load(sys.stdin)
print({
    "mode": r.get("mode"),
    "model": r.get("model"),
    "cost_usd": r.get("cost_usd"),
    "error_code": r.get("error_code"),
    "error_message": r.get("error_message"),
})
'
```

Sum current-month AI cost from local logs:

```bash
python3 - <<'PY'
import json
from datetime import datetime, UTC
from pathlib import Path

path = Path("apps/api/logs/model_runs.jsonl")
now = datetime.now(UTC)
total = 0.0

if path.exists():
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
            started_at = datetime.fromisoformat(record["started_at"].replace("Z", "+00:00")).astimezone(UTC)
        except Exception:
            continue
        if record.get("mode") == "ai" and started_at.year == now.year and started_at.month == now.month:
            total += float(record.get("cost_usd", 0.0))

print(f"month_to_date_ai_cost_usd={total:.6f}")
PY
```

Before sharing logs, check that they contain no API key, no raw image bytes, and
no base64 image payload.

## Out Of Scope

This runbook does not cover:

- Deployment.
- Multi-provider setup.
- Authentication, database, or storage.
- Docker.
- Video pipeline work.
- Creating or rotating OpenAI API keys.
- Prompt versioning or evaluation details.
- Frontend E2E details.
