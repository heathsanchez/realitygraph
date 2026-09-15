from __future__ import annotations

import hashlib
import itertools
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
ALREADY_RETAINED = {"17195_to_43536"}


def _eval_trace(node, env, table, n):
    if node[0] == "v":
        return env[node[1]], ()
    left, left_trace = _eval_trace(node[1], env, table, n)
    right, right_trace = _eval_trace(node[2], env, table, n)
    index = left * n + right
    value = table[index]
    return value, left_trace + right_trace + (index,)


def _first_failure_trace(parsed, table, n):
    lhs, rhs, variables = parsed
    for values in itertools.product(range(n), repeat=len(variables)):
        env = dict(zip(variables, values))
        lv, ltrace = _eval_trace(lhs, env, table, n)
        rv, rtrace = _eval_trace(rhs, env, table, n)
        if lv != rv:
            return {
                "assignment": env,
                "lhs": lv,
                "rhs": rv,
                "trace_cells": tuple(dict.fromkeys(ltrace + rtrace)),
            }
    return None


def _holds_at(parsed, table, n, assignment):
    lhs, rhs, _ = parsed
    lv, _ = _eval_trace(lhs, assignment, table, n)
    rv, _ = _eval_trace(rhs, assignment, table, n)
    return lv == rv


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

    parsed_cache = {}
    def parsed(problem_id):
        item = parsed_cache.get(problem_id)
        if item is None:
            row = rows_by_id[problem_id]
            item = (
                _parse_identity(row["equation1"]),
                _parse_identity(row["equation2"]),
            )
            parsed_cache[problem_id] = item
        return item

    work = Counter()
    seed_orders = Counter()
    first_break_orders = Counter()
    second_candidate_orders = Counter()
    hits = {}

    for problem_id in assigned:
        source, target = parsed(problem_id)
        seeds = []
        for donor in models:
            work["seed_model_checks"] += 1
            source_ok, checked = _identity_holds(source, donor["table"], donor["n"])
            work["seed_assignments_checked"] += checked
            if source_ok:
                work["source_valid_seed_models"] += 1
                seed_orders[donor["n"]] += 1
                seeds.append(donor)

        seen_second_models = set()
        found = False
        for donor in seeds:
            n = donor["n"]
            base = donor["table"]
            for first_index, first_old in enumerate(base):
                for first_new in range(n):
                    if first_new == first_old:
                        continue
                    work["first_edit_candidates"] += 1
                    table1 = list(base)
                    table1[first_index] = first_new
                    table1 = tuple(table1)

                    work["first_target_checks"] += 1
                    target_witness1 = _identity_failure(target, table1, n)
                    if target_witness1 is None:
                        work["first_target_assignments"] += n ** len(target[2])
                        continue
                    work["first_target_assignments"] += target_witness1["assignments_checked"]
                    work["target_breaking_first_edits"] += 1
                    first_break_orders[n] += 1

                    source_failure = _first_failure_trace(source, table1, n)
                    if source_failure is None:
                        # V1 proved this does not occur, but retain the invariant.
                        work["unexpected_one_edit_hits"] += 1
                        continue
                    work["source_failures_traced"] += 1
                    causal_cells = source_failure["trace_cells"]
                    work["causal_cells_total"] += len(causal_cells)

                    for second_index in causal_cells:
                        if second_index == first_index:
                            continue
                        second_old = table1[second_index]
                        for second_new in range(n):
                            if second_new == second_old:
                                continue
                            work["second_edit_candidates"] += 1
                            table2 = list(table1)
                            table2[second_index] = second_new
                            table2 = tuple(table2)
                            key = (n, table2)
                            if key in seen_second_models:
                                continue
                            seen_second_models.add(key)
                            second_candidate_orders[n] += 1
                            work["unique_second_models"] += 1

                            # The second edit was chosen from the first source
                            # witness. It must repair that exact consequence before
                            # earning a full universal replay.
                            if not _holds_at(
                                source,
                                table2,
                                n,
                                source_failure["assignment"],
                            ):
                                work["rejected_by_local_source_witness"] += 1
                                continue
                            work["local_source_witness_repairs"] += 1

                            source_ok, checked = _identity_holds(source, table2, n)
                            work["full_source_rechecks"] += 1
                            work["full_source_assignments"] += checked
                            if not source_ok:
                                continue
                            work["source_preserving_two_edits"] += 1

                            target_witness2 = _identity_failure(target, table2, n)
                            work["final_target_checks"] += 1
                            if target_witness2 is None:
                                work["final_target_assignments"] += n ** len(target[2])
                                continue
                            work["final_target_assignments"] += target_witness2[
                                "assignments_checked"
                            ]

                            hits[problem_id] = {
                                "seed_donor_id": donor["donor_id"],
                                "n": n,
                                "first_edit": {
                                    "index": first_index,
                                    "row": first_index // n,
                                    "col": first_index % n,
                                    "old": first_old,
                                    "new": first_new,
                                },
                                "second_edit": {
                                    "index": second_index,
                                    "row": second_index // n,
                                    "col": second_index % n,
                                    "old": second_old,
                                    "new": second_new,
                                },
                                "table": list(table2),
                                "target_witness": target_witness2,
                                "source_universally_verified": True,
                                "edit_distance_from_verified_model": 2,
                                "repair_was_localized_by_source_counterexample": True,
                            }
                            found = True
                            break
                        if found:
                            break
                    if found:
                        break
                if found:
                    break
            if found:
                break

    result = {
        "experiment": "realitygraph-causal-two-edit-countermodel-repair-v1",
        "shard": shard,
        "shards": shards,
        "assigned": len(assigned),
        "archive_sha256": archive_hash,
        "dataset_sha256": source_hashes,
        "bank": {"unique_literal_models": len(models)},
        "hits": hits,
        "work": {
            **dict(work),
            "seed_order_counts": dict(sorted(seed_orders.items())),
            "first_target_break_order_counts": dict(sorted(first_break_orders.items())),
            "second_candidate_order_counts": dict(sorted(second_candidate_orders.items())),
            "fresh_random_models": 0,
        },
    }
    out = Path(
        os.environ.get(
            "REALITYGRAPH_SHARD_RESULT",
            f"results/causal-two-edit-shard-{shard}.json",
        )
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
