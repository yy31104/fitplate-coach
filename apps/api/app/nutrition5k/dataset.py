"""Nutrition5k subset: metadata parsing, subset selection, and download.

Nutrition5k (Thames et al., CVPR 2021) is released by Google under the
Creative Commons Attribution 4.0 license (CC BY 4.0):
https://github.com/google-research-datasets/Nutrition5k#license--contact

Only the overhead RealSense RGB image (`rgb.png`) and the dish metadata CSVs
are used. Depth images and side-angle videos are never downloaded.
"""

import csv
import hashlib
import io
import json
import re
import urllib.request
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path

BUCKET_URL = "https://storage.googleapis.com/nutrition5k_dataset/nutrition5k_dataset"
METADATA_FILES = ("metadata/dish_metadata_cafe1.csv", "metadata/dish_metadata_cafe2.csv")
# Overhead RGB-D exists only for the depth split; its test half is used here.
SPLIT_FILE = "dish_ids/splits/depth_test_ids.txt"
RGB_IMAGE_NAME = "rgb.png"
DEFAULT_SUBSET_SIZE = 100

LICENSE = {
    "name": "Creative Commons Attribution 4.0 International (CC BY 4.0)",
    "url": "https://creativecommons.org/licenses/by/4.0/",
    "source": "https://github.com/google-research-datasets/Nutrition5k",
    "attribution": (
        "Nutrition5k dataset by Google Research (Thames, Karpur, Norris, Xia, Panait, "
        "Weyand, Sim), CVPR 2021. Images are not stored in this repository; "
        "the manifest lists dish ids and metadata values only."
    ),
    "citation": (
        "Thames, Q., Karpur, A., Norris, W., Xia, F., Panait, L., Weyand, T., Sim, J. "
        "Nutrition5k: Towards Automatic Nutritional Understanding of Generic Food. CVPR 2021."
    ),
}

# Dish ids become path components; anything else is rejected.
_DISH_ID = re.compile(r"^dish_\d{10}$")
_FIELDS_PER_INGREDIENT = 7
_DISH_FIELDS = 6

Fetch = Callable[[str], bytes]


@dataclass(frozen=True)
class DishRecord:
    dish_id: str
    total_calories: float
    total_mass_g: float
    ingredients: tuple[str, ...]


@dataclass
class ManifestDish:
    dish_id: str
    total_calories: float
    total_mass_g: float
    ingredients: list[str]
    rgb_sha256: str | None = None
    rgb_size_bytes: int | None = None


@dataclass
class Manifest:
    dataset: str
    license: dict[str, str]
    split_file: str
    image: str
    selection: str
    dishes: list[ManifestDish] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, ensure_ascii=False) + "\n"

    @classmethod
    def from_json(cls, text: str) -> "Manifest":
        raw = json.loads(text)
        dishes = [ManifestDish(**dish) for dish in raw.pop("dishes")]
        manifest = cls(**raw, dishes=dishes)
        for dish in manifest.dishes:
            validate_dish_id(dish.dish_id)
        return manifest


def validate_dish_id(dish_id: str) -> str:
    if not _DISH_ID.fullmatch(dish_id):
        raise ValueError(f"Not a Nutrition5k dish id: {dish_id!r}")
    return dish_id


def parse_dish_metadata(csv_text: str) -> dict[str, DishRecord]:
    """Parse a dish_metadata_cafe*.csv file.

    Each row: dish_id, total_calories, total_mass, total_fat, total_carb,
    total_protein, then 7 fields per ingredient (id, name, grams, calories,
    fat, carb, protein). The file has no header row.
    """
    records: dict[str, DishRecord] = {}
    for row in csv.reader(io.StringIO(csv_text)):
        if not row:
            continue
        dish_id = row[0].strip()
        if not _DISH_ID.fullmatch(dish_id):
            continue
        ingredient_fields = row[_DISH_FIELDS:]
        names = tuple(
            ingredient_fields[index + 1].strip()
            for index in range(0, len(ingredient_fields) - 1, _FIELDS_PER_INGREDIENT)
        )
        records[dish_id] = DishRecord(
            dish_id=dish_id,
            total_calories=float(row[1]),
            total_mass_g=float(row[2]),
            ingredients=names,
        )
    return records


def parse_dish_ids(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if _DISH_ID.fullmatch(line.strip())]


def select_subset(
    records: dict[str, DishRecord],
    split_ids: Iterable[str],
    size: int = DEFAULT_SUBSET_SIZE,
) -> list[DishRecord]:
    """Pick `size` split dishes spread evenly over total mass.

    Dishes with zero calories or mass are dropped. The rest are sorted by
    (total mass, dish id) and taken at evenly spaced ranks, so the subset
    includes both small and large portions and is the same on every run.
    """
    candidates = sorted(
        (
            records[dish_id]
            for dish_id in set(split_ids)
            if dish_id in records
            and records[dish_id].total_calories > 0
            and records[dish_id].total_mass_g > 0
        ),
        key=lambda record: (record.total_mass_g, record.dish_id),
    )
    if size <= 0 or not candidates:
        return []
    if size >= len(candidates):
        return candidates
    if size == 1:
        return [candidates[len(candidates) // 2]]

    last = len(candidates) - 1
    ranks = sorted({round(index * last / (size - 1)) for index in range(size)})
    return [candidates[rank] for rank in ranks]


def build_manifest(subset: list[DishRecord]) -> Manifest:
    return Manifest(
        dataset="Nutrition5k",
        license=LICENSE,
        split_file=SPLIT_FILE,
        image=f"imagery/realsense_overhead/<dish_id>/{RGB_IMAGE_NAME}",
        selection=(
            "depth_test_ids with total_calories > 0 and total_mass > 0, sorted by "
            "(total_mass, dish_id), taken at evenly spaced ranks"
        ),
        dishes=[
            ManifestDish(
                dish_id=record.dish_id,
                total_calories=round(record.total_calories, 1),
                total_mass_g=round(record.total_mass_g, 1),
                ingredients=list(record.ingredients),
            )
            for record in subset
        ],
    )


def rgb_url(dish_id: str) -> str:
    return f"{BUCKET_URL}/imagery/realsense_overhead/{validate_dish_id(dish_id)}/{RGB_IMAGE_NAME}"


def rgb_path(data_dir: Path, dish_id: str) -> Path:
    return data_dir / validate_dish_id(dish_id) / RGB_IMAGE_NAME


def default_fetch(url: str, timeout_seconds: int = 60) -> bytes:
    if not url.startswith(BUCKET_URL + "/"):
        raise ValueError(f"Refusing to fetch outside the Nutrition5k bucket: {url}")
    with urllib.request.urlopen(url, timeout=timeout_seconds) as response:  # noqa: S310
        return response.read()


def prepare_subset(
    *,
    size: int = DEFAULT_SUBSET_SIZE,
    data_dir: Path,
    fetch: Fetch = default_fetch,
) -> Manifest:
    """Download metadata, select the subset, download its RGB images."""
    records: dict[str, DishRecord] = {}
    for name in METADATA_FILES:
        records.update(parse_dish_metadata(fetch(f"{BUCKET_URL}/{name}").decode("utf-8")))
    split_ids = parse_dish_ids(fetch(f"{BUCKET_URL}/{SPLIT_FILE}").decode("utf-8"))

    manifest = build_manifest(select_subset(records, split_ids, size))
    download_images(manifest, data_dir=data_dir, fetch=fetch, record_hashes=True)
    return manifest


def download_images(
    manifest: Manifest,
    *,
    data_dir: Path,
    fetch: Fetch = default_fetch,
    record_hashes: bool = False,
) -> list[str]:
    """Download each dish's rgb.png. Verify hashes the manifest already has.

    Returns the dish ids that were fetched (existing, verified files are kept).
    """
    fetched: list[str] = []
    for dish in manifest.dishes:
        path = rgb_path(data_dir, dish.dish_id)
        if path.exists() and dish.rgb_sha256 and _sha256(path.read_bytes()) == dish.rgb_sha256:
            continue

        data = fetch(rgb_url(dish.dish_id))
        digest = _sha256(data)
        if dish.rgb_sha256 and not record_hashes and digest != dish.rgb_sha256:
            raise ValueError(
                f"{dish.dish_id}: rgb.png sha256 {digest} does not match manifest {dish.rgb_sha256}"
            )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        if record_hashes:
            dish.rgb_sha256 = digest
            dish.rgb_size_bytes = len(data)
        fetched.append(dish.dish_id)
    return fetched


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
