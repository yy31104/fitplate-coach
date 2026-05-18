from app.schemas.food import CalorieRange, Confidence

CALORIE_DENSITY_KCAL_PER_GRAM: dict[str, float] = {
    "rice_cooked": 1.30,
    "chicken_breast": 1.65,
    "mixed_salad": 0.35,
    "avocado": 1.60,
    "pasta_cooked": 1.55,
    "salmon": 2.08,
    "beans": 1.27,
    "fried_egg": 1.96,
    "tortilla": 3.12,
    "generic_mixed_food": 1.50,
}

CONFIDENCE_MARGIN: dict[Confidence, float] = {
    "high": 0.10,
    "medium": 0.20,
    "low": 0.30,
}


def calorie_range_for(
    grams: int,
    density_key: str,
    confidence: Confidence,
) -> CalorieRange:
    density = CALORIE_DENSITY_KCAL_PER_GRAM.get(
        density_key,
        CALORIE_DENSITY_KCAL_PER_GRAM["generic_mixed_food"],
    )
    return calorie_range_from_density(grams=grams, density=density, confidence=confidence)


def calorie_range_from_density(
    grams: int,
    density: float,
    confidence: Confidence,
) -> CalorieRange:
    point_estimate = round(grams * density)
    margin = CONFIDENCE_MARGIN[confidence]

    return CalorieRange(
        min=round(point_estimate * (1 - margin)),
        max=round(point_estimate * (1 + margin)),
        point_estimate=point_estimate,
    )


def sum_calorie_ranges(ranges: list[CalorieRange]) -> CalorieRange:
    return CalorieRange(
        min=sum(item.min for item in ranges),
        max=sum(item.max for item in ranges),
        point_estimate=sum(item.point_estimate for item in ranges),
    )
