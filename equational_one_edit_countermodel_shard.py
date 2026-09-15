from __future__ import annotations

import hashlib
import itertools
import json
import os
import re
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
ALREADY_RETAINED = {"17195_to_43536"}


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
        raise ValueError(f"archive hash mismatch: {digest}")

    rows, final_proofs, _, _, source_hashes, archive_hash = _read_corpus(raw)
    files = _archive_files(raw)
    rows_by_id = {str(row["id"]): row for row in rows}
    current = sorted(set(rows_by_id) - final_proofs - ALREADY_RETAINED)
    assigned = [problem_id for i, problem_id in enumerate(current) if i % shards == shard]

    unique_models = {}
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
        n, table = model
        unique_models.setdefault(
            (n, table),
            {"donor_id": donor_id, "n": n, "table": tuple(table)},
        )
    models = list(unique_models.values())

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

    seed_checks = 0
    seed_assignments = 0
    seed_holds = 0
    mutation_candidates = 0
    target_checks = 0
    target_assignments = 0
    source_rechecks = 0
    source_recheck_assignments = 0
    source_preserving_target_breaks = 0
    seed_order_counts = Counter()
    mutation_order_counts = Counter()
    hits = {}

    for problem_id in assigned:
        source, target = parse_problem(problem_id)
        seeds = []
        for donor in models:
            seed_checks += 1
            source_ok, checked = _identity_holds(
                source,
                donor["table"],
                donor["n"],
            )
            seed_assignments += checked
            if source_ok:
                seed_holds += 1
                seed_order_counts[donor["n"]] += 1
                seeds.append(donor)

        seen_mutations = set()
        found = False
        for donor in seeds:
            n = donor["n"]
            base = donor["table"]
            for index, old in enumerate(base):
                for new in range(n):
                    if new == old:
                        continue
                    mutation_candidates += 1
                    mutated = list(base)
                    mutated[index] = new
                    table = tuple(mutated)
                    key = (n, table)
                    if key in seen_mutations:
                        continue
                    seen_mutations.add(key)
                    mutation_order_counts[n] += 1

                    target_checks += 1
                    witness = _identity_failure(target, table, n)
                    if witness is None:
                        target_assignments += n ** len(target[2])
                        continue
                    target_assignments += witness["assignments_checked"]

                    source_rechecks += 1
                    source_ok, checked = _identity_holds(source, table, n)
                    source_recheck_assignments += checked
                    if not source_ok:
                        continue

                    source_preserving_target_breaks += 1
                    row = index // n
                    col = index % n
                    hits[problem_id] = {
                        "seed_donor_id": donor["donor_id"],
                        "n": n,
                        "mutation": {
                            "index": index,
                            "row": row,
                            "col": col,
                            "old": old,
                            "new": new,
                        },
                        "table": list(table),
                        "target_witness": witness,
                        "source_universally_verified_after_mutation": True,
                        "edit_distance_from_verified_model": 1,
                    }
                    found = True
                    break
                if found:
                    break
            if found:
                break

    result = {
        "experiment": "realitygraph-one-edit-countermodel-repair-v1",
        "shard": shard,
        "shards": shards,
        "assigned": len(assigned),
        "archive_sha256": archive_hash,
        "dataset_sha256": source_hashes,
        "bank": {"unique_literal_models": len(models)},
        "hits": hits,
        "work": {
            "seed_model_checks": seed_checks,
            "seed_assignments_checked": seed_assignments,
            "source_valid_seed_models": seed_holds,
            "mutation_candidates_generated": mutation_candidates,
            "unique_mutations_tested": sum(mutation_order_counts.values()),
            "target_checks": target_checks,
            "target_assignments_checked": target_assignments,
            "source_rechecks_after_target_break": source_rechecks,
            "source_recheck_assignments": source_recheck_assignments,
            "source_preserving_target_breaks": source_preserving_target_breaks,
            "seed_order_counts": dict(sorted(seed_order_counts.items())),
            "mutation_order_counts": dict(sorted(mutation_order_counts.items())),
            "fresh_random_models": 0,
        },
    }
    out = Path(
        os.environ.get(
            "REALITYGRAPH_SHARD_RESULT",
            f"results/one-edit-countermodel-shard-{shard}.json",
        )
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
