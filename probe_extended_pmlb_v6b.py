from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path

from pmlb_meta_world import CORPUS_SEED, SUMMARY_URL, _download, _hash


def extended_manifest(summary_raw: bytes) -> list[dict]:
    reader = csv.DictReader(io.StringIO(summary_raw.decode("utf-8")), delimiter="\t")
    primary, extension, wide = [], [], []

    for row in reader:
        if row.get("task") != "classification":
            continue
        name = row["dataset"]
        if name.startswith("_deprecated_"):
            continue
        try:
            n = int(float(row["n_instances"]))
            f = int(float(row["n_features"]))
            c = int(float(row["n_classes"]))
        except (TypeError, ValueError):
            continue

        meta = {
            "dataset": name,
            "n_instances": n,
            "n_features": f,
            "n_classes": c,
        }
        if 80 <= n <= 20000 and 2 <= f <= 180 and 2 <= c <= 26:
            primary.append(meta)
        elif 40 <= n <= 100000 and 2 <= f <= 1000 and 2 <= c <= 100:
            extension.append(meta)
        elif 40 <= n <= 500000 and 2 <= f <= 5000 and 2 <= c <= 1000:
            wide.append(meta)

    def order_key(row):
        return (_hash(CORPUS_SEED, row["dataset"]), row["dataset"])

    primary.sort(key=order_key)
    extension.sort(key=order_key)
    wide.sort(key=order_key)
    eligible = primary + extension + wide

    if len(primary) != 126:
        raise AssertionError(f"primary corpus drifted: {len(primary)}")
    if len(primary) + len(extension) != 141:
        raise AssertionError(
            f"original extended corpus drifted: {len(primary)+len(extension)}"
        )
    if len(eligible) < 160:
        raise AssertionError(f"wide eligibility produced only {len(eligible)} datasets")
    return eligible


def main():
    raw = _download(SUMMARY_URL)
    summary_sha = hashlib.sha256(raw).hexdigest()
    manifest = extended_manifest(raw)
    block = manifest[140:160]
    digest = hashlib.sha256(
        "\n".join(
            f"{140+i}|{row['dataset']}|{row['n_instances']}|"
            f"{row['n_features']}|{row['n_classes']}"
            for i, row in enumerate(block)
        ).encode()
    ).hexdigest()

    result = {
        "summary_url": SUMMARY_URL,
        "summary_sha256": summary_sha,
        "eligible_count": len(manifest),
        "original_eligible_count": 141,
        "block_start": 140,
        "block_stop": 160,
        "block_digest": digest,
        "datasets": [
            {"index": 140 + i, **row}
            for i, row in enumerate(block)
        ],
        "target_data_downloaded": False,
    }
    Path("pmlb-v6-manifest.json").write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n"
    )

    print("REALITYGRAPH / V6 SOURCE-ONLY WIDE MANIFEST")
    print("-------------------------------------------")
    print(f"summary_sha256={summary_sha}")
    print(f"eligible_count={len(manifest)}")
    print(f"block_digest={digest}")
    print("target_data_downloaded=0")
    for row in result["datasets"]:
        print(
            f"{row['index']:03d} {row['dataset']} "
            f"n={row['n_instances']} f={row['n_features']} c={row['n_classes']}"
        )


if __name__ == "__main__":
    main()
