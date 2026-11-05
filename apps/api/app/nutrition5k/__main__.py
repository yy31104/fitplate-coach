"""Nutrition5k evaluation CLI.

    python -m app.nutrition5k prepare  [--size 100]      # metadata + subset + images, writes manifest
    python -m app.nutrition5k download                    # images for the committed manifest
    python -m app.nutrition5k evaluate --provider fake    # no network, no cost
    python -m app.nutrition5k evaluate --provider openai --confirm-paid-calls   # paid; needs a key
"""

import argparse
import sys
from pathlib import Path

from app.nutrition5k.dataset import (
    DEFAULT_SUBSET_SIZE,
    Manifest,
    download_images,
    prepare_subset,
)
from app.nutrition5k.runner import (
    DEFAULT_MAX_COST_USD,
    DEFAULT_OPENAI_MODEL,
    PROVIDERS,
    PaidCallNotConfirmedError,
    build_analyzer,
    build_report,
    run_subset,
    write_report,
)

API_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = API_ROOT.parents[1]
EVAL_ROOT = API_ROOT / "evaluation" / "nutrition5k"
DEFAULT_MANIFEST = EVAL_ROOT / "subset_manifest.json"
DEFAULT_DATA_DIR = EVAL_ROOT / "data"
DEFAULT_RUNS_DIR = EVAL_ROOT / "runs"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.nutrition5k", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare", help="Download metadata, select a subset, download images.")
    prepare.add_argument("--size", type=int, default=DEFAULT_SUBSET_SIZE)
    prepare.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    prepare.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)

    download = sub.add_parser("download", help="Download the images listed in the manifest.")
    download.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    download.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)

    evaluate = sub.add_parser("evaluate", help="Run an analyzer on the subset and write a report.")
    evaluate.add_argument("--provider", choices=PROVIDERS, default="fake")
    evaluate.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    evaluate.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    evaluate.add_argument("--out-dir", type=Path, default=None,
                          help="Default: evaluation/nutrition5k/runs/<provider>")
    evaluate.add_argument("--limit", type=int, default=None, help="Only the first N dishes.")
    evaluate.add_argument("--model", default=DEFAULT_OPENAI_MODEL, help="OpenAI model id.")
    evaluate.add_argument("--confirm-paid-calls", action="store_true",
                          help="Required for --provider openai. Each dish is one paid request.")
    evaluate.add_argument("--max-cost-usd", type=float, default=DEFAULT_MAX_COST_USD,
                          help="Stop starting new requests once this much has been spent.")

    args = parser.parse_args(argv)

    if args.command == "prepare":
        manifest = prepare_subset(size=args.size, data_dir=args.data_dir)
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(manifest.to_json(), encoding="utf-8")
        print(f"Selected {len(manifest.dishes)} dishes; wrote {_rel(args.manifest)}")
        return 0

    manifest = Manifest.from_json(args.manifest.read_text(encoding="utf-8"))

    if args.command == "download":
        fetched = download_images(manifest, data_dir=args.data_dir)
        print(f"Downloaded {len(fetched)} images ({len(manifest.dishes) - len(fetched)} already present)")
        return 0

    try:
        analyzer = build_analyzer(args.provider, confirm_paid_calls=args.confirm_paid_calls,
                                  model=args.model)
    except PaidCallNotConfirmedError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    def progress(index: int, total: int, prediction) -> None:
        status = prediction.error or f"{prediction.predicted_point} kcal (true {prediction.true_calories:.0f})"
        print(f"[{index}/{total}] {prediction.dish_id}: {status}", file=sys.stderr)

    predictions, usage = run_subset(
        manifest,
        data_dir=args.data_dir,
        analyzer=analyzer,
        limit=args.limit,
        max_cost_usd=args.max_cost_usd if args.provider == "openai" else None,
        on_progress=progress,
    )
    report = build_report(manifest=manifest, provider=args.provider, model=analyzer.model,
                          prompt_version=getattr(analyzer, "prompt_version", None),
                          predictions=predictions, usage=usage)
    out_dir = args.out_dir or DEFAULT_RUNS_DIR / args.provider
    json_path, markdown_path = write_report(report, out_dir)
    metrics = report["metrics"]
    print(f"{metrics['scored']}/{metrics['dishes']} scored; MAE% {metrics['calories']['mae_pct']}; "
          f"wrote {_rel(markdown_path)} and {_rel(json_path)}")
    return 0


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


if __name__ == "__main__":
    raise SystemExit(main())
