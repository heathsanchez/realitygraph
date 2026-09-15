from __future__ import annotations

from pathlib import Path

from realitygraph.empirical import fetch_dataset
from realitygraph.empirical_sources import uci_sources


def main():
    cache = Path(".cache/real-datasets")
    cache.mkdir(parents=True, exist_ok=True)

    print("REALITYGRAPH / PINNED DATASET ACQUISITION")
    print("----------------------------------------")
    for source in uci_sources():
        dataset = fetch_dataset(source, cache)
        print(
            f"{source.name}: rows={len(dataset.features)} "
            f"sha256={dataset.source_sha256}"
        )
    print("PINNED_DATASETS_VERIFIED")


if __name__ == "__main__":
    main()
