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
        headers={"User-Agent": "RealityGraph/1.0 other-countermodel decomposition"},
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


def _coarse_family(text):
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


def _traits(text):
    traits = []
    if "decideFin!" in text:
        traits.append("has_decideFin")
    if re.search(r"\bMagma\s+\(Fin\s+\d+\)", text):
        traits.append("carrier_Fin")
    if re.search(r"\bMagma\s+Bool\b", text):
        traits.append("carrier_Bool")
    if re.search(r"abbrev\s+CM\s*:=", text):
        traits.append("defines_CM")
    if re.search(r"\bSum\b|\bBool\b|\bUnit\b", text):
        traits.append("finite_sum_bool_unit_syntax")
    if re.search(r"\bZMod\b", text):
        traits.append("carrier_ZMod")
    if "Fintype" in text or "Finite" in text:
        traits.append("mentions_finite")
    if re.search(r"\bdecide\b", text):
        traits.append("uses_decide")
    if "Classical.choice" in text or "noncomputable" in text:
        traits.append("noncomputable")
    if re.search(r"\bstructure\b|\binductive\b", text):
        traits.append("custom_structure_or_inductive")
    if re.search(r"\bNat\b|\bInt\b", text):
        traits.append("mentions_nat_int")
    return tuple(traits)


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

    donors = []
    for proof_id in sorted(proofs):
        row = rows_by_id.get(proof_id)
        proof = files.get(f"proofs/{proof_id}.lean")
        if row is None or proof is None:
            continue
        text = proof.decode("utf-8", errors="replace")
        if _verdict(text) != "false" or _coarse_family(text) != "other_countermodel":
            continue
        donors.append(
            {
                "id": proof_id,
                "source": int(row["eq1_id"]),
                "traits": _traits(text),
                "lines": text.count("\n") + 1,
            }
        )

    donor_by_source = defaultdict(list)
    for donor in donors:
        donor_by_source[donor["source"]].append(donor)

    current_sources = sorted({int(rows_by_id[p]["eq1_id"]) for p in current})
    transferable = defaultdict(list)
    checks = 0
    for donor_source, source_donors in donor_by_source.items():
        dl, dr = parsed[donor_source]
        for current_source in current_sources:
            checks += 1
            cl, cr = parsed[current_source]
            match = _specializes(dl, dr, cl, cr)
            if match is None:
                continue
            for donor in source_donors:
                transferable[current_source].append(
                    {
                        **donor,
                        "premise_specialization": match,
                    }
                )

    residual_pairs = []
    trait_residual_counts = Counter()
    trait_pair_counts = Counter()
    unique_donors = set()
    for problem_id in current:
        source = int(rows_by_id[problem_id]["eq1_id"])
        matches = transferable.get(source, ())
        if not matches:
            continue
        for donor in matches:
            unique_donors.add(donor["id"])
            for trait in donor["traits"]:
                trait_pair_counts[trait] += 1
        for trait in {t for donor in matches for t in donor["traits"]}:
            trait_residual_counts[trait] += 1
        residual_pairs.append(
            {
                "residual_id": problem_id,
                "source_eq": source,
                "donors": [
                    {
                        "id": d["id"],
                        "donor_source": d["source"],
                        "traits": list(d["traits"]),
                        "lines": d["lines"],
                        "premise_specialization": d["premise_specialization"],
                    }
                    for d in matches[:12]
                ],
            }
        )

    decidable_pairs = [
        item for item in residual_pairs
        if any("has_decideFin" in d["traits"] for d in item["donors"])
    ]

    result = {
        "experiment": "realitygraph-other-countermodel-decomposition-v1",
        "upstream": {
            "commit": COMMIT,
            "archive_sha256": archive_hash,
            "dataset_sha256": source_hashes,
            "acquisition": "anonymous pinned codeload archive; no fork/star/watch/upstream write",
        },
        "scope": {
            "input_frontier": len(current),
            "other_countermodel_certificates": len(donors),
            "other_countermodel_sources": len(donor_by_source),
            "premise_match_checks": checks,
            "transferable_unique_donors": len(unique_donors),
            "transferable_residuals": len(residual_pairs),
        },
        "traits": {
            "residual_counts": dict(trait_residual_counts),
            "pair_counts": dict(trait_pair_counts),
        },
        "decidable": {
            "residuals_with_has_decideFin_donor": len(decidable_pairs),
            "candidates": decidable_pairs[:120],
        },
        "examples": residual_pairs[:120],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    out = Path("results/equational-other-countermodel-decomposition-v1.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
