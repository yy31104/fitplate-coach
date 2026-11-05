"""Run an analyzer over the Nutrition5k subset and write a report."""

import json
import os
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path

from app.ai.analyzer import AIFoodAnalyzer, FoodAnalyzer, MockFoodAnalyzer
from app.ai.openai_provider import OpenAIProvider
from app.ai.provider import AIAnalysisError, FakeAIProvider, ImageRef
from app.nutrition5k.dataset import Manifest, rgb_path
from app.nutrition5k.metrics import CONFIDENCE_GROUPS, DishPrediction, compute_metrics
from app.schemas.food import FoodAnalyzeMockRequest

PROVIDERS = ("fake", "mock", "openai")
PAID_PROVIDERS = {"openai"}
DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"
DEFAULT_MAX_COST_USD = 1.0


class PaidCallNotConfirmedError(RuntimeError):
    pass


def build_analyzer(
    provider: str,
    *,
    confirm_paid_calls: bool = False,
    api_key: str | None = None,
    model: str = DEFAULT_OPENAI_MODEL,
    timeout_seconds: int = 60,
) -> FoodAnalyzer:
    """Return the analyzer for `provider`. Paid providers need explicit consent."""
    if provider == "fake":
        return AIFoodAnalyzer(provider=FakeAIProvider())
    if provider == "mock":
        return MockFoodAnalyzer()
    if provider == "openai":
        if not confirm_paid_calls:
            raise PaidCallNotConfirmedError(
                "--provider openai sends every subset image to a paid API. "
                "Re-run with --confirm-paid-calls to proceed."
            )
        key = api_key if api_key is not None else os.environ.get("FITPLATE_AI_PROVIDER_API_KEY")
        if not key:
            raise PaidCallNotConfirmedError("FITPLATE_AI_PROVIDER_API_KEY is not set.")
        return AIFoodAnalyzer(
            provider=OpenAIProvider(api_key=key, model=model, timeout_seconds=timeout_seconds)
        )
    raise ValueError(f"Unknown provider {provider!r}. Expected one of {PROVIDERS}.")


def run_subset(
    manifest: Manifest,
    *,
    data_dir: Path,
    analyzer: FoodAnalyzer,
    limit: int | None = None,
    max_cost_usd: float | None = None,
    on_progress: Callable[[int, int, DishPrediction], None] | None = None,
) -> tuple[list[DishPrediction], dict[str, float | int | bool]]:
    dishes = manifest.dishes[:limit] if limit is not None else manifest.dishes
    predictions: list[DishPrediction] = []
    cost_usd = 0.0
    input_tokens = 0
    output_tokens = 0
    stopped_for_cost = False

    for index, dish in enumerate(dishes, start=1):
        if max_cost_usd is not None and cost_usd >= max_cost_usd:
            stopped_for_cost = True
            break

        path = rgb_path(data_dir, dish.dish_id)
        if not path.exists():
            prediction = DishPrediction(
                dish_id=dish.dish_id,
                true_calories=dish.total_calories,
                true_mass_g=dish.total_mass_g,
                error="image_missing",
            )
        else:
            data = path.read_bytes()
            payload = FoodAnalyzeMockRequest(
                filename=f"{dish.dish_id}.png",
                content_type="image/png",
                size_bytes=len(data),
                last_modified_ms=0,
            )
            image_ref = ImageRef(content_type="image/png", size_bytes=len(data), data=data)
            try:
                result = analyzer.analyze(payload, image_ref=image_ref)
            except AIAnalysisError as exc:
                prediction = DishPrediction(
                    dish_id=dish.dish_id,
                    true_calories=dish.total_calories,
                    true_mass_g=dish.total_mass_g,
                    error=type(exc).__name__,
                )
            else:
                analysis = result.analysis
                cost_usd += result.usage.cost_usd
                input_tokens += result.usage.input_tokens
                output_tokens += result.usage.output_tokens
                prediction = DishPrediction(
                    dish_id=dish.dish_id,
                    true_calories=dish.total_calories,
                    true_mass_g=dish.total_mass_g,
                    predicted_min=analysis.total_calories.min,
                    predicted_max=analysis.total_calories.max,
                    predicted_point=analysis.total_calories.point_estimate,
                    predicted_mass_g=sum(item.portion.grams_estimate for item in analysis.items),
                    item_confidences=tuple(item.confidence for item in analysis.items),
                )

        predictions.append(prediction)
        if on_progress is not None:
            on_progress(index, len(dishes), prediction)

    usage = {
        "cost_usd": round(cost_usd, 6),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "stopped_for_cost_cap": stopped_for_cost,
    }
    return predictions, usage


def build_report(
    *,
    manifest: Manifest,
    provider: str,
    model: str,
    predictions: list[DishPrediction],
    usage: dict[str, float | int | bool],
) -> dict[str, object]:
    return {
        "schema_version": "nutrition5k_eval.v1",
        "dataset": manifest.dataset,
        "license": manifest.license,
        "split_file": manifest.split_file,
        "image": manifest.image,
        "provider": provider,
        "model": model,
        "usage": usage,
        "metrics": compute_metrics(predictions),
        "predictions": [asdict(prediction) for prediction in predictions],
    }


def write_report(report: dict[str, object], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "report.json"
    markdown_path = out_dir / "REPORT.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, markdown_path


def render_markdown(report: dict[str, object]) -> str:
    metrics = report["metrics"]
    calories = metrics["calories"]  # type: ignore[index]
    coverage = metrics["interval_coverage"]  # type: ignore[index]
    bias = metrics["large_portion_bias"]  # type: ignore[index]
    usage = report["usage"]
    license_info = report["license"]

    lines = [
        f"# Nutrition5k evaluation: provider `{report['provider']}`",
        "",
        "Generated by `python -m app.nutrition5k evaluate`. Do not edit by hand.",
        "",
    ]
    if report["provider"] in ("fake", "mock"):
        lines += [
            "> **Pipeline check, not an accuracy result.** The fake and mock analyzers "
            "pick a canned plate from file size or filename and never look at the image. "
            "These numbers show that download, analysis, scoring and reporting run end to "
            "end. Run the real-provider command in `docs/evaluation/NUTRITION5K.md` for a "
            "meaningful score.",
            "",
        ]
    lines += [
        "## Run",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Dataset | {report['dataset']} (`{report['split_file']}`, overhead `rgb.png`) |",
        f"| Provider / model | `{report['provider']}` / `{report['model']}` |",
        f"| Dishes | {metrics['dishes']} ({metrics['scored']} scored, {metrics['failed']} failed) |",  # type: ignore[index]
        f"| Cost | ${usage['cost_usd']:.4f} ({usage['input_tokens']} input / {usage['output_tokens']} output tokens) |",  # type: ignore[index]
        "",
    ]
    if metrics["failure_reasons"]:  # type: ignore[index]
        reasons = ", ".join(f"`{k}`: {v}" for k, v in metrics["failure_reasons"].items())  # type: ignore[index]
        lines += [f"Failures: {reasons}.", ""]

    lines += [
        "## Calorie error",
        "",
        "MAE% = mean absolute error / mean true calories × 100 (Nutrition5k paper convention).",
        "",
        "| MAE (kcal) | MAE % | Median APE % | Mean true kcal |",
        "| ---: | ---: | ---: | ---: |",
        f"| {_fmt(calories['mae_kcal'])} | {_fmt(calories['mae_pct'])} | "
        f"{_fmt(calories['median_ape_pct'])} | {_fmt(calories['mean_true_kcal'])} |",
        "",
        "## Interval coverage by confidence",
        "",
        "Covered = true calories inside the predicted `total_calories` [min, max]. "
        "Dish confidence = lowest item confidence.",
        "",
        "| Confidence | Dishes | Covered | Coverage % | Mean width (% of true) |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for group in (*CONFIDENCE_GROUPS, "all"):
        row = coverage[group]
        lines.append(
            f"| {group} | {row['dishes']} | {row['covered']} | {_fmt(row['coverage_pct'])} | "
            f"{_fmt(row['mean_width_pct_of_true'])} |"
        )

    lines += [
        "",
        "## Bias on large portions",
        "",
        f"Large = true mass ≥ {_fmt(bias['threshold_mass_g'])} g (75th percentile of scored dishes). "
        "Signed error = predicted − true.",
        "",
        "| Group | Dishes | Direction | Mean signed kcal | Mean signed % | Mean signed grams | Over % | Under % |",
        "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for group in ("large", "rest"):
        row = bias[group]
        lines.append(
            f"| {group} | {row['dishes']} | {row['direction']} | {_fmt(row['mean_signed_error_kcal'])} | "
            f"{_fmt(row['mean_signed_error_pct'])} | {_fmt(row['mean_signed_mass_error_g'])} | "
            f"{_fmt(row['over_pct'])} | {_fmt(row['under_pct'])} |"
        )

    lines += [
        "",
        "## Data and license",
        "",
        f"{license_info['attribution']} License: [{license_info['name']}]({license_info['url']}). "  # type: ignore[index]
        f"Source: {license_info['source']}.",  # type: ignore[index]
        "",
        f"Citation: {license_info['citation']}",  # type: ignore[index]
        "",
    ]
    return "\n".join(lines)


def _fmt(value: object) -> str:
    return "–" if value is None else str(value)
