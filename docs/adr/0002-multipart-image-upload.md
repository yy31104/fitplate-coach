# ADR 0002: Multipart Image Upload Transport

## Status

Accepted

## Context

PR #13 closed the AI integration contract gaps: analyzer selection, provider
boundary, prompt logging, fake-provider evaluation, and `mode: "ai"` schema
support. A real image-capable provider will eventually need image bytes, but
FitPlate Coach still has no storage, user accounts, or real AI provider call.

## Decision

Add `POST /api/v0/food/analyze` as a synchronous multipart upload transport.
The route accepts one required file field named `image`, reads bytes in memory
with a hard size cap, summarizes upload metadata for `ModelRun`, and discards
bytes before returning.

Starlette's multipart parser is configured with a spool threshold above the
10 MB app upload cap, so accepted uploads within that cap remain in memory at
the framework parser layer.

The route shares the existing analyzer adapter. In this PR, the analyzer still
receives metadata-shaped input built from the upload: filename, content type,
actual byte count, and `last_modified_ms=0`. The metadata-only
`POST /api/v0/food/analyze/mock` route remains deterministic and is not
deprecated.

Application code does not persist bytes or write them to disk, model-run logs,
error payloads, or responses. The route does not add object storage, an async
job queue, content hashing, EXIF parsing, magic-byte sniffing, or a real AI
provider call.

## Consequences

PR #15 can extend `ImageRef` with request-scoped bytes without changing the
public HTTP contract. That future work should still preserve the same privacy
boundary: no raw media in logs and no implicit persistence.

Video upload should use a different route shape. Video analysis will likely
need asynchronous job creation, object storage, and polling, while this food
route is intentionally synchronous and bounded.
