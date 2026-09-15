from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

from equational_residual_demo import _Parser, _read_corpus
from equational_transition_demo import _archive_files

COMMIT = "bed33e36c33fca139d902addd8cb77cd4172fe64"
ARCHIVE_URL = f"https://codeload.github.com/YanbiaoLab/equational-challenges/tar.gz/{COMMIT}"
EXPECTED_ARCHIVE_SHA256 = "284b45196a9e8a31f1bd3aeb05040c451a615fed2ca8ba724d7a14a833e842eb"


def _download():
    request = urllib.request.Request(
        ARCHIVE_URL,
        headers={"User-Agent": "RealityGraph/1.0 passive derived-law specialization"},
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        raw = response.read()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != EXPECTED_ARCHIVE_SHA256:
        raise ValueError(f"archive hash mismatch: {digest}")
    return raw


def _verdict(text: str):
    match = re.search(r"-- Recorded verdict:\s*(true|false)", text)
    return None if match is None else match.group(1)


def _parse_equation(formula: str):
    lhs_text, rhs_text = [part.strip() for part in formula.split("=", 1)]
    return _Parser(lhs_text).parse(), _Parser(rhs_text).parse()


def _match(pattern, target, subst):
    if pattern[0] == "v":
        name = pattern[1]
        old = subst.get(name)
        if old is None:
            subst[name] = target
            return True
        return old == target
    if target[0] != "*":
        return False
    return _match(pattern[1], target[1], subst) and _match(pattern[2], target[2], subst)


def _term_text(node):
    if node[0] == "v":
        return node[1]
    return f"({_term_text(node[1])} ◇ {_term_text(node[2])})"


def _specializes(general_formula: str, target_formula: str):
    general = _parse_equation(general_formula)
    target = _parse_equation(target_formula)
    for orientation, oriented in (
        ("direct", target),
        ("symmetric", (target[1], target[0])),
    ):
        subst = {}
        if _match(general[0], oriented[0], subst) and _match(
            general[1], oriented[1], subst
        ):
            return {
                "orientation": orientation,
                "substitution": {
                    name: _term_text(term)
                    for name, term in sorted(subst.items())
                },
            }
    return None


def main():
    raw = _download()
    rows, proofs, _, _, source_hashes, archive_hash = _read_corpus(raw)
    files = _archive_files(raw)
    rows_by_id = {str(row["id"]): row for row in rows}
    current = sorted(set(rows_by_id) - proofs)

    true_by_source = defaultdict(list)
    true_count = 0
    for problem_id in sorted(proofs):
        row = rows_by_id.get(problem_id)
        if row is None:
            continue
        proof = files.get(f"proofs/{problem_id}.lean")
        if proof is None:
            continue
        if _verdict(proof.decode("utf-8", errors="replace")) != "true":
            continue
        true_count += 1
        true_by_source[int(row["eq1_id"])].append(problem_id)

    hits = {}
    candidates = 0
    current_with_donor = 0
    donors_per_source = Counter()
    for problem_id in current:
        row = rows_by_id[problem_id]
        donors = true_by_source.get(int(row["eq1_id"]), ())
        if donors:
            current_with_donor += 1
        donors_per_source[len(donors)] += 1
        for donor_id in donors:
            candidates += 1
            donor_row = rows_by_id[donor_id]
            specialization = _specializes(
                str(donor_row["equation2"]),
                str(row["equation2"]),
            )
            if specialization is None:
                continue
            hits[problem_id] = {
                "donor_id": donor_id,
                "premise_equation_id": int(row["eq1_id"]),
                "derived_equation_id": int(donor_row["eq2_id"]),
                "target_equation_id": int(row["eq2_id"]),
                **specialization,
            }
            break

    result = {
        "experiment": "realitygraph-derived-law-specialization-v1",
        "upstream": {
            "commit": COMMIT,
            "archive_sha256": archive_hash,
            "dataset_sha256": source_hashes,
            "acquisition": "anonymous pinned codeload archive; no fork/star/watch/upstream write",
        },
        "bank": {
            "verified_true_certificates": true_count,
            "premises_with_true_donors": len(true_by_source),
        },
        "current_residual": {
            "total": len(current),
            "with_same_premise_true_donor": current_with_donor,
            "candidate_derived_laws_checked": candidates,
            "new_exact_specialization_proofs": len(hits),
            "hits": hits,
        },
        "signal": {
            "derived_law_specialization_adds_new_proofs": len(hits) > 0,
        },
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    out = Path("results/equational-derived-specialization-v1.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
