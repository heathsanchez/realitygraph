from __future__ import annotations

import hashlib
import itertools
import json
import re
import urllib.request
from collections import Counter
from pathlib import Path

from equational_residual_demo import _Parser, _read_corpus
from equational_transition_demo import _archive_files

COMMIT = "bed33e36c33fca139d902addd8cb77cd4172fe64"
URL = f"https://codeload.github.com/YanbiaoLab/equational-challenges/tar.gz/{COMMIT}"
EXPECTED_SHA = "284b45196a9e8a31f1bd3aeb05040c451a615fed2ca8ba724d7a14a833e842eb"
DONOR = "9448_to_15219"
RETAINED = {
    "17195_to_43536",
    "4922_to_4158",
    "4922_to_4258",
    "22268_to_22436",
    "22505_to_40367",
}


def _download():
    req = urllib.request.Request(
        URL,
        headers={"User-Agent": "RealityGraph/1.0 compiled-zmod-constructor"},
    )
    with urllib.request.urlopen(req, timeout=90) as response:
        raw = response.read()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != EXPECTED_SHA:
        raise ValueError(f"archive hash mismatch: {digest}")
    return raw


def _extract_h(text):
    start = text.index("def h (a c : F) : K :=")
    end = text.index("\ndef op", start)
    body = text[start:end]
    table = {(a, c): 0 for a in range(11) for c in range(11)}
    for a, c, value in re.findall(r"\|\s*(\d+),\s*(\d+)\s*=>\s*(\d+)", body):
        table[(int(a), int(c))] = int(value) % 7
    return table


def _parse_identity(formula):
    lhs_text, rhs_text = [part.strip() for part in formula.split("=", 1)]
    lhs = _Parser(lhs_text).parse()
    rhs = _Parser(rhs_text).parse()
    variables = tuple(sorted(set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", formula))))
    return lhs, rhs, variables


def _op(x, y, h):
    return (
        (9 * x[0] + 4 * y[0]) % 11,
        (4 * x[1] + 4 * y[1] + h[(x[0], y[0])]) % 7,
    )


def _eval(node, env, h):
    if node[0] == "v":
        return env[node[1]]
    return _op(_eval(node[1], env, h), _eval(node[2], env, h), h)


CARRIER = tuple((a, b) for a in range(11) for b in range(7))


def _holds(identity, h):
    lhs, rhs, variables = identity
    for values in itertools.product(CARRIER, repeat=len(variables)):
        env = dict(zip(variables, values))
        if _eval(lhs, env, h) != _eval(rhs, env, h):
            return False
    return True


def _failure(identity, h):
    lhs, rhs, variables = identity
    checked = 0
    for values in itertools.product(CARRIER, repeat=len(variables)):
        checked += 1
        env = dict(zip(variables, values))
        lv = _eval(lhs, env, h)
        rv = _eval(rhs, env, h)
        if lv != rv:
            return {"assignment": env, "lhs": lv, "rhs": rv, "checked": checked}
    return None


def main():
    raw = _download()
    rows, proofs, _, _, source_hashes, archive_hash = _read_corpus(raw)
    files = _archive_files(raw)
    rows_by_id = {str(row["id"]): row for row in rows}
    current = sorted(set(rows_by_id) - proofs - RETAINED)

    donor_text = files[f"proofs/{DONOR}.lean"].decode("utf-8", errors="replace")
    h = _extract_h(donor_text)

    parsed = {}
    def identities(problem_id):
        if problem_id not in parsed:
            row = rows_by_id[problem_id]
            parsed[problem_id] = (
                _parse_identity(str(row["equation1"])),
                _parse_identity(str(row["equation2"])),
            )
        return parsed[problem_id]

    # This model is expensive for 4-variable source laws (77^4), so first route
    # using the historically verified donor premise and exact same-premise
    # residuals. Then test additional sources only when they have at most 2 vars.
    donor_source = int(rows_by_id[DONOR]["eq1_id"])
    hits = {}
    source_checks = 0
    source_holds = 0
    target_checks = 0
    skipped_high_arity = 0

    for problem_id in current:
        source, target = identities(problem_id)
        source_eq = int(rows_by_id[problem_id]["eq1_id"])
        if source_eq == donor_source:
            source_ok = True
        elif len(source[2]) <= 2:
            source_checks += 1
            source_ok = _holds(source, h)
        else:
            skipped_high_arity += 1
            continue
        if not source_ok:
            continue
        source_holds += 1
        target_checks += 1
        witness = _failure(target, h)
        if witness is not None:
            hits[problem_id] = {
                "donor_id": DONOR,
                "carrier_order": 77,
                "target_witness": witness,
                "source_reason": (
                    "same_verified_premise"
                    if source_eq == donor_source
                    else "direct_exhaustive_source_check"
                ),
            }

    result = {
        "experiment": "realitygraph-compiled-zmod77-replay-v1",
        "upstream": {
            "commit": COMMIT,
            "archive_sha256": archive_hash,
            "dataset_sha256": source_hashes,
            "donor": DONOR,
            "acquisition": "anonymous pinned codeload archive; no fork/star/watch/upstream write",
        },
        "model": {
            "carrier": "ZMod 11 × ZMod 7",
            "order": 77,
            "h_entries_explicit": sum(int(v != 0) for v in h.values()),
        },
        "replay": {
            "input_frontier": len(current),
            "source_checks": source_checks,
            "source_holding_transfers": source_holds,
            "target_checks": target_checks,
            "skipped_high_arity_sources": skipped_high_arity,
            "new_exact_hits": len(hits),
            "hits": hits,
            "frontier_if_verified": len(current) - len(hits),
            "new_model_search": 0,
        },
        "signal": {
            "compiled_structured_model_adds_consequences": len(hits) > 0,
        },
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    out = Path("results/equational-zmod77-replay-v1.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
