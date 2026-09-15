from __future__ import annotations

import hashlib
import json
import os
from collections import Counter
from pathlib import Path

from equational_countermodel_bank import (
    _archive_files,
    _extract_literal_model,
    _identity_failure,
    _identity_holds,
    _parse_identity,
    _verdict,
)
from equational_residual_demo import _read_corpus

PINNED_ARCHIVE_SHA256 = "284b45196a9e8a31f1bd3aeb05040c451a615fed2ca8ba724d7a14a833e842eb"
KNOWN_RETAINED = {"17195_to_43536"}


def main() -> None:
    shard = int(os.environ["REALITYGRAPH_SHARD"])
    shards = int(os.environ["REALITYGRAPH_SHARDS"])
    archive_path = Path(
        os.environ.get(
            "REALITYGRAPH_EQUATIONAL_ARCHIVE",
            ".cache/equational/equational-challenges.tar.gz",
        )
    )
    raw = archive_path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != PINNED_ARCHIVE_SHA256:
        raise ValueError(
            f"archive hash mismatch: expected {PINNED_ARCHIVE_SHA256}, got {digest}"
        )

    rows, final_proofs, _, _, source_hashes, archive_hash = _read_corpus(raw)
    files = _archive_files(raw)
    rows_by_id = {str(row["id"]): row for row in rows}
    current = sorted(set(rows_by_id) - final_proofs)
    assigned = [problem_id for i, problem_id in enumerate(current) if i % shards == shard]

    unique = {}
    certificate_count = 0
    for donor_id in sorted(final_proofs):
        proof = files.get(f"proofs/{donor_id}.lean")
        if proof is None:
            continue
        text = proof.decode("utf-8", errors="replace")
        if _verdict(text) != "false":
            continue
        model = _extract_literal_model(text)
        if model is None:
            continue
        certificate_count += 1
        n, table = model
        unique.setdefault(
            (n, table),
            {
                "donor_id": donor_id,
                "n": n,
                "table": table,
            },
        )
    models = list(unique.values())

    parsed = {}
    def parse_problem(problem_id: str):
        item = parsed.get(problem_id)
        if item is None:
            row = rows_by_id[problem_id]
            item = (
                _parse_identity(row["equation1"]),
                _parse_identity(row["equation2"]),
            )
            parsed[problem_id] = item
        return item

    source_cache = {}
    hits = {}
    tests = 0
    source_checks = 0
    source_assignments = 0
    premise_holding = 0
    target_assignments = 0
    order_tests = Counter()
    order_holds = Counter()

    for problem_id in assigned:
        row = rows_by_id[problem_id]
        source, target = parse_problem(problem_id)
        source_key_prefix = int(row["eq1_id"])
        for donor in models:
            tests += 1
            order_tests[donor["n"]] += 1
            key = (source_key_prefix, donor["n"], donor["table"])
            source_ok = source_cache.get(key)
            if source_ok is None:
                source_ok, checked = _identity_holds(
                    source,
                    donor["table"],
                    donor["n"],
                )
                source_cache[key] = source_ok
                source_checks += 1
                source_assignments += checked
            if not source_ok:
                continue
            premise_holding += 1
            order_holds[donor["n"]] += 1
            witness = _identity_failure(
                target,
                donor["table"],
                donor["n"],
            )
            if witness is None:
                target_assignments += donor["n"] ** len(target[2])
                continue
            target_assignments += witness["assignments_checked"]
            hits[problem_id] = {
                "donor_id": donor["donor_id"],
                "n": donor["n"],
                "table": list(donor["table"]),
                "target_witness": witness,
                "source_universally_verified": True,
                "already_retained": problem_id in KNOWN_RETAINED,
            }
            break

    result = {
        "experiment": "realitygraph-exhaustive-countermodel-replay-v1",
        "shard": shard,
        "shards": shards,
        "archive_sha256": archive_hash,
        "dataset_sha256": source_hashes,
        "bank": {
            "literal_model_certificates": certificate_count,
            "unique_literal_models": len(models),
        },
        "assigned": len(assigned),
        "hits": hits,
        "work": {
            "candidate_model_transfers_tested": tests,
            "unique_source_model_checks": source_checks,
            "source_assignments_checked": source_assignments,
            "premise_holding_transfers": premise_holding,
            "target_assignments_checked": target_assignments,
            "order_tests": dict(sorted(order_tests.items())),
            "order_premise_holds": dict(sorted(order_holds.items())),
            "new_model_search": 0,
        },
    }
    out = Path(
        os.environ.get(
            "REALITYGRAPH_SHARD_RESULT",
            f"results/exhaustive-countermodel-shard-{shard}.json",
        )
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
