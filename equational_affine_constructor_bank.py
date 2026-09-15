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
        headers={"User-Agent": "RealityGraph/1.0 affine-constructor-bank"},
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


def _linear_form(node, variables, n, a, b, c):
    width = len(variables)
    index = {name: i for i, name in enumerate(variables)}

    def rec(term):
        if term[0] == "v":
            coeffs = [0] * width
            coeffs[index[term[1]]] = 1
            return coeffs, 0
        lc, lk = rec(term[1])
        rc, rk = rec(term[2])
        coeffs = [
            (a * x + b * y) % n
            for x, y in zip(lc, rc)
        ]
        const = (a * lk + b * rk + c) % n
        return coeffs, const

    return rec(node)


def _difference(identity, n, a, b, c):
    lhs, rhs, variables = identity
    lc, lk = _linear_form(lhs, variables, n, a, b, c)
    rc, rk = _linear_form(rhs, variables, n, a, b, c)
    coeffs = tuple((x - y) % n for x, y in zip(lc, rc))
    const = (lk - rk) % n
    return variables, coeffs, const


def _holds(identity, n, a, b, c):
    _, coeffs, const = _difference(identity, n, a, b, c)
    return const == 0 and all(value == 0 for value in coeffs)


def _eval_term(node, env, n, a, b, c):
    if node[0] == "v":
        return env[node[1]]
    x = _eval_term(node[1], env, n, a, b, c)
    y = _eval_term(node[2], env, n, a, b, c)
    return (a * x + b * y + c) % n


def _failure(identity, n, a, b, c):
    lhs, rhs, variables = identity
    _, coeffs, const = _difference(identity, n, a, b, c)
    if const == 0 and all(value == 0 for value in coeffs):
        return None
    env = {name: 0 for name in variables}
    if const == 0:
        for name, coeff in zip(variables, coeffs):
            if coeff != 0:
                env[name] = 1
                break
    lv = _eval_term(lhs, env, n, a, b, c)
    rv = _eval_term(rhs, env, n, a, b, c)
    if lv == rv:
        raise AssertionError("symbolic affine witness construction failed")
    return {
        "assignment": env,
        "lhs": lv,
        "rhs": rv,
        "coefficient_difference": dict(zip(variables, coeffs)),
        "constant_difference": const,
    }


def main():
    raw = _download()
    rows, proofs, _, _, source_hashes, archive_hash = _read_corpus(raw)
    files = _archive_files(raw)
    rows_by_id = {str(row["id"]): row for row in rows}
    current = sorted(set(rows_by_id) - proofs - RETAINED)

    models = {}
    model_donors = {}
    patterns = [
        re.compile(r"affineOp_(\d+)_(\d+)_(\d+)_(\d+)"),
        re.compile(
            r"def\s+\w+\s*\(i j : Fin (\d+)\)\s*:\s*Fin \1\s*:=\s*"
            r"⟨\((\d+)\s*\*\s*i\.val\s*\+\s*(\d+)\s*\*\s*j\.val\s*\+\s*(\d+)\)\s*%\s*\1",
            re.DOTALL,
        ),
    ]
    for proof_id in sorted(proofs):
        proof = files.get(f"proofs/{proof_id}.lean")
        if proof is None:
            continue
        text = proof.decode("utf-8", errors="replace")
        if _verdict(text) != "false":
            continue
        found = None
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                found = tuple(int(x) for x in match.groups())
                break
        if found is None:
            continue
        n, a, b, c = found
        key = (n, a % n, b % n, c % n)
        models[key] = key
        model_donors.setdefault(key, []).append(proof_id)

    parsed = {}
    def identities(problem_id):
        if problem_id not in parsed:
            row = rows_by_id[problem_id]
            parsed[problem_id] = (
                _parse_identity(str(row["equation1"])),
                _parse_identity(str(row["equation2"])),
            )
        return parsed[problem_id]

    source_cache = {}
    hits = {}
    tests = 0
    source_holds = 0
    target_checks = 0
    order_counts = Counter()

    for problem_id in current:
        source, target = identities(problem_id)
        source_eq = int(rows_by_id[problem_id]["eq1_id"])
        for key in sorted(models):
            n, a, b, c = key
            tests += 1
            cache_key = (source_eq, key)
            source_ok = source_cache.get(cache_key)
            if source_ok is None:
                source_ok = _holds(source, n, a, b, c)
                source_cache[cache_key] = source_ok
            if not source_ok:
                continue
            source_holds += 1
            target_checks += 1
            witness = _failure(target, n, a, b, c)
            if witness is None:
                continue
            hits[problem_id] = {
                "model": {"n": n, "a": a, "b": b, "c": c},
                "historical_donors": model_donors[key][:20],
                "target_witness": witness,
            }
            order_counts[n] += 1
            break

    result = {
        "experiment": "realitygraph-affine-constructor-bank-v1",
        "upstream": {
            "commit": COMMIT,
            "archive_sha256": archive_hash,
            "dataset_sha256": source_hashes,
            "acquisition": "anonymous pinned codeload archive; no fork/star/watch/upstream write",
        },
        "bank": {
            "unique_affine_models": len(models),
            "historical_certificates": sum(len(v) for v in model_donors.values()),
            "models": [
                {"n": k[0], "a": k[1], "b": k[2], "c": k[3], "donors": model_donors[k][:8]}
                for k in sorted(models)
            ],
        },
        "replay": {
            "input_frontier": len(current),
            "candidate_transfers_tested": tests,
            "unique_source_model_checks": len(source_cache),
            "source_holding_transfers": source_holds,
            "target_checks": target_checks,
            "new_exact_hits": len(hits),
            "collapse_by_order": dict(sorted(order_counts.items())),
            "hits": hits,
            "frontier_if_verified": len(current) - len(hits),
            "new_model_search": 0,
        },
        "signal": {
            "compiled_affine_family_adds_consequences": len(hits) > 0,
        },
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    out = Path("results/equational-affine-constructor-bank-v1.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
