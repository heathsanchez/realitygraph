from __future__ import annotations

import csv
import hashlib
import io
import time
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GroupedBinaryDataset:
    name: str
    doi: str
    license: str
    probe_names: tuple[str, ...]
    values: tuple[tuple[float, ...], ...]
    labels: tuple[int, ...]
    groups: tuple[str, ...]
    source_hashes: tuple[tuple[str, str], ...]

    @property
    def group_count(self) -> int:
        return len(set(self.groups))


PARKINSONS_URL = (
    "https://archive.ics.uci.edu/ml/machine-learning-databases/"
    "parkinsons/parkinsons.data"
)
OCCUPANCY_URL = (
    "https://archive.ics.uci.edu/ml/machine-learning-databases/"
    "00357/occupancy_data.zip"
)
OCCUPANCY_MEMBERS = ("datatraining.txt", "datatest.txt", "datatest2.txt")

# Filled from a frozen CI acquisition run, then enforced on every later run.
PARKINSONS_SHA256 = ""
OCCUPANCY_SHA256 = ""


def _download(url: str, attempts: int = 4, timeout: int = 30) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "RealityGraph/1.0 grouped-data verifier"},
    )
    last: Exception | None = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except (TimeoutError, OSError, urllib.error.URLError) as exc:
            last = exc
            if attempt + 1 < attempts:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"download failed: {url}") from last


def _cached_bytes(
    url: str,
    cache_dir: Path,
    expected_sha256: str,
) -> tuple[bytes, str]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    name = hashlib.sha256(url.encode()).hexdigest()[:20] + ".data"
    path = cache_dir / name
    raw = path.read_bytes() if path.exists() else _download(url)
    digest = hashlib.sha256(raw).hexdigest()
    if expected_sha256 and digest != expected_sha256:
        raise ValueError(
            f"source changed: {url}: expected {expected_sha256}, got {digest}"
        )
    if not path.exists():
        path.write_bytes(raw)
    return raw, digest


def _parkinsons_rows(raw: bytes):
    text = raw.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise ValueError("Parkinsons source has no header")
    probe_names = tuple(
        name for name in reader.fieldnames if name not in {"name", "status"}
    )
    for row in reader:
        recording = row["name"]
        subject = recording.rsplit("_", 1)[0]
        yield (
            probe_names,
            tuple(float(row[name]) for name in probe_names),
            int(row["status"]),
            subject,
        )


def fetch_parkinsons_grouped(
    cache_dir: str | Path = ".cache/grouped-real",
) -> GroupedBinaryDataset:
    raw, digest = _cached_bytes(
        PARKINSONS_URL,
        Path(cache_dir),
        PARKINSONS_SHA256,
    )
    values = []
    labels = []
    groups = []
    probe_names: tuple[str, ...] = ()
    for probe_names, value, label, group in _parkinsons_rows(raw):
        values.append(value)
        labels.append(label)
        groups.append(group)

    if not values:
        raise ValueError("Parkinsons source parsed no rows")
    if len(set(groups)) < 20:
        raise ValueError("Parkinsons subject grouping collapsed unexpectedly")
    return GroupedBinaryDataset(
        "Parkinsons voice / subject-separated",
        "10.24432/C59C74",
        "CC BY 4.0",
        probe_names,
        tuple(values),
        tuple(labels),
        tuple(groups),
        ((PARKINSONS_URL, digest),),
    )


def _occupancy_rows(raw: bytes):
    text = raw.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    header = next(reader)
    header = [cell.strip().strip('"') for cell in header]
    # UCI files include an unnamed row-index column.
    if header and header[0] == "":
        header[0] = "__rowid__"
    index = {name: i for i, name in enumerate(header)}
    required = {
        "date",
        "Temperature",
        "Humidity",
        "Light",
        "CO2",
        "HumidityRatio",
        "Occupancy",
    }
    if not required.issubset(index):
        raise ValueError(f"unexpected occupancy header: {header}")

    probes = (
        "Temperature",
        "Humidity",
        "Light",
        "CO2",
        "HumidityRatio",
    )
    for row in reader:
        if not row:
            continue
        offset = len(row) - len(header)
        if offset not in {0, 1}:
            raise ValueError(
                f"unexpected occupancy row width: header={len(header)} row={len(row)}"
            )
        date = row[index["date"] + offset].strip().strip('"')
        day = date[:10]
        yield (
            tuple(float(row[index[name] + offset]) for name in probes),
            int(float(row[index["Occupancy"] + offset])),
            day,
        )


def fetch_occupancy_grouped(
    cache_dir: str | Path = ".cache/grouped-real",
) -> GroupedBinaryDataset:
    cache = Path(cache_dir)
    raw_zip, digest = _cached_bytes(
        OCCUPANCY_URL,
        cache,
        OCCUPANCY_SHA256,
    )
    values = []
    labels = []
    groups = []

    with zipfile.ZipFile(io.BytesIO(raw_zip)) as archive:
        names = set(archive.namelist())
        missing = [name for name in OCCUPANCY_MEMBERS if name not in names]
        if missing:
            raise ValueError(f"Occupancy archive missing members: {missing}")
        for name in OCCUPANCY_MEMBERS:
            for value, label, day in _occupancy_rows(archive.read(name)):
                values.append(value)
                labels.append(label)
                groups.append(day)

    if len(values) < 20_000:
        raise ValueError("Occupancy source parsed too few rows")
    if len(set(groups)) < 10:
        raise ValueError("Occupancy day grouping collapsed unexpectedly")

    return GroupedBinaryDataset(
        "Occupancy sensors / day-separated",
        "10.24432/C5X01N",
        "CC BY 4.0",
        ("Temperature", "Humidity", "Light", "CO2", "HumidityRatio"),
        tuple(values),
        tuple(labels),
        tuple(groups),
        ((OCCUPANCY_URL, digest),),
    )

def grouped_real_datasets(
    cache_dir: str | Path = ".cache/grouped-real",
) -> tuple[GroupedBinaryDataset, ...]:
    return (
        fetch_parkinsons_grouped(cache_dir),
        fetch_occupancy_grouped(cache_dir),
    )
