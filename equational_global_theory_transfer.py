from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from collections import Counter, defaultdict, deque
from pathlib import Path

from equational_residual_demo import _Parser, _read_corpus
from equational_transition_demo import _archive_files
from equational_internal_lemma_bank import (
    _extract_internal_equalities,
    _specializes,
    _rewrite_proof,
    _apps,
    _text,
)

COMMIT = "bed33e36c33fca139d902addd8cb77cd4172fe64"
ARCHIVE_URL = f"https://codeload.github.com/YanbiaoLab/equational-challenges/tar.gz/{COMMIT}"
EXPECTED_ARCHIVE_SHA256 = "284b45196a9e8a31f1bd3aeb05040c451a615fed2ca8ba724d7a14a833e842eb"
RETAINED = {
    "17195_to_43536",
    "4922_to_4158",
    "4922_to_4258",
    "22268_to_22436",
}
MAX_REWRITE_LAWS = 450
MAX_REWRITE_LEMMA_APPS = 14


def _download():
    request = urllib.request.Request(
        ARCHIVE_URL,
        headers={"User-Agent": "RealityGraph/1.0 global theory transfer"},
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
    lhs, rhs = [part.strip() for part in formula.split("=", 1)]
    return _Parser(lhs).parse(), _Parser(rhs).parse()


def _eq_key(pair):
    lhs, rhs = pair
    return min((lhs, rhs), (rhs, lhs), key=repr)


def _short_reachable(adjacency, start, max_depth=4):
    seen = {start}
    depth = {start: 0}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        if depth[node] >= max_depth:
            continue
        for nxt in adjacency.get(node, ()):
            if nxt in seen:
                continue
            seen.add(nxt)
            depth[nxt] = depth[node] + 1
            queue.append(nxt)
    return seen


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

    parsed_equation = {
        eq_id: _parse_equation(formula)
        for eq_id, formula in equation_text.items()
    }

    true_by_source = defaultdict(list)
    adjacency = defaultdict(set)
    verified_true = 0
    for proof_id in sorted(proofs):
        row = rows_by_id.get(proof_id)
        proof = files.get(f"proofs/{proof_id}.lean")
        if row is None or proof is None:
            continue
        if _verdict(proof.decode("utf-8", errors="replace")) != "true":
            continue
        source = int(row["eq1_id"])
        target = int(row["eq2_id"])
        true_by_source[source].append(proof_id)
        adjacency[source].add(target)
        verified_true += 1

    donor_sources = sorted(true_by_source)
    current_sources = sorted({int(rows_by_id[p]["eq1_id"]) for p in current})

    access_by_current_source = {}
    transfer_reason_counts = Counter()
    premise_match_checks = 0
    for current_source in current_sources:
        accessible = {}
        # Exact and graph consequence access.
        for source in _short_reachable(adjacency, current_source, max_depth=4):
            if source in true_by_source:
                reason = "same_premise" if source == current_source else "published_true_chain"
                accessible[source] = reason

        cur_lhs, cur_rhs = parsed_equation[current_source]
        # Structural premise transfer: donor premise is a substitution instance
        # of the current premise, hence the current universal law implies it.
        for donor_source in donor_sources:
            if donor_source in accessible:
                continue
            premise_match_checks += 1
            don_lhs, don_rhs = parsed_equation[donor_source]
            match = _specializes(cur_lhs, cur_rhs, don_lhs, don_rhs)
            if match is not None:
                accessible[donor_source] = "premise_specialization"
        access_by_current_source[current_source] = accessible
        transfer_reason_counts.update(accessible.values())

    relevant_donor_sources = sorted(
        {
            donor_source
            for accessible in access_by_current_source.values()
            for donor_source in accessible
        }
    )
    relevant_proofs = sorted(
        {
            proof_id
            for source in relevant_donor_sources
            for proof_id in true_by_source[source]
        }
    )

    laws_by_source = defaultdict(list)
    seen_by_source = defaultdict(set)
    extraction_rejections = Counter()
    raw_internal_count = 0
    admitted_internal_count = 0
    published_count = 0

    for proof_id in relevant_proofs:
        row = rows_by_id[proof_id]
        source = int(row["eq1_id"])
        text = files[f"proofs/{proof_id}.lean"].decode("utf-8", errors="replace")
        internal, rejected = _extract_internal_equalities(text)
        extraction_rejections.update(rejected)
        raw_internal_count += len(internal)

        candidates = []
        for lemma in internal:
            candidates.append(
                {
                    "donor_id": proof_id,
                    "lemma_name": lemma["name"],
                    "lhs": lemma["lhs"],
                    "rhs": lemma["rhs"],
                    "lhs_text": lemma["lhs_text"],
                    "rhs_text": lemma["rhs_text"],
                    "apps": lemma["apps"],
                    "origin": "internal",
                }
            )
        final_lhs, final_rhs = parsed_equation[int(row["eq2_id"])]
        candidates.append(
            {
                "donor_id": proof_id,
                "lemma_name": "published_conclusion",
                "lhs": final_lhs,
                "rhs": final_rhs,
                "lhs_text": _text(final_lhs),
                "rhs_text": _text(final_rhs),
                "apps": max(_apps(final_lhs), _apps(final_rhs)),
                "origin": "published",
            }
        )

        for law in candidates:
            key = _eq_key((law["lhs"], law["rhs"]))
            if key in seen_by_source[source]:
                continue
            seen_by_source[source].add(key)
            laws_by_source[source].append(law)
            if law["origin"] == "internal":
                admitted_internal_count += 1
            else:
                published_count += 1

    specialization_hits = {}
    rewrite_hits = {}
    inherited_law_counts = {}
    inherited_source_counts = {}
    specialization_checks = 0

    for problem_id in current:
        row = rows_by_id[problem_id]
        current_source = int(row["eq1_id"])
        target_lhs, target_rhs = parsed_equation[int(row["eq2_id"])]
        accessible = access_by_current_source[current_source]

        bank = []
        seen = set()
        for donor_source, reason in accessible.items():
            for law in laws_by_source.get(donor_source, ()):
                key = _eq_key((law["lhs"], law["rhs"]))
                if key in seen:
                    continue
                seen.add(key)
                bank.append({**law, "transfer_reason": reason, "donor_source": donor_source})

        inherited_law_counts[problem_id] = len(bank)
        inherited_source_counts[problem_id] = len(accessible)

        for law in bank:
            specialization_checks += 1
            match = _specializes(
                law["lhs"],
                law["rhs"],
                target_lhs,
                target_rhs,
            )
            if match is None:
                continue
            specialization_hits[problem_id] = {
                "donor_id": law["donor_id"],
                "donor_source": law["donor_source"],
                "transfer_reason": law["transfer_reason"],
                "lemma_name": law["lemma_name"],
                "origin": law["origin"],
                "lemma": f'{law["lhs_text"]} = {law["rhs_text"]}',
                **match,
            }
            break

        if problem_id in specialization_hits:
            continue

        rewrite_bank = [
            law for law in bank
            if law["apps"] <= MAX_REWRITE_LEMMA_APPS
        ]
        if not rewrite_bank or len(rewrite_bank) > MAX_REWRITE_LAWS:
            continue
        proof = _rewrite_proof(target_lhs, target_rhs, rewrite_bank)
        if proof is not None:
            # Attach provenance to each step; _rewrite_proof already carries
            # donor_id/lemma_name from the law.
            rewrite_hits[problem_id] = {
                "inherited_sources": len(accessible),
                "inherited_laws": len(bank),
                "rewrite_laws": len(rewrite_bank),
                **proof,
            }

    all_hits = dict(specialization_hits)
    for problem_id, hit in rewrite_hits.items():
        all_hits.setdefault(problem_id, hit)

    law_count_values = list(inherited_law_counts.values())
    source_count_values = list(inherited_source_counts.values())

    result = {
        "experiment": "realitygraph-global-internal-theory-transfer-v1",
        "upstream": {
            "commit": COMMIT,
            "archive_sha256": archive_hash,
            "dataset_sha256": source_hashes,
            "acquisition": "anonymous pinned codeload archive; no fork/star/watch/upstream write",
        },
        "scope": {
            "input_frontier": len(current),
            "verified_true_certificates": verified_true,
            "true_premise_sources": len(donor_sources),
            "current_premise_sources": len(current_sources),
            "premise_match_checks": premise_match_checks,
            "relevant_donor_sources": len(relevant_donor_sources),
            "relevant_true_certificates": len(relevant_proofs),
            "transfer_reason_counts": dict(transfer_reason_counts),
        },
        "bank": {
            "raw_closed_internal_lemmas": raw_internal_count,
            "admitted_unique_internal_laws": admitted_internal_count,
            "admitted_unique_published_laws": published_count,
            "total_admitted_laws": admitted_internal_count + published_count,
            "extraction_rejections": dict(extraction_rejections),
        },
        "inheritance": {
            "mean_sources_per_residual": (
                sum(source_count_values) / len(source_count_values)
                if source_count_values else 0.0
            ),
            "max_sources_per_residual": max(source_count_values) if source_count_values else 0,
            "mean_laws_per_residual": (
                sum(law_count_values) / len(law_count_values)
                if law_count_values else 0.0
            ),
            "max_laws_per_residual": max(law_count_values) if law_count_values else 0,
            "residuals_with_any_inherited_law": sum(int(v > 0) for v in law_count_values),
        },
        "replay": {
            "specialization_checks": specialization_checks,
            "specialization_hits": specialization_hits,
            "rewrite_hits": rewrite_hits,
            "all_new_hits": all_hits,
            "new_exact_candidates": len(all_hits),
            "frontier_if_kernel_verified": len(current) - len(all_hits),
        },
        "bounds": {
            "published_true_chain_depth": 4,
            "max_rewrite_laws": MAX_REWRITE_LAWS,
            "max_rewrite_lemma_apps": MAX_REWRITE_LEMMA_APPS,
        },
        "signal": {
            "cross_premise_theory_transfer_adds_candidates": len(all_hits) > 0,
            "premise_specialization_expands_access": (
                transfer_reason_counts["premise_specialization"] > 0
            ),
        },
    }

    print(json.dumps(result, indent=2, sort_keys=True))
    out = Path("results/equational-global-theory-transfer-v1.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
