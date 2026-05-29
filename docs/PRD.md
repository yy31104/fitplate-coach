# Product Requirements Document

## Product Summary

FitPlate Coach is a mobile-first web app that helps users estimate food calories from photos and receive non-clinical exercise form feedback from short videos.

The product is designed around uncertainty, correction, and safety. It should help users reflect on habits without pretending that AI estimates are exact or that computer vision can provide medical judgment.

## Target Users

- People who want a lightweight way to estimate meals from photos.
- Fitness beginners who want approachable technique feedback.
- Portfolio reviewers evaluating product judgment, architecture, and AI safety thinking.

## Core User Problems

- Food tracking can be slow and brittle when users must search databases manually.
- AI calorie estimates can look falsely precise without uncertainty or correction.
- Exercise form feedback can overstate confidence or drift into medical advice.
- Production AI apps need logging, evaluation, privacy, and cost controls from the start.

## Product Principles

- Mobile-first, quick to use, and clear.
- Estimates must show uncertainty.
- Users must be able to correct AI assumptions.
- AI outputs must be structured and versioned.
- Safety boundaries must be explicit and enforceable.
- Mock behavior must be clearly separable from future real AI behavior.

## MVP v0 Scope

MVP v0 is the current local-demo implementation target, not production SaaS.

Features:

- Food photo upload or image selection.
- Mock food analysis response.
- Structured JSON-shaped result model.
- Food item candidates with portion assumptions.
- Calorie estimate range.
- Confidence and uncertainty explanation.
- User correction interface for food items and portions.
- Updated estimate after correction, using the deterministic mock recomputation algorithm defined in [Architecture](ARCHITECTURE.md).
- Safety copy that avoids medical and extreme dieting claims.

Technical boundaries:

- Next.js frontend.
- FastAPI backend.
- No real AI in CI; real AI remains local-demo-only behind explicit flags, a server-side key, and a cost cap.
- No authentication.
- No database.
- No persistent image storage.
- No video processing.
- No native mobile app.

Success criteria:

- A reviewer can understand the intended product from the first screen.
- Mock analysis feels credible, clearly labeled, and schema-driven.
- Users can correct an estimate without friction.
- The product never presents calories as exact.
- Documentation stays aligned with implementation.

## MVP v0 Product Decisions

These decisions are provisional but implementation-ready. Change them only by updating this PRD and the architecture docs together.

- Calorie precision: show rounded ranges, such as `400-550 kcal`, not exact values as the main user-facing claim.
- Correction contract: use the canonical correction object in [Architecture](ARCHITECTURE.md#correction-object-sub-schema).
- Recalculation rule: use the deterministic mock calorie recomputation algorithm in [Architecture](ARCHITECTURE.md#mock-calorie-recalculation).
- Safety flags: use the canonical enum in [Architecture](ARCHITECTURE.md#safety-flags-enum).
- Food image upload: the first backend version uses direct `multipart/form-data` upload to `/api/v0/food/analyze`.
- Correction data use: v0 has no database, so corrections are session-local only. Future persisted corrections require explicit product documentation and consent rules before being used for evaluation.
- Image retention: v0 must not persist uploaded images. The backend should discard request-time images after mock analysis until object storage and retention policy are intentionally added.
- Squat cues: future squat feedback starts with observable, non-clinical cues such as depth range, torso angle consistency, knee tracking, heel contact, tempo, control, and camera quality.

## MVP v0 Non-Goals

- Real food recognition.
- Real calorie estimation model.
- Real video analysis.
- Persistent user history.
- Personalized diet advice.
- Weight-loss plans.
- Medical screening.
- User accounts.
- Payment.

## v1 Scope

v1 introduces the first production-shaped AI and persistence layer.

Candidate features:

- Real AI food photo analysis behind a stable backend contract.
- Prompt versioning for food analysis.
- Model run logs with latency, token usage, cost, prompt version, schema version, and safety flags.
- Persistent analysis history.
- User correction storage.
- Basic evaluation dataset built from corrected examples.
- Admin or developer-only review view for model runs and corrections.
- Basic privacy controls for uploaded images.

Technical additions:

- Next.js frontend.
- FastAPI backend.
- Database.
- Object storage for images.
- AI provider integration through a service boundary.
- Structured JSON validation.
- Server-side safety checks.

v1 success criteria:

- Real AI calls can be compared against corrected user data.
- Prompt and schema versions are visible in logs.
- Cost and latency can be inspected.
- The system can fail gracefully when AI output is invalid or unsafe.

## Future Scope

Food track:

- Better portion correction tools.
- Barcode or nutrition-label support.
- Meal history and trend views.
- Personalized defaults without medical claims.
- Human-readable explanation generated from structured data.

Exercise track:

- Squat-only video upload.
- Async processing job flow.
- Pose estimation or model-based phase detection.
- Non-clinical feedback on observable technique patterns.
- Confidence and frame-quality warnings.
- Rep segmentation and key-frame annotations.

Production AI operations:

- Golden evaluation sets.
- Regression tests for prompt versions.
- Human review workflows.
- Model comparison dashboards.
- Cost budgets and alerting.
- Data retention policies.
- Privacy-preserving deletion workflows.

## Out-of-Scope Safety Areas

FitPlate Coach must not provide:

- Medical diagnosis.
- Eating disorder diagnosis or screening.
- Injury diagnosis.
- Treatment plans.
- Extreme dieting guidance.
- Promises of weight loss, recovery, or injury prevention.

## Key Metrics

Early product metrics:

- Upload-to-result completion rate.
- Correction rate.
- Average correction magnitude.
- User-reported usefulness.
- Invalid or low-confidence result rate.

Future AI metrics:

- Schema validation pass rate.
- Safety flag rate.
- Estimate error against corrected examples.
- Prompt version regression rate.
- Cost per successful analysis.
- Latency per analysis.

## Deferred Product Questions

The former open questions now have MVP-ready defaults. Revisit them before v1 real AI, persistence, or video work expands the product surface.
