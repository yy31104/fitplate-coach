# Data Map

FitPlate Coach is local-demo-ready only. It has no accounts, database,
persistent media storage, analytics, production host, or public API surface.

## Data Accepted

Current food analysis routes accept:

- Image bytes for `POST /api/v0/food/analyze`, request-scoped only.
- File metadata: filename, content type, size in bytes, and last modified time
  when supplied by the metadata mock route.
- Correction data for `POST /api/v0/food/corrections/mock`: item id, original
  name, original grams, corrected grams, calorie density, confidence, and
  original calorie range.

The backend validates media type and size limits. Accepted multipart bytes are
read into memory for the current request, passed through the analyzer boundary
when configured, and discarded before the request completes.

## Data Logged

Food analysis and correction routes append local `model_run.v1` JSONL records to
`apps/api/logs/model_runs.jsonl`.

Logged summary fields include:

- Request id, route, mode, model, prompt name, prompt version, start/end time,
  and latency.
- Input summaries such as transport, filename, content type, size in bytes,
  item id, grams, and confidence.
- Output summaries such as analysis id, item count, total-calorie range, safety
  flags, correction id, corrected grams, and corrected-calorie range.
- Token counts, cost fields, and error code/message when present.

Filenames are truncated to 255 characters before logging.

## Data Not Logged

Logs must not include:

- Raw image bytes.
- Base64 image payloads.
- API keys or provider secrets.
- Raw provider responses.
- Full prompt bodies.
- Full request bodies or full response bodies.

## Retention

Product data is not persisted in a server-side database, object store, or
account record. The frontend keeps analysis and correction state in React state
only; refreshing the page clears it.

`apps/api/logs/model_runs.jsonl` is local, append-only, gitignored, and retained
until a developer manually deletes it. Generated evaluation reports are
deterministic project evidence and do not contain user media or credentials.

## Deletion and Export

There are no accounts, user ids, sessions, database records, or stored media, so
there is no per-user deletion or export obligation in the current local demo.

Future GDPR/CCPA-style access, export, deletion, and retention requirements are
triggered before adding accounts, persistent personal data, production analytics,
or durable media storage.

## Boundaries

- FitPlate Coach is non-medical and non-clinical.
- Calorie estimates are ranges for reflection, not exact nutrition facts.
- Exercise feedback remains a documented future direction only.
- Local CORS allows only `http://127.0.0.1:3000` and
  `http://localhost:3000`.
- Do not expose the API on a public host without authentication, abuse controls,
  and a fresh privacy review.
- Real OpenAI calls are local-demo-only behind explicit flags, a server-side key,
  and a cost cap; CI uses deterministic mock and fake-provider paths only.
