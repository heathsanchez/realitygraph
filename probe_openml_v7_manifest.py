from __future__ import annotations

import csv
import hashlib
import io
import json
import urllib.request
from pathlib import Path

import openml

PMLB_SUMMARY = (
    "https://raw.githubusercontent.com/EpistasisLab/pmlb/"
    "7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/pmlb/all_summary_stats.tsv"
)
SUITE = "amlb-classification-all"
SEED = "realitygraph-openml-v7-source-only"
COUNT = 20


def pmlb_names() -> set[str]:
    req = urllib.request.Request(
        PMLB_SUMMARY,
        headers={"User-Agent": "RealityGraph/1.0 source-only manifest"},
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        raw = response.read()
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8")), delimiter="\t")
    return {
        row["dataset"]
        for row in reader
        if row.get("task") == "classification"
        and not row["dataset"].startswith("_deprecated_")
    }


def key(row: dict) -> tuple[bytes, int]:
    body = (
        f"{SEED}|{row['task_id']}|{row['data_id']}|{row['name']}|"
        f"{row['instances']}|{row['features']}|{row['classes']}"
    )
    return hashlib.sha256(body.encode()).digest(), int(row["task_id"])


def pick_column(frame, *names):
    normalized = {
        str(column).lower().replace("_", "").replace(" ", ""): column
        for column in frame.columns
    }
    for name in names:
        token = name.lower().replace("_", "").replace(" ", "")
        if token in normalized:
            return normalized[token]
    raise KeyError(f"missing metadata column {names}; have {list(frame.columns)}")


def main():
    suite = openml.study.get_suite(SUITE)
    if not suite.tasks or not suite.data_ids:
        raise AssertionError("OpenML suite returned no task/data ids")

    task_by_data = {}
    for task_id, data_id in zip(suite.tasks, suite.data_ids):
        task_by_data.setdefault(int(data_id), int(task_id))

    frame = openml.datasets.list_datasets(
        output_format="dataframe",
        status="active",
    )
    did_col = pick_column(frame, "did", "data_id")
    name_col = pick_column(frame, "name")
    n_col = pick_column(frame, "NumberOfInstances")
    f_col = pick_column(frame, "NumberOfFeatures")
    c_col = pick_column(frame, "NumberOfClasses")
    num_col = pick_column(frame, "NumberOfNumericFeatures")

    seen_pmlb = pmlb_names()
    eligible = []
    for _, item in frame.iterrows():
        try:
            did = int(item[did_col])
        except Exception:
            continue
        if did not in task_by_data:
            continue
        name = str(item[name_col])
        if name in seen_pmlb:
            continue
        try:
            n = int(float(item[n_col]))
            f = int(float(item[f_col]))
            c = int(float(item[c_col]))
            numeric = int(float(item[num_col]))
        except Exception:
            continue
        if not (200 <= n <= 50000):
            continue
        if not (2 <= f <= 100):
            continue
        if not (2 <= c <= 10):
            continue
        if numeric < 2:
            continue
        eligible.append(
            {
                "task_id": task_by_data[did],
                "data_id": did,
                "name": name,
                "instances": n,
                "features": f,
                "classes": c,
                "numeric_features": numeric,
            }
        )

    eligible.sort(key=key)
    if len(eligible) < COUNT:
        raise AssertionError(f"only {len(eligible)} source-only eligible OpenML worlds")
    block = eligible[:COUNT]
    digest = hashlib.sha256(
        "\n".join(
            f"{row['task_id']}|{row['data_id']}|{row['name']}|"
            f"{row['instances']}|{row['features']}|{row['classes']}|"
            f"{row['numeric_features']}"
            for row in block
        ).encode()
    ).hexdigest()

    result = {
        "suite": SUITE,
        "suite_id": int(suite.id),
        "suite_task_count": len(suite.tasks),
        "suite_data_count": len(suite.data_ids),
        "pmlb_names_excluded": len(seen_pmlb),
        "eligible_count": len(eligible),
        "selected_count": len(block),
        "seed": SEED,
        "manifest_digest": digest,
        "worlds": block,
        "target_data_downloaded": False,
    }
    Path("openml-v7-manifest.json").write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n"
    )

    print("REALITYGRAPH / OPENML V7 SOURCE-ONLY MANIFEST")
    print("---------------------------------------------")
    print(f"suite={SUITE} suite_id={suite.id}")
    print(f"suite_tasks={len(suite.tasks)} eligible={len(eligible)}")
    print(f"manifest_digest={digest}")
    print("target_data_downloaded=0")
    for i, row in enumerate(block):
        print(
            f"{i:02d} task={row['task_id']} data={row['data_id']} "
            f"{row['name']} n={row['instances']} f={row['features']} "
            f"num={row['numeric_features']} c={row['classes']}"
        )


if __name__ == "__main__":
    main()
