from __future__ import annotations

import itertools
import json
from collections import Counter, defaultdict
from pathlib import Path

from equational_concrete_table_bank import (
    COMMIT,
    _download,
    _verdict,
    _parse_identity,
    _extract_tables,
    _eval,
)
from equational_residual_demo import _read_corpus
from equational_transition_demo import _archive_files
from equational_internal_lemma_bank import _specializes

RETAINED = {
    "17195_to_43536",
    "4922_to_4158",
    "4922_to_4258",
    "22268_to_22436",
    "22505_to_40367",
}
PENDING_KERNEL = {
    "12820_to_2841",
    "12820_to_40755",
    "33419_to_323",
    "33419_to_3392",
    "33419_to_3412",
    "33419_to_3587",
    "33419_to_3746",
    "33419_to_4064",
    "33419_to_41819",
    "33419_to_4291",
    "33419_to_4802",
    "33419_to_55538",
}
MAX_EXHAUSTIVE_ASSIGNMENTS = 750_000


def _exhaustive_witness(identity, n, table):
    lhs, rhs, variables = identity
    total = n ** len(variables)
    if total > MAX_EXHAUSTIVE_ASSIGNMENTS:
        return None, "skipped_large", total

    checked = 0
    for assignment in itertools.product(range(n), repeat=len(variables)):
        checked += 1
        env = dict(zip(variables, assignment))
        lv = _eval(lhs, env, n, table)
        rv = _eval(rhs, env, n, table)
        if lv != rv:
            return {
                "assignment": env,
                "lhs": lv,
                "rhs": rv,
                "checked": checked,
                "total_space": total,
            }, "counterexample", total
    return None, "target_holds_in_model", total


def main():
    raw = _download()
    rows, proofs, _, _, source_hashes, archive_hash = _read_corpus(raw)
    files = _archive_files(raw)
    rows_by_id = {str(row["id"]): row for row in rows}
    current = sorted(set(rows_by_id) - proofs - RETAINED - PENDING_KERNEL)

    equation_text = {}
    for row in rows:
        equation_text.setdefault(int(row["eq1_id"]), str(row["equation1"]))
        equation_text.setdefault(int(row["eq2_id"]), str(row["equation2"]))
    parsed = {eq_id: _parse_identity(text) for eq_id, text in equation_text.items()}

    records = {}
    for proof_id in sorted(proofs):
        row = rows_by_id.get(proof_id)
        blob = files.get(f"proofs/{proof_id}.lean")
        if row is None or blob is None:
            continue
        text = blob.decode("utf-8", errors="replace")
        if _verdict(text) != "false":
            continue
        for n, table, syntax in _extract_tables(text):
            key = (n, table)
            rec = records.setdefault(key, {
                "n": n,
                "table": table,
                "donor_ids": [],
                "donor_sources": set(),
                "syntaxes": set(),
            })
            rec["donor_ids"].append(proof_id)
            rec["donor_sources"].add(int(row["eq1_id"]))
            rec["syntaxes"].add(syntax)

    current_sources = sorted({int(rows_by_id[p]["eq1_id"]) for p in current})
    access = defaultdict(list)
    match_checks = 0
    for rec in records.values():
        for donor_source in sorted(rec["donor_sources"]):
            dl, dr, _ = parsed[donor_source]
            for current_source in current_sources:
                match_checks += 1
                cl, cr, _ = parsed[current_source]
                match = _specializes(dl, dr, cl, cr)
                if match is not None:
                    access[current_source].append((rec, donor_source, match))

    hits = {}
    local_holds = 0
    skipped_large = 0
    exact_pairs = 0
    assignment_work = 0
    hit_orders = Counter()

    for problem_id in current:
        row = rows_by_id[problem_id]
        source = int(row["eq1_id"])
        target = parsed[int(row["eq2_id"])]
        seen = set()
        for rec, donor_source, match in access.get(source, ()):
            key = (rec["n"], rec["table"])
            if key in seen:
                continue
            seen.add(key)
            witness, status, total = _exhaustive_witness(target, rec["n"], rec["table"])
            if status == "skipped_large":
                skipped_large += 1
                continue
            exact_pairs += 1
            assignment_work += witness["checked"] if witness is not None else total
            if status == "target_holds_in_model":
                local_holds += 1
                continue
            hits[problem_id] = {
                "model_order": rec["n"],
                "historical_donors": rec["donor_ids"][:20],
                "donor_source": donor_source,
                "premise_specialization": match,
                "target_witness": witness,
                "table": list(rec["table"]),
            }
            hit_orders[rec["n"]] += 1
            break

    result = {
        "experiment": "realitygraph-concrete-table-exact-replay-v1",
        "upstream": {
            "commit": COMMIT,
            "archive_sha256": archive_hash,
            "dataset_sha256": source_hashes,
        },
        "scope": {
            "input_frontier_excluding_pending_kernel": len(current),
            "pending_kernel_candidates_excluded": len(PENDING_KERNEL),
            "unique_concrete_tables": len(records),
            "match_checks": match_checks,
            "max_exhaustive_assignments_per_pair": MAX_EXHAUSTIVE_ASSIGNMENTS,
        },
        "replay": {
            "exact_table_target_pairs": exact_pairs,
            "assignment_evaluations": assignment_work,
            "targets_proved_holding_in_inherited_model": local_holds,
            "pairs_skipped_as_too_large": skipped_large,
            "new_exact_hits": len(hits),
            "hits_by_order": dict(hit_orders),
            "hits": hits,
            "frontier_if_pending_and_new_hits_verify": len(current) - len(hits),
            "new_model_search": 0,
        },
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    out=Path("results/equational-concrete-table-exact-replay-v1.json")
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")


if __name__=="__main__":
    main()
