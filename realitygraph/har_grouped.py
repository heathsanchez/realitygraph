from __future__ import annotations

import hashlib
import io
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from .grouped_empirical import GroupedBinaryDataset


HAR_URL = (
    "https://archive.ics.uci.edu/static/public/240/"
    "human+activity+recognition+using+smartphones.zip"
)
HAR_DOI = "10.24432/C54S4K"
HAR_LICENSE = "CC BY 4.0"
HAR_SHA256 = "c00b803081a5c797cd5e4b83700a9810b38d53d9d84e01917e090e1fdbc81031"
HAR_FEATURE_INDICES = tuple(range(8))


def _download(url: str, attempts: int = 4, timeout: int = 90) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "RealityGraph/1.0 HAR grouped-data verifier"},
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
    cache_dir: Path,
    expected_sha256: str = HAR_SHA256,
) -> tuple[bytes, str]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / "uci-har-smartphones.zip"
    raw = path.read_bytes() if path.exists() else _download(HAR_URL)
    digest = hashlib.sha256(raw).hexdigest()
    if expected_sha256 and digest != expected_sha256:
        raise ValueError(
            f"HAR source changed: expected {expected_sha256}, got {digest}"
        )
    if not path.exists():
        path.write_bytes(raw)
    return raw, digest


def source_digest(
    cache_dir: str | Path = ".cache/grouped-real",
) -> tuple[int, str]:
    raw, digest = _cached_bytes(Path(cache_dir), expected_sha256="")
    return len(raw), digest


def _read_lines(archive: zipfile.ZipFile, path: str) -> list[str]:
    return archive.read(path).decode("utf-8").strip().splitlines()


def fetch_har_grouped(
    cache_dir: str | Path = ".cache/grouped-real",
) -> GroupedBinaryDataset:
    raw, digest = _cached_bytes(Path(cache_dir))
    if not HAR_SHA256:
        raise ValueError(
            "HAR source is not pinned; run source-only hash acquisition first"
        )

    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        feature_lines = _read_lines(archive, "UCI HAR Dataset/features.txt")
        all_names = tuple(line.split(maxsplit=1)[1] for line in feature_lines)
        probe_names = tuple(all_names[i] for i in HAR_FEATURE_INDICES)

        values: list[tuple[float, ...]] = []
        labels: list[int] = []
        groups: list[str] = []

        for split in ("train", "test"):
            x_lines = _read_lines(
                archive,
                f"UCI HAR Dataset/{split}/X_{split}.txt",
            )
            y_lines = _read_lines(
                archive,
                f"UCI HAR Dataset/{split}/y_{split}.txt",
            )
            subject_lines = _read_lines(
                archive,
                f"UCI HAR Dataset/{split}/subject_{split}.txt",
            )
            if not (len(x_lines) == len(y_lines) == len(subject_lines)):
                raise ValueError(f"HAR {split} row counts disagree")

            for x_line, y_line, subject_line in zip(
                x_lines,
                y_lines,
                subject_lines,
            ):
                columns = x_line.split()
                values.append(
                    tuple(float(columns[i]) for i in HAR_FEATURE_INDICES)
                )
                activity = int(y_line)
                labels.append(1 if activity in {1, 2, 3} else 0)
                groups.append(f"subject-{int(subject_line):02d}")

    if len(values) != 10299:
        raise ValueError(f"unexpected HAR row count: {len(values)}")
    if len(set(groups)) != 30:
        raise ValueError(f"unexpected HAR subject count: {len(set(groups))}")
    if len(set(labels)) != 2:
        raise ValueError("HAR binary target collapsed")

    return GroupedBinaryDataset(
        "UCI HAR smartphones / subject-separated",
        HAR_DOI,
        HAR_LICENSE,
        probe_names,
        tuple(values),
        tuple(labels),
        tuple(groups),
        ((HAR_URL, digest),),
    )
