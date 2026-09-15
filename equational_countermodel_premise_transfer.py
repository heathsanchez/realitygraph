from __future__ import annotations

import hashlib
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
}


def _download():
    req = urllib.request.Request(
        URL,
        headers={"User-Agent": "RealityGraph/1.0 countermodel premise transfer"},
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


def _classify(text):
    if re.search(r"finOpTable\s+\"", text):
        return "literal_fin_table"
    if re.search(r"abbrev\s+CM\s*:=\s*Bool(?:\s*×\s*Bool)+", text):
        return "bool_tuple_finite"
    if (
        re.search(r"abbrev\s+CM\s*:=", text)
        and "decideFin!" in text
        and re.search(r"\bdef\s+op\b", text)
    ):
        return "structured_finite_decide"
    if (
        "noncomputable def eval" in text
        and ("inductive " in text or "structure " in text)
    ):
        return "free_completion_infinite"
    if "Magma Nat" in text or "Magma Int" in text:
        return "nat_or_int_infinite"
    if "noncomputable" in text:
        return "other_noncomputable_countermodel"
    return "other_countermodel"


def _parse(formula):
    lhs, rhs = [part.strip() for part in formula.split("=", 1)]
    return _Parser(lhs).parse(), _Parser(rhs).parse()


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
    parsed = {eq_id: _parse(formula) for eq_id, formula in equation_text.items()}

    donor_by_source = defaultdict(list)
    family_counts = Counter()
    for proof_id in sorted(proofs):
        row = rows_by_id.get(proof_id)
        raw_proof = files.get(f"proofs/{proof_id}.lean")
        if row is None or raw_proof is None:
            continue
        text = raw_proof.decode("utf-8", errors="replace")
        if _verdict(text) != "false":
            continue
        family = _classify(text)
        if family == "literal_fin_table":
            continue
        source = int(row["eq1_id"])
        donor_by_source[source].append((proof_id, family))
        family_counts[family] += 1

    donor_sources = sorted(donor_by_source)
    current_sources = sorted({int(rows_by_id[p]["eq1_id"]) for p in current})
    source_matches = defaultdict(list)
    checks = 0
    for donor_source in donor_sources:
        donor_lhs, donor_rhs = parsed[donor_source]
        for current_source in current_sources:
            checks += 1
            current_lhs, current_rhs = parsed[current_source]
            # Current premise must be a substitution instance of donor premise:
            # donor universal identity => current identity.
            match = _specializes(
                donor_lhs,
                donor_rhs,
                current_lhs,
                current_rhs,
            )
            if match is None:
                continue
            for proof_id, family in donor_by_source[donor_source]:
                source_matches[current_source].append(
                    {
                        "donor_source": donor_source,
                        "donor_id": proof_id,
                        "family": family,
                        "premise_specialization": match,
                    }
                )

    residual_matches = {}
    family_residual_counts = Counter()
    for problem_id in current:
        source = int(rows_by_id[problem_id]["eq1_id"])
        matches = source_matches.get(source, ())
        if not matches:
            continue
        residual_matches[problem_id] = list(matches)
        for family in {m["family"] for m in matches}:
            family_residual_counts[family] += 1

    finite_transfer_candidates = {
        pid: [
            match for match in matches
            if match["family"] in {"bool_tuple_finite", "structured_finite_decide"}
        ]
        for pid, matches in residual_matches.items()
    }
    finite_transfer_candidates = {
        pid: matches for pid, matches in finite_transfer_candidates.items() if matches
    }

    result = {
        "experiment": "realitygraph-countermodel-premise-transfer-v1",
        "upstream": {
            "commit": COMMIT,
            "archive_sha256": archive_hash,
            "dataset_sha256": source_hashes,
            "acquisition": "anonymous pinned codeload archive; no fork/star/watch/upstream write",
        },
        "scope": {
            "input_frontier": len(current),
            "current_premise_sources": len(current_sources),
            "nonliteral_false_donor_sources": len(donor_sources),
            "nonliteral_false_certificates": sum(family_counts.values()),
            "premise_specialization_checks": checks,
            "donor_family_counts": dict(family_counts),
        },
        "transfer": {
            "current_sources_with_transferable_constructor": len(source_matches),
            "residuals_with_transferable_constructor": len(residual_matches),
            "residual_counts_by_family": dict(family_residual_counts),
            "finite_structured_transfer_candidates": finite_transfer_candidates,
            "finite_structured_candidate_count": len(finite_transfer_candidates),
            "all_transfer_examples": dict(list(residual_matches.items())[:80]),
        },
        "signal": {
            "cross_premise_countermodel_transfer_exists": len(residual_matches) > 0,
            "finite_structured_cross_premise_targets_exist": len(finite_transfer_candidates) > 0,
        },
    }

    print(json.dumps(result, indent=2, sort_keys=True))
    out = Path("results/equational-countermodel-premise-transfer-v1.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
