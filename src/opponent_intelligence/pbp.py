"""Validate a local nflverse-shaped CSV without silently coercing bad data."""

from collections import Counter
import csv
from dataclasses import dataclass
from hashlib import sha256
from io import StringIO
import math
from pathlib import Path
import re


REQUIRED_COLUMNS = (
    "game_id", "play_id", "season", "season_type", "week", "posteam", "defteam",
    "play_type", "down", "ydstogo", "qb_dropback", "qb_kneel", "qb_spike",
    "two_point_attempt", "epa",
)
OPTIONAL_COLUMNS = ("yardline_100", "score_differential", "qtr", "quarter_seconds_remaining")
MISSING = {"", "NA", "NAN", "NULL"}
KNOWN_PLAY_TYPES = frozenset({
    "run", "pass", "punt", "field_goal", "kickoff", "extra_point",
    "qb_kneel", "qb_spike", "no_play",
})


class DataValidationError(ValueError):
    """A source violates the documented input contract."""


@dataclass(frozen=True)
class Play:
    game_id: str
    play_id: int
    season: int
    season_type: str
    week: int
    offense: str
    defense: str
    down: int
    yards_to_go: int
    dropback: bool
    epa: float | None
    yardline_100: float | None = None
    score_differential: int | None = None
    qtr: int | None = None
    quarter_seconds_remaining: int | None = None


@dataclass(frozen=True)
class Dataset:
    plays: tuple[Play, ...]
    source_sha256: str
    input_rows: int
    exclusions: dict[str, int]
    source_manifest: dict | None = None
    optional_columns: tuple[str, ...] = ()


def _integer(value: str, name: str, minimum: int, maximum: int) -> int:
    try:
        number = float(value)
    except ValueError as exc:
        raise DataValidationError(f"{name}: expected an integer, got {value!r}") from exc
    if not math.isfinite(number) or not number.is_integer():
        raise DataValidationError(f"{name}: expected a finite integer, got {value!r}")
    if not minimum <= number <= maximum:
        raise DataValidationError(f"{name}: expected {minimum}..{maximum}, got {value!r}")
    return int(number)


def _team(value: str, name: str) -> str:
    if not (value.isascii() and value.isalpha() and value.isupper() and 2 <= len(value) <= 3):
        raise DataValidationError(f"{name}: expected an uppercase team abbreviation")
    return value


def _epa(value: str) -> float | None:
    if value.upper() in MISSING:
        return None
    try:
        number = float(value)
    except ValueError as exc:
        raise DataValidationError(f"epa: expected a number or missing value, got {value!r}") from exc
    if not math.isfinite(number):
        raise DataValidationError("epa: infinity is not a valid value")
    return number


def _yardline_100(value: str) -> float | None:
    if value.upper() in MISSING:
        return None
    try:
        number = float(value)
    except ValueError as exc:
        raise DataValidationError(f"yardline_100: expected a number or missing value, got {value!r}") from exc
    if not 0 <= number <= 100:
        raise DataValidationError(f"yardline_100: expected a finite number in 0..100, got {value!r}")
    return number


def _optional_integer(
    value: str, name: str, *, minimum: int | None = None, maximum: int | None = None,
) -> int | None:
    if value.upper() in MISSING:
        return None
    # Accept whole-value decimal notation without rounding through a float.
    if not re.fullmatch(r"[+-]?[0-9]+(?:\.0+)?", value):
        raise DataValidationError(f"{name}: expected a whole integer or missing, got {value!r}")
    try:
        number = int(value.split(".", 1)[0])
    except ValueError as exc:
        raise DataValidationError(f"{name}: integer representation is too long") from exc
    if minimum is not None and number < minimum:
        raise DataValidationError(f"{name}: expected at least {minimum}, got {value!r}")
    if maximum is not None and number > maximum:
        raise DataValidationError(f"{name}: expected at most {maximum}, got {value!r}")
    return number


def load_csv(path: Path) -> Dataset:
    """Keep completed run/pass plays; see docs/METRICS.md for exclusions.

    Hash the same bytes that are parsed. Duplicate play keys fail instead of
    guessing which revision is authoritative. Recognized optional columns are
    validated on eligible rows; other extra upstream columns are ignored.
    """
    return _load_csv_bytes(path.read_bytes())


def _load_csv_bytes(raw: bytes, *, expected_season: int | None = None) -> Dataset:
    """Parse and hash the same decoded CSV bytes, including any UTF-8 BOM."""
    reader = csv.DictReader(StringIO(raw.decode("utf-8-sig")), strict=True)
    columns = reader.fieldnames or []
    if len(columns) != len(set(columns)):
        raise DataValidationError("CSV contains duplicate column names")
    missing = sorted(set(REQUIRED_COLUMNS) - set(columns))
    if missing:
        raise DataValidationError(f"CSV is missing required columns: {', '.join(missing)}")

    seen: set[tuple[str, int]] = set()
    plays: list[Play] = []
    exclusions: Counter[str] = Counter()
    input_rows = 0
    for row in reader:
        input_rows += 1
        try:
            if None in row or any(value is None for value in row.values()):
                raise DataValidationError("row width does not match the CSV header")
            values = {key: value.strip() for key, value in row.items()}
            game_id = values["game_id"]
            if game_id.upper() in MISSING:
                raise DataValidationError("game_id must be present")
            play_id = _integer(values["play_id"], "play_id", 0, 1_000_000)
            key = (game_id, play_id)
            if key in seen:
                raise DataValidationError(f"duplicate play key {key!r}")
            seen.add(key)
            if expected_season is not None:
                season = _integer(values["season"], "season", 1999, 9999)
                if season != expected_season:
                    raise DataValidationError("row season differs from snapshot manifest")
            play_type = values["play_type"]
            # Upstream administrative rows may have no type; audit them separately.
            if play_type.upper() in MISSING:
                exclusions["missing_play_type"] += 1
                continue
            if play_type not in KNOWN_PLAY_TYPES:
                raise DataValidationError(f"play_type: unrecognized value {play_type!r}")
            if play_type not in {"run", "pass"}:
                exclusions["non_run_pass"] += 1
                continue
            if _integer(values["two_point_attempt"], "two_point_attempt", 0, 1):
                exclusions["two_point_attempt"] += 1
                continue
            if _integer(values["qb_kneel"], "qb_kneel", 0, 1):
                exclusions["kneel"] += 1
                continue
            if _integer(values["qb_spike"], "qb_spike", 0, 1):
                exclusions["spike"] += 1
                continue
            season_type = values["season_type"]
            if season_type not in {"REG", "POST"}:
                raise DataValidationError("season_type must be REG or POST")
            offense = _team(values["posteam"], "posteam")
            defense = _team(values["defteam"], "defteam")
            if offense == defense:
                raise DataValidationError("posteam and defteam must differ")
            dropback = bool(_integer(values["qb_dropback"], "qb_dropback", 0, 1))
            if play_type == "pass" and not dropback:
                raise DataValidationError("pass play must have qb_dropback=1")
            plays.append(Play(
                game_id=game_id,
                play_id=play_id,
                season=_integer(values["season"], "season", 1999, 9999),
                season_type=season_type,
                week=_integer(values["week"], "week", 1, 22),
                offense=offense,
                defense=defense,
                down=_integer(values["down"], "down", 1, 4),
                yards_to_go=_integer(values["ydstogo"], "ydstogo", 0, 100),
                dropback=dropback,
                epa=_epa(values["epa"]),
                yardline_100=_yardline_100(values.get("yardline_100", "")),
                score_differential=_optional_integer(values.get("score_differential", ""), "score_differential"),
                qtr=_optional_integer(values.get("qtr", ""), "qtr", minimum=1),
                quarter_seconds_remaining=_optional_integer(
                    values.get("quarter_seconds_remaining", ""), "quarter_seconds_remaining",
                    minimum=0, maximum=900,
                ),
            ))
        except DataValidationError as exc:
            raise DataValidationError(f"CSV line {reader.line_num}: {exc}") from exc

    return Dataset(tuple(plays), sha256(raw).hexdigest(), input_rows, dict(exclusions),
                   optional_columns=tuple(name for name in OPTIONAL_COLUMNS if name in columns))
