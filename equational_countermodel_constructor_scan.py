from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

from equational_residual_demo import _read_corpus
from equational_transition_demo import _archive_files

FINAL_COMMIT = "bed33e36c33fca139d902addd8cb77cd4172fe64"
PRE_WAVE2 = "9ff9cd90d3875e59f213064374764b95f8c2df54"
FINAL_URL = f"https://codeload.github.com/YanbiaoLab/equational-challenges/tar.gz/{FINAL_COMMIT}"
PRE_URL = f"https://codeload.github.com/YanbiaoLab/equational-challenges/tar.gz/{PRE_WAVE2}"
FINAL_SHA = "284b45196a9e8a31f1bd3aeb05040c451a615fed2ca8ba724d7a14a833e842eb"
RETAINED = {
    "17195_to_43536",
    "4922_to_4158",
    "4922_to_4258",
    "22268_to_22436",
}


def _download(url, expected=None):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "RealityGraph/1.0 countermodel-constructor scan"},
    )
    with urllib.request.urlopen(req, timeout=90) as response:
        raw = response.read()
    digest = hashlib.sha256(raw).hexdigest()
    if expected is not None and digest != expected:
        raise ValueError(f"archive hash mismatch: {digest}")
    return raw, digest


def _verdict(text):
    m = re.search(r"-- Recorded verdict:\s*(true|false)", text)
    return None if m is None else m.group(1)


def _classify(text):
    if _verdict(text) == "true":
        return "true"
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


def main():
    final_raw, final_digest = _download(FINAL_URL, FINAL_SHA)
    pre_raw, pre_digest = _download(PRE_URL)
    rows, final_proofs, _, _, source_hashes, archive_hash = _read_corpus(final_raw)
    final_files = _archive_files(final_raw)
    pre_files = _archive_files(pre_raw)

    pre_proofs = {
        Path(path).stem
        for path in pre_files
        if path.startswith("proofs/") and path.endswith(".lean")
    }
    wave2 = sorted(final_proofs - pre_proofs)
    if len(wave2) != 75:
        raise ValueError(f"expected 75 wave2 proofs, got {len(wave2)}")

    rows_by_id = {str(row["id"]): row for row in rows}
    current = sorted(set(rows_by_id) - final_proofs - RETAINED)

    all_false_family = {}
    wave2_family = {}
    family_counts_all = Counter()
    family_counts_wave2 = Counter()
    source_family = defaultdict(Counter)
    examples = defaultdict(list)

    for proof_id in sorted(final_proofs):
        raw = final_files.get(f"proofs/{proof_id}.lean")
        if raw is None:
            continue
        text = raw.decode("utf-8", errors="replace")
        if _verdict(text) != "false":
            continue
        family = _classify(text)
        all_false_family[proof_id] = family
        family_counts_all[family] += 1
        row = rows_by_id.get(proof_id)
        if row is not None:
            source_family[int(row["eq1_id"])][family] += 1
        if len(examples[family]) < 8:
            examples[family].append(proof_id)
        if proof_id in wave2:
            wave2_family[proof_id] = family
            family_counts_wave2[family] += 1

    current_neighbor_counts = Counter()
    current_neighbor_ids = defaultdict(list)
    current_sources_with_false = set()
    for problem_id in current:
        source = int(rows_by_id[problem_id]["eq1_id"])
        fams = source_family.get(source)
        if not fams:
            continue
        current_sources_with_false.add(source)
        for family, count in fams.items():
            current_neighbor_counts[family] += 1
            if len(current_neighbor_ids[family]) < 30:
                current_neighbor_ids[family].append(
                    {
                        "residual_id": problem_id,
                        "source_eq": source,
                        "historical_donors_in_family": count,
                    }
                )

    wave2_source_family = defaultdict(Counter)
    for proof_id, family in wave2_family.items():
        row = rows_by_id[proof_id]
        wave2_source_family[int(row["eq1_id"])][family] += 1

    current_wave2_neighbors = Counter()
    current_wave2_neighbor_ids = defaultdict(list)
    for problem_id in current:
        source = int(rows_by_id[problem_id]["eq1_id"])
        fams = wave2_source_family.get(source)
        if not fams:
            continue
        for family, count in fams.items():
            current_wave2_neighbors[family] += 1
            if len(current_wave2_neighbor_ids[family]) < 30:
                current_wave2_neighbor_ids[family].append(
                    {
                        "residual_id": problem_id,
                        "source_eq": source,
                        "wave2_donors_in_family": count,
                    }
                )

    result = {
        "experiment": "realitygraph-countermodel-constructor-scan-v1",
        "upstream": {
            "final_commit": FINAL_COMMIT,
            "pre_wave2_commit": PRE_WAVE2,
            "final_archive_sha256": final_digest,
            "pre_archive_sha256": pre_digest,
            "dataset_sha256": source_hashes,
            "acquisition": "anonymous pinned codeload archives; no fork/star/watch/upstream write",
        },
        "wave2": {
            "proofs": len(wave2),
            "false_proofs": len(wave2_family),
            "family_counts": dict(family_counts_wave2),
            "family_examples": {
                family: [pid for pid in ids if pid in wave2_family]
                for family, ids in examples.items()
            },
        },
        "all_false": {
            "proofs": len(all_false_family),
            "family_counts": dict(family_counts_all),
            "family_examples": dict(examples),
        },
        "current_567": {
            "residuals": len(current),
            "premise_sources_with_any_false_donor": len(current_sources_with_false),
            "residual_neighbor_counts_by_family": dict(current_neighbor_counts),
            "residual_neighbor_examples": dict(current_neighbor_ids),
            "residual_wave2_neighbor_counts_by_family": dict(current_wave2_neighbors),
            "residual_wave2_neighbor_examples": dict(current_wave2_neighbor_ids),
        },
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    out = Path("results/equational-countermodel-constructor-scan-v1.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
