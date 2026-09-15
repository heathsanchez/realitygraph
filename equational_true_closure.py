from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from collections import Counter, defaultdict, deque
from pathlib import Path

from equational_transition_demo import _archive_files
from equational_residual_demo import _read_corpus

COMMIT = "bed33e36c33fca139d902addd8cb77cd4172fe64"
ARCHIVE_URL = f"https://codeload.github.com/YanbiaoLab/equational-challenges/tar.gz/{COMMIT}"
EXPECTED_ARCHIVE_SHA256 = "284b45196a9e8a31f1bd3aeb05040c451a615fed2ca8ba724d7a14a833e842eb"


def _download():
    request = urllib.request.Request(
        ARCHIVE_URL,
        headers={"User-Agent": "RealityGraph/1.0 passive true-consequence closure"},
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


def _shortest_path(adjacency, start, target, max_depth=12):
    if start == target:
        return [start]
    queue = deque([start])
    parent = {start: None}
    depth = {start: 0}
    while queue:
        node = queue.popleft()
        if depth[node] >= max_depth:
            continue
        for nxt in adjacency.get(node, ()):
            if nxt in parent:
                continue
            parent[nxt] = node
            depth[nxt] = depth[node] + 1
            if nxt == target:
                path = [target]
                cur = node
                while cur is not None:
                    path.append(cur)
                    cur = parent[cur]
                return list(reversed(path))
            queue.append(nxt)
    return None


def main():
    raw = _download()
    rows, proofs, _, _, source_hashes, archive_hash = _read_corpus(raw)
    files = _archive_files(raw)
    rows_by_id = {str(row["id"]): row for row in rows}
    current = sorted(set(rows_by_id) - proofs)

    adjacency = defaultdict(set)
    edge_to_proof = {}
    true_edges = 0
    false_edges = 0
    for problem_id in sorted(proofs):
        row = rows_by_id.get(problem_id)
        if row is None:
            continue
        proof = files.get(f"proofs/{problem_id}.lean")
        if proof is None:
            continue
        verdict = _verdict(proof.decode("utf-8", errors="replace"))
        if verdict == "true":
            a = int(row["eq1_id"])
            b = int(row["eq2_id"])
            adjacency[a].add(b)
            edge_to_proof[(a, b)] = problem_id
            true_edges += 1
        elif verdict == "false":
            false_edges += 1

    hits = {}
    path_lengths = Counter()
    source_reach_sizes = {}
    for problem_id in current:
        row = rows_by_id[problem_id]
        start = int(row["eq1_id"])
        target = int(row["eq2_id"])
        path = _shortest_path(adjacency, start, target)
        if path is None or len(path) < 3:
            continue
        edges = []
        for a, b in zip(path, path[1:]):
            proof_id = edge_to_proof.get((a, b))
            if proof_id is None:
                raise ValueError(f"missing proof id for true edge {a}->{b}")
            edges.append(proof_id)
        hits[problem_id] = {
            "equation_path": path,
            "proof_path": edges,
            "length": len(edges),
        }
        path_lengths[len(edges)] += 1

    # Also quantify how much consequence each residual premise already has in the
    # public true graph, even where its requested target is not yet reachable.
    for source in sorted({int(rows_by_id[p]["eq1_id"]) for p in current}):
        seen = {source}
        queue = deque([source])
        while queue:
            node = queue.popleft()
            for nxt in adjacency.get(node, ()):
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
        source_reach_sizes[source] = len(seen) - 1

    result = {
        "experiment": "realitygraph-verified-true-consequence-closure-v1",
        "upstream": {
            "commit": COMMIT,
            "archive_sha256": archive_hash,
            "dataset_sha256": source_hashes,
            "acquisition": "anonymous pinned codeload archive; no fork/star/watch/upstream write",
        },
        "graph": {
            "verified_true_edges": true_edges,
            "verified_false_edges": false_edges,
            "source_nodes": len(adjacency),
            "target_nodes": len({b for targets in adjacency.values() for b in targets}),
        },
        "current_residual": {
            "total": len(current),
            "multi_hop_true_closure_hits": len(hits),
            "path_length_counts": dict(sorted(path_lengths.items())),
            "hits": hits,
            "premise_reachability": {
                "mean": sum(source_reach_sizes.values()) / len(source_reach_sizes)
                if source_reach_sizes else 0.0,
                "max": max(source_reach_sizes.values()) if source_reach_sizes else 0,
                "nonzero_sources": sum(int(v > 0) for v in source_reach_sizes.values()),
                "source_count": len(source_reach_sizes),
            },
        },
        "signal": {
            "verified_transitive_closure_adds_new_proofs": len(hits) > 0,
        },
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    out = Path("results/equational-true-closure-v1.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
