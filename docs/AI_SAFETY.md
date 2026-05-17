# AI Safety

## Safety Position

FitPlate Coach is a health-adjacent wellness and fitness tool. It is not a medical device, dietitian, clinician, physical therapist, or personal trainer.

The app may provide reflective estimates and general technique observations. It must not provide diagnosis, treatment, or extreme dieting guidance.

Uploaded images that appear non-food, NSFW, or too sensitive to analyze should return a safe unsupported state instead of a food estimate, using flags such as `non_food_image` or `nsfw_or_sensitive_image`.

## Core Boundaries

The product must not:

- Diagnose medical conditions.
- Diagnose eating disorders.
- Diagnose injuries or movement disorders.
- Provide treatment advice.
- Prescribe diets, medication, supplements, or rehabilitation plans.
- Encourage extreme calorie restriction.
- Encourage purging, dehydration, overtraining, or unsafe weight-loss tactics.
- Claim that exercise feedback prevents injury.
- Claim that calorie estimates are exact.

## Nutrition Output Constraints

Food analysis must:

- Use estimate ranges.
- Show uncertainty.
- Identify assumptions.
- Allow user correction.
- Avoid moralizing food choices.
- Avoid shame-based language.
- Avoid prescriptive weight-loss claims.

Food analysis must not:

- Tell a user how much they must eat.
- Recommend extreme calorie targets.
- Classify foods as universally good or bad.
- Infer medical conditions from food photos.
- Provide eating disorder screening or diagnosis.

Preferred language:

- "This is an estimate based on visible portions."
- "Portion size is uncertain."
- "You can adjust the items or serving size."
- "For medical nutrition advice, consult a qualified professional."

Avoid:

- "You should only eat..."
- "This meal will make you gain fat."
- "You need to lose weight."
- "This indicates an eating disorder."

## Exercise Output Constraints

Exercise feedback must:

- Stay focused on observable form cues.
- Use uncertainty when video quality is limited.
- Be squat-specific until additional movements are intentionally added.
- Encourage stopping if the user feels pain.
- Recommend a qualified professional for pain, injury, or medical concerns.

Exercise feedback must not:

- Diagnose injuries.
- Provide rehabilitation protocols.
- Claim to detect joint damage.
- Promise injury prevention.
- Recommend training through pain.
- Provide high-risk loading instructions.

Preferred language:

- "Your knees appear to move inward in some frames."
- "The camera angle makes this uncertain."
- "Consider reducing load or asking a qualified coach if this feels uncomfortable."
- "Stop if you feel pain."

Avoid:

- "You have knee valgus syndrome."
- "This will injure you."
- "Do these rehab exercises to fix it."
- "Keep going through the pain."

## Structured Output Requirements

Future AI output should be schema-first JSON. The application should validate the schema before using any generated content.

Food output should include:

- Schema version.
- Analysis mode: mock or AI.
- Food item candidates.
- Portion assumptions.
- Calorie range.
- Confidence.
- Uncertainty notes.
- Safety flags.
- Correction-ready fields.

Exercise output should include:

- Schema version.
- Movement type.
- Video quality notes.
- Observations.
- Confidence.
- Non-clinical cues.
- Safety flags.
- Escalation guidance.

Free-form text should be generated from structured fields, not used as the primary source of truth.

## Safety Flags

The canonical `safety_flags` enum is defined in [Architecture](ARCHITECTURE.md#safety-flags-enum). Do not add new safety flag strings in product code without updating that enum and any schema validation.

Safety flags should affect both backend behavior and frontend display.

## User Correction Safety

User corrections should improve estimates but must not become a way to generate unsafe advice.

Correction flow should:

- Let users edit food names and portions.
- Recompute estimates transparently.
- Preserve original assumptions for auditability.
- Avoid judgmental feedback about corrections.
- Use the canonical correction object from [Architecture](ARCHITECTURE.md#correction-object-sub-schema).

Correction flow should not:

- Punish users for high-calorie meals.
- Recommend compensatory restriction.
- Suggest purging, fasting, dehydration, or overtraining.

## Privacy and Consent

Food images and exercise videos can reveal sensitive personal context. Future production design should:

- Collect only what the feature needs.
- Avoid storing raw media longer than necessary.
- Keep media out of logs where possible.
- Use references instead of raw files in model logs.
- Make evaluation-data usage explicit.
- Support deletion when persistent accounts exist.
- Review GDPR/CCPA-style access, export, and deletion obligations before adding accounts or persistent personal data.

## Prompt and Model Governance

Future AI changes should be tracked with:

- Prompt versions.
- Schema versions.
- Safety policy versions.
- Model identifiers.
- Evaluation results.
- Known limitations.

Before promoting a new prompt or model, evaluate:

- JSON validity.
- Safety-boundary compliance.
- Estimate quality.
- Confidence calibration.
- Refusal behavior for medical or extreme dieting requests.

## Human Factors

The app should make uncertainty feel normal. Users should understand that correction is expected, not a failure.

Good experience patterns:

- Show estimate ranges instead of single exact numbers.
- Explain visible assumptions.
- Make corrections quick.
- Use calm language.
- Offer professional escalation only when appropriate.

Bad experience patterns:

- Red-alert styling for ordinary meals.
- Shame language.
- Overconfident calorie numbers.
- Clinical-sounding diagnoses.
- Hidden assumptions.
