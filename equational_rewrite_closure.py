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
MAX_NODES_PER_SIDE = 5000
MAX_APPS = 20


def _download():
    request = urllib.request.Request(
        ARCHIVE_URL,
        headers={"User-Agent": "RealityGraph/1.0 verified rewrite consequence"},
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
        name = pattern[1]
        old = subst.get(name)
        if old is None:
            subst[name] = target
            return True
        return old == target
    if target[0] != "*":
        return False
    return _match(pattern[1], target[1], subst) and _match(pattern[2], target[2], subst)


def _instantiate(node, subst):
    if node[0] == "v":
        if node[1] not in subst:
            raise KeyError(node[1])
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
    if node[0] != "*":
        raise ValueError("position descends through variable")
    head, *tail = position
    tail = tuple(tail)
    if head == 0:
        return ("*", _replace(node[1], tail, replacement), node[2])
    return ("*", node[1], _replace(node[2], tail, replacement))


def _text(node):
    if node[0] == "v":
        return node[1]
    return f"({_text(node[1])} ◇ {_text(node[2])})"


def _one_steps(node, law_lhs, law_rhs):
    out = []
    seen = set()
    directions = [
        ("forward", law_lhs, law_rhs),
        ("reverse", law_rhs, law_lhs),
    ]
    for position, subterm in _positions(node):
        for orientation, pattern, replacement_pattern in directions:
            # Sound deterministic rewriting requires every replacement variable
            # to be bound by the matched side.
            if not _vars(replacement_pattern) <= _vars(pattern):
                continue
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


def _reachable(start, law_lhs, law_rhs):
    parent = {start: None}
    step = {}
    depth = {start: 0}
    queue = deque([start])
    while queue and len(parent) < MAX_NODES_PER_SIDE:
        node = queue.popleft()
        if depth[node] >= MAX_DEPTH:
            continue
        for nxt, info in _one_steps(node, law_lhs, law_rhs):
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


def _rewrite_proof(target_lhs, target_rhs, law_lhs, law_rhs):
    left_parent, left_step, left_depth = _reachable(target_lhs, law_lhs, law_rhs)
    right_parent, right_step, right_depth = _reachable(target_rhs, law_lhs, law_rhs)
    common = set(left_parent) & set(right_parent)
    if not common:
        return None
    meet = min(
        common,
        key=lambda node: (
            left_depth[node] + right_depth[node],
            _apps(node),
            _text(node),
        ),
    )
    return {
        "meeting_term": _text(meet),
        "left_steps": _path_to(meet, left_parent, left_step),
        # This path is from target RHS to meeting term; reverse it to prove
        # meeting = target RHS.
        "right_steps_from_target": _path_to(meet, right_parent, right_step),
        "total_steps": left_depth[meet] + right_depth[meet],
        "left_reachable": len(left_parent),
        "right_reachable": len(right_parent),
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
        if _verdict(proof.decode("utf-8", errors="replace")) == "true":
            true_by_source[int(row["eq1_id"])].append(donor_id)

    hits = {}
    donor_attempts = 0
    bounded_explorations = 0
    for problem_id in current:
        row = rows_by_id[problem_id]
        target_lhs, target_rhs = _parse_equation(str(row["equation2"]))
        for donor_id in true_by_source.get(int(row["eq1_id"]), ()):
            donor_attempts += 1
            donor_row = rows_by_id[donor_id]
            law_lhs, law_rhs = _parse_equation(str(donor_row["equation2"]))
            proof = _rewrite_proof(target_lhs, target_rhs, law_lhs, law_rhs)
            bounded_explorations += 1
            if proof is None or proof["total_steps"] == 0:
                continue
            hits[problem_id] = {
                "donor_id": donor_id,
                "derived_equation_id": int(donor_row["eq2_id"]),
                "target_equation_id": int(row["eq2_id"]),
                **proof,
            }
            break

    result = {
        "experiment": "realitygraph-single-derived-law-rewrite-closure-v1",
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
            "same_premise_donor_attempts": donor_attempts,
            "bounded_rewrite_explorations": bounded_explorations,
            "new_rewrite_proofs": len(hits),
            "hits": hits,
        },
        "signal": {
            "repeated_contextual_use_adds_new_proofs": len(hits) > 0,
        },
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    out = Path("results/equational-rewrite-closure-v1.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
