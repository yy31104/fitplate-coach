# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Repository Purpose

FitPlate Coach is a mobile-first web app concept for:

1. Food photo calorie estimation with uncertainty and user correction.
2. Exercise form feedback from short videos, starting with squat only.

The project should feel like a production-style portfolio project, not an AI toy. Favor explicit product decisions, structured contracts, safety boundaries, and a credible path from mock behavior to production AI workflows.

## Current Scope

MVP v0 is not an application scaffold yet. It is a governed project foundation.

Allowed now:

- Documentation.
- Repo rules.
- Product requirements.
- Architecture notes.
- AI safety constraints.
- Implementation planning.

Do not create yet:

- Next.js app.
- FastAPI app.
- Package manifests.
- Dependency lockfiles.
- Database schema.
- Auth flows.
- Real AI calls.
- Video processing pipeline.
- Native mobile app.

## Planned Stack

The intended future stack is:

- Frontend: Next.js, TypeScript, mobile-first responsive UI.
- Backend: FastAPI, Python.
- AI integration: structured JSON outputs with versioned prompts and logged model runs.
- Future async processing: job queue and object storage for video workflows.
- Future persistence: database for users, analyses, corrections, model runs, and evaluation data.

These are documented intentions, not current implementation requirements.

## Product Principles

- Show uncertainty clearly.
- Invite user correction instead of pretending AI estimates are exact.
- Keep AI output structured and auditable.
- Separate mock analysis from real AI integration.
- Keep safety language visible but calm.
- Treat privacy, cost, evaluation, and observability as first-class production concerns.

## Safety Rules

FitPlate Coach must not provide medical diagnosis, treatment advice, injury diagnosis, or extreme dieting guidance.

Use safe wording:

- "Estimate" instead of "exact calories."
- "May help you reflect" instead of "you should."
- "Consider a qualified professional if you have pain or medical concerns" instead of diagnosing.

Avoid unsafe wording:

- Claims that the system can detect eating disorders, injuries, or disease.
- Specific treatment plans.
- Extreme calorie targets.
- Promises of rapid weight loss.
- Exercise feedback that claims to prevent or diagnose injury.

## AI Contract Expectations

Future AI outputs should be schema-first JSON with explicit uncertainty. Free-form generated text may be used for user-facing summaries, but only after structured data is available.

Document prompt changes, schema changes, and model behavior changes. Future production work should include:

- Prompt versioning.
- Model run logs.
- Evaluation sets.
- Cost tracking.
- User correction loops.
- Privacy review.

## Working Instructions

- Before editing, inspect the relevant file contents.
- Preserve existing user work.
- Keep documentation consistent across README, PRD, architecture, safety, and implementation plan.
- Do not introduce code or dependencies unless the user explicitly asks for implementation.
- When implementation begins later, keep mock behavior clearly separate from production AI integration.
