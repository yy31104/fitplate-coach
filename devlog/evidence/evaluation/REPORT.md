# Evaluation Report

schema_version: `evaluation.v1`

Provider modes covered: mock + ai/fake

Total: 8
Passed: 8
Failed: 0

All cases validate against `FoodAnalysis`.

Cost and latency are 0 because no real provider runs.

## mock

Total: 4
Passed: 4
Failed: 0

| Case | Passed | Safety flags | Total calorie bounds | Expected bounds |
| --- | --- | --- | --- | --- |
| standard-scenario | true | none | 452-620 (point 536) | min >= 400, max <= 700 |
| low-confidence-scenario | true | low_confidence | 298-554 (point 426) | min >= 250, max <= 650 |
| non-food-scenario | true | non_food_image | 0-0 (point 0) | min >= 0, max <= 0 |
| complex-scenario | true | none | 707-1061 (point 884) | min >= 600, max <= 1200 |

## ai/fake

Total: 4
Passed: 4
Failed: 0

| Case | Passed | Safety flags | Total calorie bounds | Expected bounds |
| --- | --- | --- | --- | --- |
| standard-scenario | true | none | 452-620 (point 536) | min >= 400, max <= 700 |
| low-confidence-scenario | true | low_confidence | 298-554 (point 426) | min >= 250, max <= 650 |
| non-food-scenario | true | non_food_image | 0-0 (point 0) | min >= 0, max <= 0 |
| complex-scenario | true | none | 707-1061 (point 884) | min >= 600, max <= 1200 |
