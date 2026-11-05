# Nutrition5k subset evaluation

Measures how close the food analyzer's calorie estimates are to weighed ground truth on 100 real cafeteria plates.

Code: [`apps/api/app/nutrition5k/`](../../apps/api/app/nutrition5k/). Subset manifest: [`subset_manifest.json`](../../apps/api/evaluation/nutrition5k/subset_manifest.json). Sample report (fake provider): [`sample_fake/REPORT.md`](../../apps/api/evaluation/nutrition5k/sample_fake/REPORT.md).

## License

Nutrition5k is published by Google Research at <https://github.com/google-research-datasets/Nutrition5k>. Its README says: "We release all Nutrition5k data under the Creative Commons V4.0 license. You are free to share and adapt this data for any purpose, even commercially." The linked license is [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The GitHub repository has no separate `LICENSE` file; the README section "License & Contact" is the license statement.

Obligations under CC BY 4.0 and how this repo meets them:

- **Attribution and citation.** The manifest, every generated report and this page name the dataset, its authors, the CVPR 2021 paper, the license and its URL.
- **Indicate changes.** This repo uses a 100-dish subset. It keeps only `dish_id`, total calories, total mass and ingredient names from the metadata CSVs, with values rounded to 0.1. The images are unmodified.
- **Images are not redistributed.** They stay in a gitignored folder (`apps/api/evaluation/nutrition5k/data/`). The manifest stores each image's SHA-256 so a later download can be verified.

The dataset README also notes a bias: all plates come from a few cafeterias in California, so the subset does not represent other cuisines.

## What is downloaded

From the public bucket `gs://nutrition5k_dataset` over HTTPS (`storage.googleapis.com`), with no credentials:

| File | Why |
| --- | --- |
| `metadata/dish_metadata_cafe1.csv`, `metadata/dish_metadata_cafe2.csv` | Ground-truth calories, mass and ingredients |
| `dish_ids/splits/depth_test_ids.txt` | Official test split. Overhead RGB exists only for depth-split dishes. |
| `imagery/realsense_overhead/<dish_id>/rgb.png` × 100 | Overhead RGB photo, about 400 KB each, 39 MB in total |

Depth images, side-angle videos and the 181 GB tarball are never fetched. `default_fetch` refuses any URL outside the bucket. Dish ids must match `dish_\d{10}` before they become path components.

**Subset rule:** take the depth test ids with calories > 0 and mass > 0, sort them by (mass, id), and keep 100 at evenly spaced ranks. The result is deterministic and runs from 5 g to 871 g plates (1 to 1,050 kcal), so large portions are represented.

## Metrics

All metrics are per dish, using the analysis's `total_calories`.

| Metric | Definition |
| --- | --- |
| **MAE %** | mean \|predicted point − true\| ÷ mean true calories × 100. This is the Nutrition5k paper's "caloric MAE %". Median per-dish APE is also reported. |
| **Interval coverage** | Share of dishes with `min ≤ true ≤ max`, grouped by **dish confidence**. Dish confidence is the lowest item confidence: a plate with one `low` item is `low`. Plates with no items form a `no_items` group. Mean interval width (% of true) is reported next to it. Calibrated ranges cover about equally often in every group while getting narrower as confidence rises. Low coverage at `high` means the ranges are overconfident. |
| **Large-portion bias** | Large means true mass ≥ the 75th percentile of the scored dishes. For large plates and for the rest: mean signed error (predicted − true) in kcal, in %, and in grams (sum of item `grams_estimate` − true mass); the share over- and under-estimated; and the direction (`over` / `under`). |

A dish whose analysis raises an error, or whose image is missing, counts as `failed` and is excluded from scoring. The reason is counted.

## Commands

From `apps/api` after `pip install -e ".[dev]"`:

```bash
./.venv/bin/python -m app.nutrition5k download
```

```bash
./.venv/bin/python -m app.nutrition5k evaluate --provider fake
```

```bash
./.venv/bin/python -m app.nutrition5k evaluate --provider mock
```

`download` fetches the 100 images listed in the committed manifest and checks their SHA-256. `evaluate` writes `REPORT.md` and `report.json` to `evaluation/nutrition5k/runs/<provider>/` (gitignored). `prepare --size N` rebuilds the manifest from the bucket.

### Real provider (not run here; needs your key and costs money)

```bash
FITPLATE_AI_PROVIDER_API_KEY=<your key> ./.venv/bin/python -m app.nutrition5k evaluate --provider openai --confirm-paid-calls --max-cost-usd 1.00 --limit 10 --out-dir evaluation/nutrition5k/runs/openai-smoke
```

```bash
FITPLATE_AI_PROVIDER_API_KEY=<your key> ./.venv/bin/python -m app.nutrition5k evaluate --provider openai --confirm-paid-calls --max-cost-usd 1.00 --out-dir evaluation/nutrition5k/runs/openai-$(date +%F)
```

- Without `--confirm-paid-calls` the command exits with code 2 before creating a client.
- Each dish is one request, with the overhead PNG sent as image bytes. `--max-cost-usd` (default 1.00) stops starting new requests once the cost reported by the provider reaches the cap. The cost uses the pricing table in `openai_provider.py`; a model missing from that table reports $0, so the cap would not stop it.
- `--model` selects the OpenAI model (default `gpt-5.4-mini`).
- The cost of a 100-dish run has not been measured. At the repo's `gpt-5.4-mini` prices ($0.75 / $4.50 per million input / output tokens), roughly 1–2k input and 300–500 output tokens per dish would be $0.1–0.5.
- Run the 10-dish smoke command first and check `report.json` → `usage` before running all 100.

## Sample report

[`sample_fake/REPORT.md`](../../apps/api/evaluation/nutrition5k/sample_fake/REPORT.md) is the fake provider on all 100 dishes. **It checks the pipeline; it is not an accuracy result.** The fake picks a canned plate from file size (every subset PNG is < 700 KB, so every dish gets the same chicken/rice/salad plate) and never looks at the image. The test `test_committed_sample_report_metrics_match_its_predictions` recomputes the report's metrics from its stored predictions.
