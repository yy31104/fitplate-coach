# Model Run Metrics Report

schema_version: `model_run_metrics.v1`

Total runs: 6
Success rate: 0.8333
Error rate: 0.1667
Error count: 1
Runs with safety flags: 3

## Latency

Count: 6
Min: 8 ms
Max: 55 ms
Mean: 26.7 ms

## Tokens And Cost

Total input tokens: 360
Total output tokens: 95
Total cost USD: 0.019500
Mean cost USD: 0.003250

## Breakdowns

### Runs by route

- `POST /api/v0/food/analyze`: 1
- `POST /api/v0/food/analyze/mock`: 4
- `POST /api/v0/food/corrections/mock`: 1

### Runs by mode

- `ai`: 3
- `mock`: 3

### Runs by model

- `fake-food-vision-v1`: 3
- `mock`: 3

### Runs by prompt

- `food_analysis@v1`: 3
- `none`: 3

### Errors by code

- `analysis_failed`: 1

### Safety flag counts

- `low_confidence`: 1
- `non_food_image`: 1
- `schema_validation_failed`: 1

## Schema Versions Seen

- `model_run.v1`
