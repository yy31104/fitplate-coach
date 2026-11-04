from pathlib import Path

from app.observability.metrics import (
    ModelRunMetrics,
    load_model_runs,
    render_json,
    render_markdown,
    summarize_model_runs,
)

API_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = API_ROOT.parents[1]
SAMPLE_PATH = API_ROOT / "observability_samples" / "model_runs.sample.jsonl"
DEFAULT_MARKDOWN_REPORT_PATH = REPO_ROOT / "devlog" / "evidence" / "metrics" / "METRICS_REPORT.md"
DEFAULT_JSON_REPORT_PATH = REPO_ROOT / "devlog" / "evidence" / "metrics" / "metrics_report.json"


def main() -> None:
    metrics = generate_metrics_reports()
    print(
        f"{metrics.schema_version}: {metrics.total_runs} runs, "
        f"{metrics.error_count} errors, ${metrics.total_cost_usd:.6f} total cost"
    )
    print(f"Wrote {DEFAULT_MARKDOWN_REPORT_PATH.relative_to(REPO_ROOT)}")
    print(f"Wrote {DEFAULT_JSON_REPORT_PATH.relative_to(REPO_ROOT)}")


def generate_metrics_reports(
    *,
    sample_path: Path = SAMPLE_PATH,
    markdown_report_path: Path = DEFAULT_MARKDOWN_REPORT_PATH,
    json_report_path: Path = DEFAULT_JSON_REPORT_PATH,
) -> ModelRunMetrics:
    records = load_model_runs(sample_path.read_text(encoding="utf-8"))
    metrics = summarize_model_runs(records)

    markdown_report_path.parent.mkdir(parents=True, exist_ok=True)
    json_report_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_report_path.write_text(render_markdown(metrics), encoding="utf-8")
    json_report_path.write_text(render_json(metrics), encoding="utf-8")

    return metrics


if __name__ == "__main__":
    main()
