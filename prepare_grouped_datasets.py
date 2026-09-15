from pathlib import Path

from realitygraph.grouped_empirical import grouped_real_datasets


def main():
    cache = Path(".cache/grouped-real")
    print("REALITYGRAPH / GROUPED DATASET ACQUISITION")
    print("-----------------------------------------")
    for dataset in grouped_real_datasets(cache):
        print(
            f"{dataset.name}: rows={len(dataset.values)} "
            f"groups={dataset.group_count} probes={len(dataset.probe_names)}"
        )
        for url, digest in dataset.source_hashes:
            print(f"  sha256={digest} url={url}")
    print("GROUPED_DATASETS_VERIFIED")


if __name__ == "__main__":
    main()
