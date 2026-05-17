# FitPlate Coach

FitPlate Coach is a mobile-first web app concept for helping users reflect on nutrition and exercise technique with AI-assisted estimates, clear uncertainty, and user correction.

The project has two product tracks:

1. Food photo calorie estimation with visible assumptions, confidence, and correction.
2. Exercise form feedback from short videos, starting with squat feedback.

The current repository is in its initial documentation and governance phase. No application code has been scaffolded yet.

## Current Status

MVP v0 is documentation-first.

Implemented now:

- Repository governance files.
- Product requirements.
- Architecture notes.
- AI safety boundaries.
- Implementation plan.

Not implemented yet:

- Next.js frontend.
- FastAPI backend.
- Real AI provider integration.
- Authentication.
- Database.
- Video processing.
- Native mobile app.

## MVP v0 Scope

The first implementation milestone will focus on a food photo mock-analysis flow:

- Mobile-first upload or image selection experience.
- Mock food analysis response.
- Structured JSON-shaped analysis contract.
- Calorie estimate ranges rather than exact claims.
- User correction path for food items and portions.
- Clear safety and uncertainty language.

Squat video feedback is documented for future design but intentionally out of v0 implementation scope.

## Planned Stack

The planned application stack, once scaffolding begins:

- Frontend: Next.js with TypeScript.
- Backend: FastAPI.
- AI contracts: structured JSON schemas.
- Future storage: database for analyses, corrections, prompts, model runs, and evaluations.
- Future media handling: object storage for uploaded media.
- Future async work: job queue for video processing.

No packages are installed in the current repository state.

## Product Principles

- Production-style portfolio quality over demo-only shortcuts.
- Mobile-first workflows.
- Structured AI outputs instead of fragile free-form parsing.
- Uncertainty shown directly in the user experience.
- User corrections treated as product value and future evaluation data.
- Safety boundaries for nutrition and exercise advice.
- Privacy-aware handling of photos, videos, and health-adjacent data.

## Safety Position

FitPlate Coach is not a medical device and does not replace a doctor, dietitian, physical therapist, trainer, or other qualified professional.

The product must not:

- Diagnose medical conditions, eating disorders, injuries, or movement disorders.
- Provide treatment advice.
- Encourage extreme dieting or unsafe weight loss.
- Present calorie estimates as exact.
- Claim that form feedback prevents or diagnoses injury.

## Documentation Map

- [Product Requirements](docs/PRD.md)
- [Architecture](docs/ARCHITECTURE.md)
- [AI Safety](docs/AI_SAFETY.md)
- [Implementation Plan](docs/IMPLEMENTATION_PLAN.md)

## Non-Goals

For the current MVP v0, this project will not include:

- Real AI API calls.
- User accounts.
- Persistent storage.
- Payment or subscription features.
- Medical, clinical, or therapeutic workflows.
- Multi-exercise video analysis.
- Native iOS or Android apps.

## License

No license has been selected yet.
