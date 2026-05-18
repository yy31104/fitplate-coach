from app.ai.provider import AIProvider, FakeAIProvider, ImageRef, ProviderResult
from app.schemas.food import FoodAnalysis


def test_fake_ai_provider_satisfies_protocol() -> None:
    assert isinstance(FakeAIProvider(), AIProvider)


def test_fake_ai_provider_returns_valid_food_analysis_for_each_scenario() -> None:
    provider = FakeAIProvider()

    scenarios = [
        (345_678, 3, []),
        (745_678, 2, ["low_confidence"]),
        (845_678, 0, ["non_food_image"]),
        (945_678, 5, []),
    ]

    for size_bytes, items_count, safety_flags in scenarios:
        result = provider.call("prompt", ImageRef(content_type="image/jpeg", size_bytes=size_bytes))
        analysis = FoodAnalysis.model_validate(result.raw_analysis)

        assert isinstance(result, ProviderResult)
        assert analysis.schema_version == "food_analysis.v1"
        assert analysis.mode == "ai"
        assert analysis.items_count == items_count
        assert analysis.safety_flags == safety_flags


def test_fake_ai_provider_result_usage_fields_are_zero() -> None:
    result = FakeAIProvider().call(
        "prompt",
        ImageRef(content_type="image/jpeg", size_bytes=345_678),
    )

    assert result.input_tokens == 0
    assert result.output_tokens == 0
    assert result.cost_usd == 0.0
    assert result.provider_latency_ms is None


def test_image_ref_data_does_not_change_fake_provider_scenario() -> None:
    provider = FakeAIProvider()

    without_data = provider.call(
        "prompt",
        ImageRef(content_type="image/jpeg", size_bytes=345_678),
    )
    with_data = provider.call(
        "prompt",
        ImageRef(
            content_type="image/jpeg",
            size_bytes=345_678,
            data=b"not used for fake routing",
        ),
    )

    assert FoodAnalysis.model_validate(with_data.raw_analysis).items_count == (
        FoodAnalysis.model_validate(without_data.raw_analysis).items_count
    )


def test_fake_ai_provider_ignores_api_key_environment(monkeypatch) -> None:
    monkeypatch.setenv("FITPLATE_AI_PROVIDER_API_KEY", "not-used")

    result = FakeAIProvider().call(
        "prompt",
        ImageRef(content_type="image/jpeg", size_bytes=345_678),
    )

    assert FoodAnalysis.model_validate(result.raw_analysis).items_count == 3
