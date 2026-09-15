from __future__ import annotations

import ast
import hashlib
import itertools
import json
import re
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

from equational_residual_demo import _Parser, _read_corpus
from equational_transition_demo import _archive_files
from equational_internal_lemma_bank import _specializes

COMMIT = "bed33e36c33fca139d902addd8cb77cd4172fe64"
URL = f"https://codeload.github.com/YanbiaoLab/equational-challenges/tar.gz/{COMMIT}"
EXPECTED_SHA = "284b45196a9e8a31f1bd3aeb05040c451a615fed2ca8ba724d7a14a833e842eb"
RETAINED = {
    "17195_to_43536",
    "4922_to_4158",
    "4922_to_4258",
    "22268_to_22436",
    "22505_to_40367",
}
MAX_WITNESS_ASSIGNMENTS = 20000
SMALL_VALUE_CAP = 6


def _download():
    req = urllib.request.Request(
        URL,
        headers={"User-Agent": "RealityGraph/1.0 concrete-table-replay"},
    )
    with urllib.request.urlopen(req, timeout=90) as response:
        raw = response.read()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != EXPECTED_SHA:
        raise ValueError(f"archive hash mismatch: {digest}")
    return raw


def _verdict(text):
    m = re.search(r"-- Recorded verdict:\s*(true|false)", text)
    return None if m is None else m.group(1)


def _parse_identity(formula):
    lhs_text, rhs_text = [part.strip() for part in formula.split("=", 1)]
    lhs = _Parser(lhs_text).parse()
    rhs = _Parser(rhs_text).parse()
    variables = tuple(sorted(set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", formula))))
    return lhs, rhs, variables


def _extract_tables(text):
    out = []

    # Ignore embedded helper/documentation examples. Only scan the actual
    # submission/corrected-submission body where a countermodel is constructed.
    markers = [
        text.rfind("-- Original submission body"),
        text.rfind("-- Aurora-accepted corrected submission body"),
    ]
    body_start = max(markers)
    if body_start >= 0:
        text = text[body_start:]

    # finOpTable string syntax.
    for m in re.finditer(
        r"let\s+\w+\s*:\s*Magma\s*\(Fin\s+(\d+)\)\s*:=\s*\{\s*"
        r"op\s*:=\s*finOpTable\s+\"([^\"]+)\"\s*\}",
        text,
        re.DOTALL,
    ):
        n = int(m.group(1))
        digits = [int(ch) for ch in m.group(2) if ch.isdigit()]
        if len(digits) == n * n:
            out.append((n, tuple(v % n for v in digits), "finOpTable"))

    # literal magmaFin n [ ... ] syntax.
    for m in re.finditer(r"magmaFin\s+(\d+)\s*\[", text):
        n = int(m.group(1))
        start = m.end() - 1
        depth = 0
        end = None
        for i in range(start, len(text)):
            ch = text[i]
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        if end is None:
            continue
        body = text[start + 1:end]
        if re.search(r"[^0-9,\s]", body):
            continue
        vals = [int(x) for x in re.findall(r"\d+", body)]
        if len(vals) == n * n:
            out.append((n, tuple(v % n for v in vals), "magmaFin_literal"))

    # Deduplicate inside certificate.
    seen = set()
    unique = []
    for item in out:
        key = (item[0], item[1])
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def _eval(node, env, n, table):
    if node[0] == "v":
        return env[node[1]]
    a = _eval(node[1], env, n, table)
    b = _eval(node[2], env, n, table)
    return table[a * n + b]


def _witness(identity, n, table):
    lhs, rhs, variables = identity
    values = list(range(min(n, SMALL_VALUE_CAP)))
    checked = 0

    # First cover low-value cube. This tends to find finite-model witnesses fast.
    for assignment in itertools.product(values, repeat=len(variables)):
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
                "search": "low_value_cube",
            }
        if checked >= MAX_WITNESS_ASSIGNMENTS:
            return None

    # Then deterministic diagonal / edge probes over the whole carrier.
    probes = []
    for v in range(n):
        probes.append(tuple(v for _ in variables))
    for i in range(len(variables)):
        for v in range(n):
            a = [0] * len(variables)
            a[i] = v
            probes.append(tuple(a))

    seen = set()
    for assignment in probes:
        if assignment in seen:
            continue
        seen.add(assignment)
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
                "search": "carrier_edge_probes",
            }
        if checked >= MAX_WITNESS_ASSIGNMENTS:
            break
    return None


def main():
    raw = _download()
    rows, proofs, _, _, source_hashes, archive_hash = _read_corpus(raw)
    files = _archive_files(raw)
    rows_by_id = {str(row["id"]): row for row in rows}
    current = sorted(set(rows_by_id) - proofs - RETAINED)

    equation_text = {}
    for row in rows:
        equation_text.setdefault(int(row["eq1_id"]), str(row["equation1"]))
        equation_text.setdefault(int(row["eq2_id"]), str(row["equation2"]))
    parsed_eq = {
        eq_id: _parse_identity(formula)
        for eq_id, formula in equation_text.items()
    }

    table_records = []
    table_seen = {}
    extraction_counts = Counter()
    for proof_id in sorted(proofs):
        row = rows_by_id.get(proof_id)
        blob = files.get(f"proofs/{proof_id}.lean")
        if row is None or blob is None:
            continue
        text = blob.decode("utf-8", errors="replace")
        if _verdict(text) != "false":
            continue
        for n, table, syntax in _extract_tables(text):
            extraction_counts[syntax] += 1
            key = (n, table)
            rec = table_seen.get(key)
            if rec is None:
                rec = {
                    "n": n,
                    "table": table,
                    "donor_ids": [],
                    "donor_sources": set(),
                    "syntaxes": set(),
                }
                table_seen[key] = rec
                table_records.append(rec)
            rec["donor_ids"].append(proof_id)
            rec["donor_sources"].add(int(row["eq1_id"]))
            rec["syntaxes"].add(syntax)

    current_sources = sorted({int(rows_by_id[p]["eq1_id"]) for p in current})

    # Sound routing: donor premise universally implies current premise by specialization.
    accessible_by_source = defaultdict(list)
    specialization_checks = 0
    for rec in table_records:
        for donor_source in sorted(rec["donor_sources"]):
            dl, dr, _ = parsed_eq[donor_source]
            for current_source in current_sources:
                specialization_checks += 1
                cl, cr, _ = parsed_eq[current_source]
                match = _specializes(dl, dr, cl, cr)
                if match is not None:
                    accessible_by_source[current_source].append(
                        {
                            "record": rec,
                            "donor_source": donor_source,
                            "match": match,
                        }
                    )

    hits = {}
    candidate_pairs = 0
    witness_checks = 0
    table_orders = Counter()
    routed_residuals = 0

    for problem_id in current:
        row = rows_by_id[problem_id]
        source = int(row["eq1_id"])
        candidates = accessible_by_source.get(source, ())
        if not candidates:
            continue
        routed_residuals += 1
        target = parsed_eq[int(row["eq2_id"])]

        # Dedup same table inherited via multiple donor sources.
        seen_tables = set()
        for candidate in candidates:
            rec = candidate["record"]
            key = (rec["n"], rec["table"])
            if key in seen_tables:
                continue
            seen_tables.add(key)
            candidate_pairs += 1
            witness = _witness(target, rec["n"], rec["table"])
            witness_checks += witness["checked"] if witness is not None else MAX_WITNESS_ASSIGNMENTS
            if witness is None:
                continue
            hits[problem_id] = {
                "model_order": rec["n"],
                "table": list(rec["table"]),
                "historical_donors": rec["donor_ids"][:20],
                "donor_source": candidate["donor_source"],
                "premise_specialization": candidate["match"],
                "target_witness": witness,
            }
            table_orders[rec["n"]] += 1
            break

    result = {
        "experiment": "realitygraph-concrete-table-bank-v1",
        "upstream": {
            "commit": COMMIT,
            "archive_sha256": archive_hash,
            "dataset_sha256": source_hashes,
            "acquisition": "anonymous pinned codeload archive; no fork/star/watch/upstream write",
        },
        "bank": {
            "unique_concrete_tables": len(table_records),
            "certificate_table_occurrences": sum(len(r["donor_ids"]) for r in table_records),
            "syntax_counts": dict(extraction_counts),
            "orders": dict(Counter(r["n"] for r in table_records)),
        },
        "routing": {
            "current_premise_sources": len(current_sources),
            "specialization_checks": specialization_checks,
            "routed_current_sources": len(accessible_by_source),
            "routed_residuals": routed_residuals,
        },
        "replay": {
            "input_frontier": len(current),
            "candidate_table_target_pairs": candidate_pairs,
            "new_exact_hits": len(hits),
            "hits_by_order": dict(table_orders),
            "hits": hits,
            "frontier_if_kernel_verified": len(current) - len(hits),
            "miss_semantics": "UNKNOWN: bounded witness search found no counterexample; no truth claim",
            "max_witness_assignments_per_pair": MAX_WITNESS_ASSIGNMENTS,
            "new_model_search": 0,
        },
        "signal": {
            "compiled_table_bank_adds_consequences": len(hits) > 0,
        },
    }

    print(json.dumps(result, indent=2, sort_keys=True))
    out = Path("results/equational-concrete-table-bank-v1.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
