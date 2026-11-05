from pathlib import Path
from typing import Literal

from pydantic import BaseModel


class PromptRecord(BaseModel):
    name: str
    version: str
    schema_version: str
    created_at: str
    status: Literal["active", "deprecated"]
    body: str


_PROMPTS_ROOT = Path(__file__).resolve().parents[2] / "prompts"


def _load_prompt(
    name: str,
    version: str,
    *,
    created_at: str,
    status: Literal["active", "deprecated"],
) -> PromptRecord:
    body_path = _PROMPTS_ROOT / name / f"{version}.txt"
    if not body_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {body_path}")

    return PromptRecord(
        name=name,
        version=version,
        schema_version="food_analysis.v1",
        created_at=created_at,
        status=status,
        body=body_path.read_text(encoding="utf-8").strip(),
    )


PROMPT_REGISTRY: dict[str, dict[str, PromptRecord]] = {
    "food_analysis": {
        # v1 is kept for log replay; it told the model it was a "future" model
        # that the live route does not call, which was no longer true.
        "v1": _load_prompt("food_analysis", "v1", created_at="2026-05-18", status="deprecated"),
        "v2": _load_prompt("food_analysis", "v2", created_at="2026-11-05", status="active"),
    },
}

ACTIVE_FOOD_ANALYSIS_PROMPT_VERSION = "v2"


def get_prompt(name: str, version: str) -> PromptRecord:
    by_name = PROMPT_REGISTRY.get(name)
    if by_name is None:
        raise KeyError(f"No prompts registered for name {name!r}")

    record = by_name.get(version)
    if record is None:
        raise KeyError(f"Prompt {name!r} has no version {version!r}")

    return record
