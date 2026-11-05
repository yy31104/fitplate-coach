"""Dish-level calorie metrics for a Nutrition5k run.

- MAE%: mean absolute calorie error divided by the mean true calories, x100.
  This is the "caloric MAE %" convention of the Nutrition5k paper.
- Interval coverage: share of dishes whose true calories fall inside the
  predicted [min, max] of total_calories, grouped by dish confidence. Dish
  confidence is the lowest item confidence (a dish is only as sure as its
  least certain item); dishes with no items form the "no_items" group.
- Large-portion bias: dishes at or above the 75th percentile of true mass
  are "large". For them and for the rest: mean signed error (predicted minus
  true) in kcal, %, and grams, and the share over- and under-estimated.
"""

import math
from dataclasses import dataclass
from statistics import mean, median

CONFIDENCE_ORDER = ("low", "medium", "high")
CONFIDENCE_GROUPS = ("high", "medium", "low", "no_items")
LARGE_PORTION_PERCENTILE = 75


@dataclass(frozen=True)
class DishPrediction:
    dish_id: str
    true_calories: float
    true_mass_g: float
    predicted_min: int | None = None
    predicted_max: int | None = None
    predicted_point: int | None = None
    predicted_mass_g: int | None = None
    item_confidences: tuple[str, ...] = ()
    error: str | None = None
    # Result of check_analysis_consistency on the returned analysis; None
    # when there was no analysis.
    consistent: bool | None = None

    @property
    def scored(self) -> bool:
        return self.error is None and self.predicted_point is not None

    @property
    def confidence_group(self) -> str:
        if not self.item_confidences:
            return "no_items"
        return min(self.item_confidences, key=CONFIDENCE_ORDER.index)

    @property
    def signed_error(self) -> float:
        return float(self.predicted_point or 0) - self.true_calories

    @property
    def covered(self) -> bool:
        return (
            self.predicted_min is not None
            and self.predicted_max is not None
            and self.predicted_min <= self.true_calories <= self.predicted_max
        )


def compute_metrics(predictions: list[DishPrediction]) -> dict[str, object]:
    scored = [prediction for prediction in predictions if prediction.scored]
    failed = [prediction for prediction in predictions if not prediction.scored]

    return {
        "dishes": len(predictions),
        "scored": len(scored),
        "failed": len(failed),
        "failure_reasons": _count(prediction.error or "no prediction" for prediction in failed),
        "consistent_analyses": sum(1 for prediction in scored if prediction.consistent),
        "calories": _calorie_error(scored),
        "interval_coverage": _coverage(scored),
        "large_portion_bias": _large_portion_bias(scored),
    }


def _calorie_error(scored: list[DishPrediction]) -> dict[str, float | None]:
    if not scored:
        return {"mae_kcal": None, "mae_pct": None, "median_ape_pct": None, "mean_true_kcal": None}

    absolute = [abs(prediction.signed_error) for prediction in scored]
    mean_true = mean(prediction.true_calories for prediction in scored)
    return {
        "mae_kcal": _round(mean(absolute)),
        "mae_pct": _round(100 * mean(absolute) / mean_true) if mean_true else None,
        "median_ape_pct": _round(
            median(100 * abs(p.signed_error) / p.true_calories for p in scored)
        ),
        "mean_true_kcal": _round(mean_true),
    }


def _coverage(scored: list[DishPrediction]) -> dict[str, dict[str, float | int | None]]:
    groups: dict[str, dict[str, float | int | None]] = {}
    for group in (*CONFIDENCE_GROUPS, "all"):
        members = [p for p in scored if group == "all" or p.confidence_group == group]
        covered = sum(1 for p in members if p.covered)
        widths = [
            100 * (p.predicted_max - p.predicted_min) / p.true_calories  # type: ignore[operator]
            for p in members
            if p.predicted_min is not None and p.predicted_max is not None
        ]
        groups[group] = {
            "dishes": len(members),
            "covered": covered,
            "coverage_pct": _round(100 * covered / len(members)) if members else None,
            "mean_width_pct_of_true": _round(mean(widths)) if widths else None,
        }
    return groups


def _large_portion_bias(scored: list[DishPrediction]) -> dict[str, object]:
    if not scored:
        return {"threshold_mass_g": None, "large": _bias([]), "rest": _bias([])}

    threshold = _percentile([p.true_mass_g for p in scored], LARGE_PORTION_PERCENTILE)
    large = [p for p in scored if p.true_mass_g >= threshold]
    rest = [p for p in scored if p.true_mass_g < threshold]
    return {
        "threshold_mass_g": _round(threshold),
        "large": _bias(large),
        "rest": _bias(rest),
    }


def _bias(members: list[DishPrediction]) -> dict[str, object]:
    if not members:
        return {
            "dishes": 0,
            "mean_signed_error_kcal": None,
            "mean_signed_error_pct": None,
            "mean_signed_mass_error_g": None,
            "over_pct": None,
            "under_pct": None,
            "direction": "n/a",
        }

    signed = [p.signed_error for p in members]
    over = sum(1 for error in signed if error > 0)
    under = sum(1 for error in signed if error < 0)
    mass_errors = [
        p.predicted_mass_g - p.true_mass_g for p in members if p.predicted_mass_g is not None
    ]
    mean_signed = mean(signed)
    return {
        "dishes": len(members),
        "mean_signed_error_kcal": _round(mean_signed),
        "mean_signed_error_pct": _round(
            mean(100 * p.signed_error / p.true_calories for p in members)
        ),
        "mean_signed_mass_error_g": _round(mean(mass_errors)) if mass_errors else None,
        "over_pct": _round(100 * over / len(members)),
        "under_pct": _round(100 * under / len(members)),
        "direction": "over" if mean_signed > 0 else "under" if mean_signed < 0 else "none",
    }


def _percentile(values: list[float], percentile: int) -> float:
    """Nearest-rank percentile."""
    ordered = sorted(values)
    rank = max(1, math.ceil(percentile / 100 * len(ordered)))
    return ordered[rank - 1]


def _count(values) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _round(value: float) -> float:
    return round(value, 1)
