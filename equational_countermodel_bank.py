from __future__ import annotations

import ast
import hashlib
import itertools
import json
import math
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from equational_residual_demo import _Parser, _download_archive, _pair_features, _read_corpus
from equational_transition_demo import _archive_files, _distance, _zscore_parameters


def _parse_identity(formula):
    lhs_text, rhs_text = [part.strip() for part in str(formula).split("=", 1)]
    lhs = _Parser(lhs_text).parse()
    rhs = _Parser(rhs_text).parse()
    variables = tuple(sorted(set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", str(formula)))))
    return lhs, rhs, variables


def _eval_term(node, env, table, n):
    if node[0] == "v":
        return env[node[1]]
    a = _eval_term(node[1], env, table, n)
    b = _eval_term(node[2], env, table, n)
    return table[a * n + b]


def _identity_holds(parsed, table, n):
    lhs, rhs, variables = parsed
    checked = 0
    for values in itertools.product(range(n), repeat=len(variables)):
        checked += 1
        env = dict(zip(variables, values))
        if _eval_term(lhs, env, table, n) != _eval_term(rhs, env, table, n):
            return False, checked
    return True, checked


def _identity_failure(parsed, table, n):
    lhs, rhs, variables = parsed
    checked = 0
    for values in itertools.product(range(n), repeat=len(variables)):
        checked += 1
        env = dict(zip(variables, values))
        lv = _eval_term(lhs, env, table, n)
        rv = _eval_term(rhs, env, table, n)
        if lv != rv:
            return {
                "assignment": env,
                "lhs": lv,
                "rhs": rv,
                "assignments_checked": checked,
            }
    return None


def _flatten_matrix(value):
    if not isinstance(value, list) or not value:
        return None
    if all(isinstance(row, list) for row in value):
        return [int(x) for row in value for x in row]
    if all(isinstance(x, int) for x in value):
        return [int(x) for x in value]
    return None


def _extract_literal_model(text: str):
    body_at = text.find("-- Original submission body")
    body = text[body_at:] if body_at >= 0 else text

    patterns = [
        r"let\s+\w+\s*:\s*Magma\s*\(Fin\s+(\d+)\)\s*:=\s*\{.*?finOpTable\s+\"([^\"]+)\"",
        r"refine\s*⟨Fin\s+(\d+).*?finOpTable\s+\"([^\"]+)\"",
    ]
    for pattern in patterns:
        match = re.search(pattern, body, flags=re.DOTALL)
        if match:
            n = int(match.group(1))
            try:
                matrix = ast.literal_eval(match.group(2))
            except (ValueError, SyntaxError):
                continue
            table = _flatten_matrix(matrix)
            if table is not None and len(table) == n * n and all(0 <= x < n for x in table):
                return n, tuple(table)

    match = re.search(
        r"magmaFin\s+(\d+)\s+\[([0-9,\s]+)\]",
        body,
        flags=re.DOTALL,
    )
    if match:
        n = int(match.group(1))
        table = tuple(int(x) for x in re.findall(r"\d+", match.group(2)))
        if len(table) == n * n and all(0 <= x < n for x in table):
            return n, table
    return None


def _verdict(text: str):
    match = re.search(r"-- Recorded verdict:\s*(true|false)", text)
    return None if match is None else match.group(1)


def _feature_table(rows):
    names = None
    vectors = {}
    for row in rows:
        feature_names, values, _, _ = _pair_features(row)
        if names is None:
            names = feature_names
        elif names != feature_names:
            raise ValueError("feature layout drift")
        vectors[str(row["id"])] = values
    if names is None:
        raise ValueError("empty corpus")
    return names, vectors


def main():
    raw = _download_archive()
    rows, final_proofs, _, _, source_hashes, archive_hash = _read_corpus(raw)
    files = _archive_files(raw)
    rows_by_id = {str(row["id"]): row for row in rows}
    all_ids = sorted(rows_by_id)
    current = sorted(set(all_ids) - final_proofs)
    if len(current) != 571:
        raise ValueError(f"expected 571 current residuals, got {len(current)}")

    feature_names, vectors = _feature_table(rows)
    means, scales = _zscore_parameters(vectors, all_ids)

    bank = []
    unique_tables = {}
    for problem_id in sorted(final_proofs):
        raw_proof = files.get(f"proofs/{problem_id}.lean")
        if raw_proof is None:
            continue
        text = raw_proof.decode("utf-8", errors="replace")
        if _verdict(text) != "false":
            continue
        model = _extract_literal_model(text)
        if model is None:
            continue
        n, table = model
        row = rows_by_id.get(problem_id)
        if row is None:
            continue
        key = (n, table)
        entry = {
            "donor_id": problem_id,
            "source_eq": int(row["eq1_id"]),
            "target_eq": int(row["eq2_id"]),
            "n": n,
            "table": table,
            "vector": vectors[problem_id],
        }
        bank.append(entry)
        unique_tables.setdefault(key, entry)

    bank_unique = list(unique_tables.values())
    size_counts = Counter(entry["n"] for entry in bank_unique)
    by_source = defaultdict(list)
    for entry in bank_unique:
        by_source[entry["source_eq"]].append(entry)

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

    source_check_cache = {}
    tests = 0
    source_assignments = 0
    target_assignments = 0
    hits = {}
    donor_hit_counts = Counter()

    def test(problem_id, donor, kind):
        nonlocal tests, source_assignments, target_assignments
        if problem_id in hits:
            return
        tests += 1
        source, target = parsed(problem_id)
        cache_key = (str(rows_by_id[problem_id]["eq1_id"]), donor["n"], donor["table"])
        cached = source_check_cache.get(cache_key)
        if cached is None:
            source_ok, checked = _identity_holds(source, donor["table"], donor["n"])
            source_check_cache[cache_key] = source_ok
            source_assignments += checked
        else:
            source_ok = cached
        if not source_ok:
            return
        witness = _identity_failure(target, donor["table"], donor["n"])
        if witness is None:
            target_assignments += donor["n"] ** len(target[2])
            return
        target_assignments += witness["assignments_checked"]
        hits[problem_id] = {
            "donor_id": donor["donor_id"],
            "reuse_kind": kind,
            "n": donor["n"],
            "table": list(donor["table"]),
            "target_witness": witness,
            "source_universally_verified": True,
        }
        donor_hit_counts[donor["donor_id"]] += 1

    # Tier 1: exact same-premise reuse. This is the strongest zero-search transfer.
    same_source_candidates = 0
    for problem_id in current:
        source_eq = int(rows_by_id[problem_id]["eq1_id"])
        donors = by_source.get(source_eq, ())
        if donors:
            same_source_candidates += 1
        for donor in donors:
            test(problem_id, donor, "same_premise")

    # Tier 2: nearest previously verified literal finite countermodels.
    # Source failure aborts immediately, so most rejected transfers are cheap.
    nearest_k = 16
    max_model_order = 12
    eligible_bank = [entry for entry in bank_unique if entry["n"] <= max_model_order]
    for problem_id in current:
        if problem_id in hits:
            continue
        ranked = sorted(
            eligible_bank,
            key=lambda donor: _distance(
                vectors[problem_id],
                donor["vector"],
                means,
                scales,
            ),
        )[:nearest_k]
        for donor in ranked:
            test(problem_id, donor, "nearest_structure")
            if problem_id in hits:
                break

    collapse_by_source = Counter(int(rows_by_id[problem_id]["eq1_id"]) for problem_id in hits)
    collapse_by_order = Counter(item["n"] for item in hits.values())
    top_donors = donor_hit_counts.most_common(20)

    result = {
        "experiment": "realitygraph-compiled-countermodel-bank-v1",
        "upstream": {
            "commit": "bed33e36c33fca139d902addd8cb77cd4172fe64",
            "archive_sha256": archive_hash,
            "dataset_sha256": source_hashes,
            "acquisition": "anonymous pinned codeload archive; no fork/star/watch/upstream write",
        },
        "bank": {
            "literal_model_certificates": len(bank),
            "unique_literal_models": len(bank_unique),
            "orders": dict(sorted(size_counts.items())),
            "max_order": max(size_counts) if size_counts else None,
        },
        "current_residual": {
            "total": len(current),
            "with_same_premise_model": same_source_candidates,
            "models_per_nearest_probe": nearest_k,
            "exact_collapsed": len(hits),
            "remaining": len(current) - len(hits),
            "collapse_by_model_order": dict(sorted(collapse_by_order.items())),
            "collapse_by_source_equation": dict(collapse_by_source.most_common()),
            "top_reusable_donors": top_donors,
            "hits": hits,
        },
        "work": {
            "candidate_model_transfers_tested": tests,
            "unique_source_model_checks": len(source_check_cache),
            "source_assignments_checked": source_assignments,
            "target_assignments_checked": target_assignments,
            "new_model_search": 0,
        },
    }
    result["signal"] = {
        "compiled_experience_collapses_current_residual": len(hits) > 0,
        "one_model_collapses_multiple_residuals": any(count > 1 for _, count in top_donors),
        "zero_search": True,
    }

    print(json.dumps(result, indent=2, sort_keys=True))
    path = Path("results/equational-countermodel-bank-v1.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
