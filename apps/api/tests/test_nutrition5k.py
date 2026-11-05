"""Nutrition5k evaluation tool. No network: every fetch is a local stub."""

import hashlib
import json
from pathlib import Path

import pytest

import app.nutrition5k.runner as runner
from app.ai.analyzer import AnalyzerResult, MockFoodAnalyzer, ProviderUsage
from app.nutrition5k import __main__ as cli
from app.nutrition5k.dataset import (
    BUCKET_URL,
    SPLIT_FILE,
    DishRecord,
    Manifest,
    build_manifest,
    default_fetch,
    download_images,
    parse_dish_metadata,
    prepare_subset,
    rgb_path,
    rgb_url,
    select_subset,
    validate_dish_id,
)
from app.nutrition5k.metrics import DishPrediction, compute_metrics
from app.nutrition5k.runner import (
    PaidCallNotConfirmedError,
    build_analyzer,
    build_report,
    render_markdown,
    run_subset,
)

API_ROOT = Path(__file__).resolve().parents[1]
COMMITTED_MANIFEST = API_ROOT / "evaluation" / "nutrition5k" / "subset_manifest.json"
COMMITTED_SAMPLE = API_ROOT / "evaluation" / "nutrition5k" / "sample_fake" / "report.json"

CSV = (
    "dish_1000000001,300.5,193.0,12.3,28.2,18.6,"
    "ingr_0000000508,soy sauce,3.4,1.8,0.02,0.17,0.28,"
    "ingr_0000000026,white rice,150.0,195.0,0.4,43.0,4.0\n"
    "dish_1000000002,0.0,0.0,0,0,0\n"
    "not_a_dish,1,1,1,1,1\n"
    "dish_1000000003,80.0,40.0,1,1,1,ingr_0000000001,apple,40.0,80.0,0,20,0\n"
)


def _record(dish_id: str, mass: float, calories: float = 100.0) -> DishRecord:
    return DishRecord(dish_id=dish_id, total_calories=calories, total_mass_g=mass, ingredients=())


def _ids(count: int) -> list[str]:
    return [f"dish_{1_000_000_000 + index}" for index in range(count)]


# --- metadata and subset ------------------------------------------------------


def test_parse_dish_metadata_reads_totals_and_ingredient_names() -> None:
    records = parse_dish_metadata(CSV)

    assert set(records) == {"dish_1000000001", "dish_1000000002", "dish_1000000003"}
    assert records["dish_1000000001"].total_calories == 300.5
    assert records["dish_1000000001"].total_mass_g == 193.0
    assert records["dish_1000000001"].ingredients == ("soy sauce", "white rice")
    assert records["dish_1000000002"].ingredients == ()


def test_select_subset_spreads_over_mass_and_is_deterministic() -> None:
    ids = _ids(10)
    records = {dish_id: _record(dish_id, mass=10.0 * (index + 1)) for index, dish_id in enumerate(ids)}

    subset = select_subset(records, reversed(ids), size=4)

    assert [record.total_mass_g for record in subset] == [10.0, 40.0, 70.0, 100.0]
    assert subset == select_subset(records, ids, size=4)


def test_select_subset_drops_zero_rows_and_ids_outside_the_split() -> None:
    records = parse_dish_metadata(CSV)

    subset = select_subset(records, ["dish_1000000001", "dish_1000000002"], size=5)

    assert [record.dish_id for record in subset] == ["dish_1000000001"]


@pytest.mark.parametrize("bad", ["../etc/passwd", "dish_1", "dish_123456789a", "dish_1000000001/.."])
def test_dish_ids_that_could_escape_the_data_dir_are_rejected(bad: str, tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        validate_dish_id(bad)
    with pytest.raises(ValueError):
        rgb_path(tmp_path, bad)


def test_manifest_with_a_bad_dish_id_does_not_load() -> None:
    manifest = build_manifest([_record("dish_1000000001", 10.0)])
    raw = json.loads(manifest.to_json())
    raw["dishes"][0]["dish_id"] = "../../secrets"

    with pytest.raises(ValueError):
        Manifest.from_json(json.dumps(raw))


def test_default_fetch_refuses_urls_outside_the_bucket() -> None:
    with pytest.raises(ValueError):
        default_fetch("https://example.com/rgb.png")


def test_rgb_url_points_at_the_overhead_rgb_image_only() -> None:
    assert rgb_url("dish_1000000001") == (
        f"{BUCKET_URL}/imagery/realsense_overhead/dish_1000000001/rgb.png"
    )


# --- download -----------------------------------------------------------------


class StubBucket:
    def __init__(self, files: dict[str, bytes]) -> None:
        self.files = files
        self.requested: list[str] = []

    def __call__(self, url: str) -> bytes:
        self.requested.append(url)
        return self.files[url.removeprefix(BUCKET_URL + "/")]


def _bucket() -> StubBucket:
    return StubBucket(
        {
            "metadata/dish_metadata_cafe1.csv": CSV.encode(),
            "metadata/dish_metadata_cafe2.csv": b"",
            SPLIT_FILE: b"dish_1000000001\ndish_1000000003\n",
            "imagery/realsense_overhead/dish_1000000001/rgb.png": b"png-1",
            "imagery/realsense_overhead/dish_1000000003/rgb.png": b"png-3",
        }
    )


def test_prepare_downloads_only_metadata_split_and_rgb(tmp_path: Path) -> None:
    bucket = _bucket()

    manifest = prepare_subset(size=100, data_dir=tmp_path, fetch=bucket)

    assert [dish.dish_id for dish in manifest.dishes] == ["dish_1000000003", "dish_1000000001"]
    assert all(url.endswith((".csv", ".txt", "/rgb.png")) for url in bucket.requested)
    assert not any("depth" in url and url.endswith(".png") for url in bucket.requested)
    assert manifest.dishes[0].rgb_sha256 == hashlib.sha256(b"png-3").hexdigest()
    assert manifest.dishes[0].rgb_size_bytes == 5
    assert rgb_path(tmp_path, "dish_1000000001").read_bytes() == b"png-1"


def test_download_verifies_hashes_and_skips_verified_files(tmp_path: Path) -> None:
    manifest = prepare_subset(size=100, data_dir=tmp_path / "first", fetch=_bucket())

    bucket = _bucket()
    assert download_images(manifest, data_dir=tmp_path / "second", fetch=bucket) == [
        "dish_1000000003",
        "dish_1000000001",
    ]
    again = _bucket()
    assert download_images(manifest, data_dir=tmp_path / "second", fetch=again) == []
    assert again.requested == []

    tampered = _bucket()
    tampered.files["imagery/realsense_overhead/dish_1000000001/rgb.png"] = b"changed"
    with pytest.raises(ValueError, match="sha256"):
        download_images(manifest, data_dir=tmp_path / "third", fetch=tampered)


# --- metrics ------------------------------------------------------------------


def _prediction(
    dish_id: str,
    true: float,
    mass: float,
    point: int,
    low: int,
    high: int,
    confidences: tuple[str, ...] = ("medium",),
    grams: int | None = None,
) -> DishPrediction:
    return DishPrediction(
        dish_id=dish_id,
        true_calories=true,
        true_mass_g=mass,
        predicted_min=low,
        predicted_max=high,
        predicted_point=point,
        predicted_mass_g=grams if grams is not None else int(mass),
        item_confidences=confidences,
    )


def test_mae_pct_uses_mean_true_calories() -> None:
    metrics = compute_metrics(
        [
            _prediction("dish_1000000001", true=100, mass=100, point=150, low=120, high=180),
            _prediction("dish_1000000002", true=300, mass=200, point=250, low=200, high=300),
        ]
    )

    # |150-100| + |250-300| = 100; MAE 50; mean true 200 -> 25 %.
    assert metrics["calories"] == {
        "mae_kcal": 50.0,
        "mae_pct": 25.0,
        "median_ape_pct": 33.3,
        "mean_true_kcal": 200.0,
    }


def test_coverage_is_grouped_by_lowest_item_confidence() -> None:
    metrics = compute_metrics(
        [
            _prediction("dish_1000000001", 100, 100, 100, 90, 110, ("high",)),
            _prediction("dish_1000000002", 100, 100, 200, 180, 220, ("high",)),
            _prediction("dish_1000000003", 100, 100, 100, 80, 120, ("high", "medium")),
            _prediction("dish_1000000004", 100, 100, 100, 70, 130, ("medium", "low")),
            _prediction("dish_1000000005", 100, 100, 0, 0, 0, ()),
        ]
    )
    coverage = metrics["interval_coverage"]

    assert coverage["high"]["dishes"] == 2
    assert coverage["high"]["coverage_pct"] == 50.0
    assert coverage["medium"] == {"dishes": 1, "covered": 1, "coverage_pct": 100.0, "mean_width_pct_of_true": 40.0}
    assert coverage["low"]["covered"] == 1
    assert coverage["no_items"]["coverage_pct"] == 0.0
    assert coverage["all"]["covered"] == 3


def test_interval_bounds_are_inclusive() -> None:
    metrics = compute_metrics([_prediction("dish_1000000001", 120, 100, 100, 80, 120)])

    assert metrics["interval_coverage"]["all"]["covered"] == 1


def test_large_portions_report_underestimation() -> None:
    predictions = [
        _prediction(f"dish_100000000{index}", true=100, mass=100, point=110, low=0, high=999)
        for index in range(1, 4)
    ] + [
        _prediction("dish_1000000009", true=800, mass=600, point=500, low=0, high=999, grams=400),
    ]

    bias = compute_metrics(predictions)["large_portion_bias"]

    assert bias["threshold_mass_g"] == 100.0  # nearest-rank p75 of [100, 100, 100, 600]
    # Every dish is >= 100 g, so all are "large"; only the 600 g dish is under.
    assert bias["large"]["dishes"] == 4
    assert bias["large"]["under_pct"] == 25.0
    assert bias["large"]["mean_signed_error_kcal"] == -67.5
    assert bias["large"]["direction"] == "under"
    assert bias["large"]["mean_signed_mass_error_g"] == -50.0
    assert bias["rest"]["direction"] == "n/a"


def test_failures_are_counted_and_not_scored() -> None:
    metrics = compute_metrics(
        [
            _prediction("dish_1000000001", 100, 100, 100, 90, 110),
            DishPrediction("dish_1000000002", 100, 100, error="AIAnalysisError"),
            DishPrediction("dish_1000000003", 100, 100, error="image_missing"),
        ]
    )

    assert metrics["scored"] == 1
    assert metrics["failed"] == 2
    assert metrics["failure_reasons"] == {"AIAnalysisError": 1, "image_missing": 1}
    assert metrics["calories"]["mae_kcal"] == 0.0


# --- runner -------------------------------------------------------------------


def _manifest_with_images(tmp_path: Path, count: int = 3) -> Manifest:
    records = [_record(dish_id, mass=50.0 * (index + 1), calories=80.0 * (index + 1))
               for index, dish_id in enumerate(_ids(count))]
    manifest = build_manifest(records)
    for dish in manifest.dishes:
        path = rgb_path(tmp_path, dish.dish_id)
        path.parent.mkdir(parents=True)
        path.write_bytes(b"\x89PNG fake " + dish.dish_id.encode())
    return manifest


@pytest.mark.parametrize("provider", ["fake", "mock"])
def test_pipeline_runs_end_to_end_without_network(tmp_path: Path, provider: str) -> None:
    manifest = _manifest_with_images(tmp_path)
    analyzer = build_analyzer(provider)

    predictions, usage = run_subset(manifest, data_dir=tmp_path, analyzer=analyzer)
    report = build_report(manifest=manifest, provider=provider, model=analyzer.model,
                          predictions=predictions, usage=usage)

    assert report["metrics"]["scored"] == 3
    assert usage["cost_usd"] == 0.0
    markdown = render_markdown(report)
    for heading in ("## Calorie error", "## Interval coverage by confidence", "## Bias on large portions"):
        assert heading in markdown
    assert "Pipeline check, not an accuracy result" in markdown
    assert "CC BY 4.0" in markdown


def test_missing_image_is_reported_as_failure(tmp_path: Path) -> None:
    manifest = _manifest_with_images(tmp_path)
    rgb_path(tmp_path, manifest.dishes[0].dish_id).unlink()

    predictions, _ = run_subset(manifest, data_dir=tmp_path, analyzer=MockFoodAnalyzer())

    assert predictions[0].error == "image_missing"
    assert all(prediction.scored for prediction in predictions[1:])


def test_the_analyzer_receives_the_image_bytes(tmp_path: Path) -> None:
    manifest = _manifest_with_images(tmp_path, count=1)
    seen: list[bytes] = []

    class Recording:
        mode = "ai"
        model = "recording"

        def analyze(self, payload, *, image_ref=None):
            seen.append(image_ref.data)
            return MockFoodAnalyzer().analyze(payload)

    run_subset(manifest, data_dir=tmp_path, analyzer=Recording())

    assert seen == [rgb_path(tmp_path, manifest.dishes[0].dish_id).read_bytes()]


def test_cost_cap_stops_new_requests(tmp_path: Path) -> None:
    manifest = _manifest_with_images(tmp_path, count=5)

    class Priced:
        mode = "ai"
        model = "priced"
        calls = 0

        def analyze(self, payload, *, image_ref=None):
            Priced.calls += 1
            result = MockFoodAnalyzer().analyze(payload)
            return AnalyzerResult(analysis=result.analysis,
                                  usage=ProviderUsage(input_tokens=1, output_tokens=1, cost_usd=0.6))

    predictions, usage = run_subset(manifest, data_dir=tmp_path, analyzer=Priced(), max_cost_usd=1.0)

    assert Priced.calls == 2
    assert len(predictions) == 2
    assert usage["stopped_for_cost_cap"] is True


# --- the paid provider is never reached without consent -------------------------


def test_openai_needs_explicit_confirmation(monkeypatch) -> None:
    monkeypatch.setenv("FITPLATE_AI_PROVIDER_API_KEY", "test-key-not-real")
    monkeypatch.setattr(runner, "OpenAIProvider", _explode)

    with pytest.raises(PaidCallNotConfirmedError, match="--confirm-paid-calls"):
        build_analyzer("openai")


def test_openai_needs_a_key_even_when_confirmed(monkeypatch) -> None:
    monkeypatch.delenv("FITPLATE_AI_PROVIDER_API_KEY", raising=False)
    monkeypatch.setattr(runner, "OpenAIProvider", _explode)

    with pytest.raises(PaidCallNotConfirmedError, match="FITPLATE_AI_PROVIDER_API_KEY"):
        build_analyzer("openai", confirm_paid_calls=True)


def test_cli_exits_2_for_openai_without_confirmation(tmp_path: Path, monkeypatch, capsys) -> None:
    manifest = _manifest_with_images(tmp_path)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(manifest.to_json(), encoding="utf-8")
    monkeypatch.setattr(runner, "OpenAIProvider", _explode)

    code = cli.main(["evaluate", "--provider", "openai", "--manifest", str(manifest_path),
                     "--data-dir", str(tmp_path), "--out-dir", str(tmp_path / "out")])

    assert code == 2
    assert "--confirm-paid-calls" in capsys.readouterr().err
    assert not (tmp_path / "out").exists()


def _explode(*args, **kwargs):
    raise AssertionError("OpenAIProvider must not be constructed")


# --- committed artifacts ----------------------------------------------------------


def test_committed_manifest_is_a_100_dish_subset_with_hashes() -> None:
    manifest = Manifest.from_json(COMMITTED_MANIFEST.read_text(encoding="utf-8"))

    assert len(manifest.dishes) == 100
    assert len({dish.dish_id for dish in manifest.dishes}) == 100
    assert manifest.split_file == SPLIT_FILE
    assert "CC BY 4.0" in manifest.license["name"]
    assert all(dish.rgb_sha256 and len(dish.rgb_sha256) == 64 for dish in manifest.dishes)
    masses = [dish.total_mass_g for dish in manifest.dishes]
    assert masses == sorted(masses)


def test_committed_sample_report_metrics_match_its_predictions() -> None:
    report = json.loads(COMMITTED_SAMPLE.read_text(encoding="utf-8"))
    predictions = [
        DishPrediction(**{**row, "item_confidences": tuple(row["item_confidences"])})
        for row in report["predictions"]
    ]

    assert report["provider"] == "fake"
    assert len(predictions) == 100
    assert compute_metrics(predictions) == report["metrics"]
