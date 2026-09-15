from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from collections import defaultdict, deque
from pathlib import Path

from equational_residual_demo import _Parser, _read_corpus
from equational_transition_demo import _archive_files

COMMIT = "bed33e36c33fca139d902addd8cb77cd4172fe64"
ARCHIVE_URL = f"https://codeload.github.com/YanbiaoLab/equational-challenges/tar.gz/{COMMIT}"
EXPECTED_ARCHIVE_SHA256 = "284b45196a9e8a31f1bd3aeb05040c451a615fed2ca8ba724d7a14a833e842eb"
RETAINED = {"17195_to_43536", "4922_to_4158", "4922_to_4258"}
MAX_DEPTH = 4
MAX_NODES_PER_SIDE = 12000
MAX_APPS = 22


def _download():
    request = urllib.request.Request(
        ARCHIVE_URL,
        headers={"User-Agent": "RealityGraph/1.0 multi-law verified rewrite"},
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        raw = response.read()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != EXPECTED_ARCHIVE_SHA256:
        raise ValueError(f"archive hash mismatch: {digest}")
    return raw


def _verdict(text):
    match = re.search(r"-- Recorded verdict:\s*(true|false)", text)
    return None if match is None else match.group(1)


def _parse_equation(formula):
    lhs, rhs = [part.strip() for part in formula.split("=", 1)]
    return _Parser(lhs).parse(), _Parser(rhs).parse()


def _vars(node):
    if node[0] == "v":
        return {node[1]}
    return _vars(node[1]) | _vars(node[2])


def _apps(node):
    if node[0] == "v":
        return 0
    return 1 + _apps(node[1]) + _apps(node[2])


def _match(pattern, target, subst):
    if pattern[0] == "v":
        old = subst.get(pattern[1])
        if old is None:
            subst[pattern[1]] = target
            return True
        return old == target
    if target[0] != "*":
        return False
    return _match(pattern[1], target[1], subst) and _match(pattern[2], target[2], subst)


def _instantiate(node, subst):
    if node[0] == "v":
        return subst[node[1]]
    return ("*", _instantiate(node[1], subst), _instantiate(node[2], subst))


def _positions(node, prefix=()):
    yield prefix, node
    if node[0] == "*":
        yield from _positions(node[1], prefix + (0,))
        yield from _positions(node[2], prefix + (1,))


def _replace(node, position, replacement):
    if not position:
        return replacement
    head, *tail = position
    tail = tuple(tail)
    if head == 0:
        return ("*", _replace(node[1], tail, replacement), node[2])
    return ("*", node[1], _replace(node[2], tail, replacement))


def _text(node):
    if node[0] == "v":
        return node[1]
    return f"({_text(node[1])} ◇ {_text(node[2])})"


def _one_steps(node, laws):
    out = []
    seen = set()
    for donor_id, law_lhs, law_rhs in laws:
        for orientation, pattern, replacement_pattern in (
            ("forward", law_lhs, law_rhs),
            ("reverse", law_rhs, law_lhs),
        ):
            if not _vars(replacement_pattern) <= _vars(pattern):
                continue
            for position, subterm in _positions(node):
                subst = {}
                if not _match(pattern, subterm, subst):
                    continue
                replacement = _instantiate(replacement_pattern, subst)
                candidate = _replace(node, position, replacement)
                if candidate == node or _apps(candidate) > MAX_APPS or candidate in seen:
                    continue
                seen.add(candidate)
                out.append(
                    (
                        candidate,
                        {
                            "donor_id": donor_id,
                            "orientation": orientation,
                            "position": list(position),
                            "substitution": {
                                name: _text(term) for name, term in sorted(subst.items())
                            },
                            "before": _text(node),
                            "after": _text(candidate),
                        },
                    )
                )
    return out


def _reachable(start, laws):
    parent = {start: None}
    step = {}
    depth = {start: 0}
    queue = deque([start])
    while queue and len(parent) < MAX_NODES_PER_SIDE:
        node = queue.popleft()
        if depth[node] >= MAX_DEPTH:
            continue
        for nxt, info in _one_steps(node, laws):
            if nxt in parent:
                continue
            parent[nxt] = node
            step[nxt] = info
            depth[nxt] = depth[node] + 1
            queue.append(nxt)
            if len(parent) >= MAX_NODES_PER_SIDE:
                break
    return parent, step, depth


def _path_to(node, parent, step):
    items = []
    cur = node
    while parent[cur] is not None:
        items.append(step[cur])
        cur = parent[cur]
    items.reverse()
    return items


def _prove(lhs, rhs, laws):
    lp, ls, ld = _reachable(lhs, laws)
    rp, rs, rd = _reachable(rhs, laws)
    common = set(lp) & set(rp)
    if not common:
        return None
    meet = min(
        common,
        key=lambda node: (
            ld[node] + rd[node],
            len({
                item["donor_id"]
                for item in _path_to(node, lp, ls) + _path_to(node, rp, rs)
            }),
            _apps(node),
            _text(node),
        ),
    )
    left_steps = _path_to(meet, lp, ls)
    right_steps = _path_to(meet, rp, rs)
    donors = sorted({step["donor_id"] for step in left_steps + right_steps})
    return {
        "meeting_term": _text(meet),
        "left_steps": left_steps,
        "right_steps_from_target": right_steps,
        "total_steps": ld[meet] + rd[meet],
        "donors_used": donors,
        "donor_count": len(donors),
        "left_reachable": len(lp),
        "right_reachable": len(rp),
    }


def main():
    raw = _download()
    rows, proofs, _, _, source_hashes, archive_hash = _read_corpus(raw)
    files = _archive_files(raw)
    rows_by_id = {str(row["id"]): row for row in rows}
    current = sorted(set(rows_by_id) - proofs - RETAINED)

    true_by_source = defaultdict(list)
    for donor_id in sorted(proofs):
        row = rows_by_id.get(donor_id)
        proof = files.get(f"proofs/{donor_id}.lean")
        if row is None or proof is None:
            continue
        if _verdict(proof.decode("utf-8", errors="replace")) != "true":
            continue
        lhs, rhs = _parse_equation(str(row["equation2"]))
        true_by_source[int(row["eq1_id"])].append((donor_id, lhs, rhs))

    hits = {}
    attempted = 0
    total_laws_available = 0
    for problem_id in current:
        row = rows_by_id[problem_id]
        laws = true_by_source.get(int(row["eq1_id"]), ())
        if not laws:
            continue
        attempted += 1
        total_laws_available += len(laws)
        lhs, rhs = _parse_equation(str(row["equation2"]))
        proof = _prove(lhs, rhs, laws)
        if proof is None or proof["total_steps"] == 0:
            continue
        hits[problem_id] = {
            "premise_equation_id": int(row["eq1_id"]),
            "target_equation_id": int(row["eq2_id"]),
            "available_donor_count": len(laws),
            **proof,
        }

    result = {
        "experiment": "realitygraph-multi-derived-law-rewrite-closure-v1",
        "upstream": {
            "commit": COMMIT,
            "archive_sha256": archive_hash,
            "dataset_sha256": source_hashes,
            "acquisition": "anonymous pinned codeload archive; no fork/star/watch/upstream write",
        },
        "bounds": {
            "max_rewrite_depth_per_side": MAX_DEPTH,
            "max_nodes_per_side": MAX_NODES_PER_SIDE,
            "max_term_apps": MAX_APPS,
        },
        "current_residual": {
            "input_frontier": len(current),
            "residuals_with_verified_law_bank": attempted,
            "total_laws_available_across_attempts": total_laws_available,
            "new_multi_law_proofs": len(hits),
            "hits": hits,
        },
        "signal": {
            "cooperating_verified_laws_add_new_proofs": len(hits) > 0,
        },
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    out = Path("results/equational-multi-law-rewrite-v1.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
