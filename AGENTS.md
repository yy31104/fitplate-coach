# AGENTS.md

Guidance for Codex and other agentic coding assistants working in this repository.

## Project Identity

FitPlate Coach is a mobile-first web app for food photo calorie estimation and exercise form feedback. It should read as a production-style portfolio project: disciplined scope, clear safety boundaries, structured AI contracts, and practical architecture notes.

The MVP v0 is documentation-first and implementation-light:

- Food photo mock analysis only.
- Squat feedback is documented as a future direction only.
- No real AI API calls yet.
- No authentication yet.
- No database yet.
- No video processing yet.
- No native mobile app yet.

## Current Repository Rule

Until application scaffolding is explicitly requested, do not create app code, framework boilerplate, package manifests, lockfiles, dependency installs, or generated build artifacts.

Allowed in the current phase:

- Governance files.
- Product documentation.
- Architecture documentation.
- Safety documentation.
- Implementation planning.

Not allowed in the current phase:

- Next.js scaffolding.
- FastAPI scaffolding.
- Package installation.
- Database setup.
- AI provider integration.
- Video processing implementation.

## Transition to Implementation

When the user explicitly approves scaffolding or implementation, update this file before creating code. The update must name the approved phase, move only the approved work into the allowed list, and keep the remaining v0 prohibitions visible.

Approval for one layer does not imply approval for all layers. For example, approval to scaffold the Next.js frontend does not approve FastAPI, auth, a database, real AI calls, or video processing.

During MVP v0 implementation, preserve these rules unless the user explicitly changes scope:

- No authentication.
- No database.
- No real AI API call.
- No video processing.
- No native mobile app.

## Engineering Principles

- Keep the app mobile-first, pragmatic, and portfolio-grade.
- Prefer typed, structured contracts over free-form text for AI-style outputs.
- Treat AI output as uncertain, user-correctable, and auditable.
- Preserve clear separation between product behavior, AI contracts, safety policy, and infrastructure.
- Avoid adding abstractions before the codebase needs them.
- Keep future production concerns visible: evaluation, prompt versioning, model run logs, cost tracking, privacy, and correction loops.

## Safety Boundaries

FitPlate Coach is not a medical device, dietitian, clinician, or physical therapist.

Do not implement or document behavior that:

- Diagnoses disease, eating disorders, injuries, or medical conditions.
- Gives treatment advice.
- Encourages extreme dieting, purging, dehydration, or unsafe weight loss.
- Presents calorie estimates as exact.
- Presents form feedback as a clinical or injury diagnosis.

Use language that supports reflection and safer habits, not prescriptive medical claims.

## AI Output Requirements

All future AI-facing features should use structured JSON schemas. Avoid relying on unstructured prose as the primary integration contract.

Food analysis outputs should include:

- Food item candidates.
- Portion assumptions.
- Calorie estimate ranges.
- Confidence or uncertainty.
- User correction fields.
- Safety flags where relevant.

Exercise feedback outputs should include:

- Movement type.
- Rep or phase observations.
- Confidence.
- Non-clinical technique cues.
- Safety disclaimers.
- Escalation guidance for pain or injury concerns.

## Working Style

- Read relevant docs before making changes.
- Keep edits tightly scoped to the requested files.
- Do not overwrite user work without checking current file contents.
- If implementation is requested later, update docs when architecture or safety assumptions change.
- Prefer concise, high-signal documentation over broad speculative detail.

## Verification

For documentation-only changes, verify with:

- `git status`
- `rg --files`
- Manual review of changed Markdown files

Do not run package managers or framework commands unless application code has been intentionally introduced.
