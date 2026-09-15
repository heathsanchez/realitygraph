from __future__ import annotations

import itertools
import json
from collections import Counter
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
MAX_SOURCE_EXHAUSTIVE = 1_000_000
MAX_TARGET_SEARCH = 200_000
QUICK_VALUES = 3


def _quick_source_reject(identity, n, table):
    lhs, rhs, variables = identity
    values = range(min(n, QUICK_VALUES))
    checked = 0
    for assignment in itertools.product(values, repeat=len(variables)):
        checked += 1
        env = dict(zip(variables, assignment))
        if _eval(lhs, env, n, table) != _eval(rhs, env, n, table):
            return True, checked
    return False, checked


def _source_holds(identity, n, table):
    lhs, rhs, variables = identity
    total = n ** len(variables)
    rejected, quick = _quick_source_reject(identity, n, table)
    if rejected:
        return False, "quick_reject", quick, total
    if total > MAX_SOURCE_EXHAUSTIVE:
        return None, "source_too_large", quick, total
    checked = 0
    for assignment in itertools.product(range(n), repeat=len(variables)):
        checked += 1
        env = dict(zip(variables, assignment))
        if _eval(lhs, env, n, table) != _eval(rhs, env, n, table):
            return False, "exhaustive_reject", quick + checked, total
    return True, "verified_holds", quick + checked, total


def _target_witness(identity, n, table):
    lhs, rhs, variables = identity
    total = n ** len(variables)
    checked = 0

    # Full exhaustive pass whenever cheap enough.
    if total <= MAX_TARGET_SEARCH:
        iterator = itertools.product(range(n), repeat=len(variables))
        mode = "exhaustive"
    else:
        # Deterministic low-value prefix; misses remain UNKNOWN.
        iterator = itertools.product(range(min(n, QUICK_VALUES + 2)), repeat=len(variables))
        mode = "bounded_low_cube"

    for assignment in iterator:
        checked += 1
        if checked > MAX_TARGET_SEARCH:
            break
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
                "search": mode,
            }
    return None


def main():
    raw = _download()
    rows, proofs, _, _, source_hashes, archive_hash = _read_corpus(raw)
    files = _archive_files(raw)
    rows_by_id = {str(row["id"]): row for row in rows}
    current = sorted(set(rows_by_id) - proofs - RETAINED - PENDING_KERNEL)

    eqtext = {}
    for row in rows:
        eqtext.setdefault(int(row["eq1_id"]), str(row["equation1"]))
        eqtext.setdefault(int(row["eq2_id"]), str(row["equation2"]))
    parsed = {eq_id: _parse_identity(text) for eq_id, text in eqtext.items()}

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
    source_models = {}
    source_stats = Counter()
    evaluation_work = 0

    # Global model-bank routing: history/source identity is irrelevant here.
    for source in current_sources:
        identity = parsed[source]
        good = []
        for rec in records.values():
            holds, status, checked, total = _source_holds(identity, rec["n"], rec["table"])
            source_stats[status] += 1
            evaluation_work += checked
            if holds is True:
                good.append(rec)
        if good:
            source_models[source] = good

    hits = {}
    target_checks = 0
    target_work = 0
    hit_orders = Counter()
    cross_source_hits = 0

    for problem_id in current:
        row = rows_by_id[problem_id]
        source = int(row["eq1_id"])
        target = parsed[int(row["eq2_id"])]
        for rec in source_models.get(source, ()):
            target_checks += 1
            witness = _target_witness(target, rec["n"], rec["table"])
            if witness is None:
                continue
            target_work += witness["checked"]
            donor_sources = sorted(rec["donor_sources"])
            if source not in rec["donor_sources"]:
                cross_source_hits += 1
            hits[problem_id] = {
                "model_order": rec["n"],
                "historical_donors": rec["donor_ids"][:20],
                "historical_donor_sources": donor_sources[:20],
                "cross_source_transfer": source not in rec["donor_sources"],
                "source_verification": "direct exhaustive evaluation in concrete finite magma",
                "target_witness": witness,
                "table": list(rec["table"]),
            }
            hit_orders[rec["n"]] += 1
            break

    result = {
        "experiment": "realitygraph-global-finite-model-bank-v1",
        "upstream": {
            "commit": COMMIT,
            "archive_sha256": archive_hash,
            "dataset_sha256": source_hashes,
        },
        "bank": {
            "unique_verified_concrete_models": len(records),
            "orders": dict(Counter(r["n"] for r in records.values())),
        },
        "source_routing": {
            "current_premise_sources": len(current_sources),
            "sources_with_at_least_one_verified_model": len(source_models),
            "source_model_pairs_by_status": dict(source_stats),
            "source_evaluation_work": evaluation_work,
            "max_source_exhaustive_assignments": MAX_SOURCE_EXHAUSTIVE,
        },
        "replay": {
            "input_frontier_excluding_pending_kernel": len(current),
            "pending_kernel_candidates_excluded": len(PENDING_KERNEL),
            "target_model_pairs_tested": target_checks,
            "new_exact_hits": len(hits),
            "cross_source_hits": cross_source_hits,
            "hits_by_order": dict(hit_orders),
            "hits": hits,
            "frontier_if_pending_and_new_hits_verify": len(current) - len(hits),
            "miss_semantics": "UNKNOWN unless a concrete target witness is found",
            "new_model_search": 0,
        },
        "signal": {
            "history_independent_model_reuse_adds_consequences": len(hits) > 0,
            "genuine_cross_source_transfer_exists": cross_source_hits > 0,
        },
    }

    print(json.dumps(result, indent=2, sort_keys=True))
    out=Path("results/equational-global-finite-model-bank-v1.json")
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")


if __name__=="__main__":
    main()
