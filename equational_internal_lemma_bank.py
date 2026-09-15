from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from collections import Counter, defaultdict, deque
from pathlib import Path

from equational_residual_demo import _Parser, _read_corpus
from equational_transition_demo import _archive_files

COMMIT = "bed33e36c33fca139d902addd8cb77cd4172fe64"
ARCHIVE_URL = f"https://codeload.github.com/YanbiaoLab/equational-challenges/tar.gz/{COMMIT}"
EXPECTED_ARCHIVE_SHA256 = "284b45196a9e8a31f1bd3aeb05040c451a615fed2ca8ba724d7a14a833e842eb"
RETAINED = {"17195_to_43536", "4922_to_4158", "4922_to_4258"}

MAX_LEMMA_APPS_FOR_REWRITE = 18
MAX_TARGET_APPS = 24
MAX_REWRITE_DEPTH = 3
MAX_NODES_PER_SIDE = 8000


def _download():
    request = urllib.request.Request(
        ARCHIVE_URL,
        headers={"User-Agent": "RealityGraph/1.0 internal-lemma compilation"},
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


def _apps(node):
    if node[0] == "v":
        return 0
    return 1 + _apps(node[1]) + _apps(node[2])


def _vars(node):
    if node[0] == "v":
        return {node[1]}
    return _vars(node[1]) | _vars(node[2])


def _text(node):
    if node[0] == "v":
        return node[1]
    return f"({_text(node[1])} ◇ {_text(node[2])})"


def _strip_outer_parens(text: str) -> str:
    text = text.strip()
    while text.startswith("(") and text.endswith(")"):
        depth = 0
        wraps = True
        for i, ch in enumerate(text):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0 and i != len(text) - 1:
                    wraps = False
                    break
        if not wraps or depth != 0:
            break
        text = text[1:-1].strip()
    return text


def _split_top_level_eq(text: str):
    depth = 0
    pos = None
    for i, ch in enumerate(text):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "=" and depth == 0:
            if pos is not None:
                return None
            pos = i
    if pos is None:
        return None
    return text[:pos].strip(), text[pos + 1 :].strip()


def _consume_forall(prop: str):
    prop = prop.strip()
    if not prop.startswith("∀"):
        return None
    i = 1
    depth = 0
    comma = None
    while i < len(prop):
        ch = prop[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "," and depth == 0:
            comma = i
            break
        i += 1
    if comma is None:
        return None
    binder = prop[1:comma].strip()
    body = prop[comma + 1 :].strip()

    names = []
    # Accept only explicit parenthesized G-binders, e.g. (x y z:G) (w:G).
    for group in re.findall(r"\(([^()]*)\)", binder):
        if ":" not in group:
            return None
        left, ty = group.rsplit(":", 1)
        if ty.strip() != "G":
            return None
        for name in left.split():
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
                return None
            names.append(name)
    if not names:
        return None
    # Ensure binder contains nothing except the groups and whitespace.
    residue = re.sub(r"\([^()]*\)", "", binder).strip()
    if residue:
        return None
    return tuple(names), body


def _extract_internal_equalities(text: str):
    raw_types = re.findall(
        r"\bhave\s+([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*?)\s*:=\s*by\b",
        text,
        flags=re.DOTALL,
    )
    out = []
    rejected = Counter()
    seen = set()
    for name, prop in raw_types:
        consumed = _consume_forall(prop)
        if consumed is None:
            rejected["not_closed_forall_G"] += 1
            continue
        bound, body = consumed
        body = _strip_outer_parens(body)
        # Strict grammar: magma terms and one top-level equality only.
        if re.search(r"[^A-Za-z0-9_◇*()=\s]", body):
            rejected["outside_term_grammar"] += 1
            continue
        split = _split_top_level_eq(body)
        if split is None:
            rejected["not_single_equality"] += 1
            continue
        lhs_text, rhs_text = split
        try:
            lhs = _Parser(lhs_text).parse()
            rhs = _Parser(rhs_text).parse()
        except Exception:
            rejected["parse_failure"] += 1
            continue
        used = _vars(lhs) | _vars(rhs)
        if not used <= set(bound):
            rejected["free_local_variable"] += 1
            continue
        key = (lhs, rhs)
        if key in seen:
            rejected["duplicate_within_certificate"] += 1
            continue
        seen.add(key)
        out.append(
            {
                "name": name,
                "bound": list(bound),
                "lhs": lhs,
                "rhs": rhs,
                "lhs_text": _text(lhs),
                "rhs_text": _text(rhs),
                "apps": max(_apps(lhs), _apps(rhs)),
            }
        )
    return out, rejected


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
        return subst[node[1]]
    return ("*", _instantiate(node[1], subst), _instantiate(node[2], subst))


def _specializes(general_lhs, general_rhs, target_lhs, target_rhs):
    for orientation, pair in (
        ("direct", (target_lhs, target_rhs)),
        ("symmetric", (target_rhs, target_lhs)),
    ):
        subst = {}
        if _match(general_lhs, pair[0], subst) and _match(general_rhs, pair[1], subst):
            return {
                "orientation": orientation,
                "substitution": {
                    name: _text(term) for name, term in sorted(subst.items())
                },
            }
    return None


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


def _one_steps(node, laws):
    out = []
    seen = set()
    for law in laws:
        for orientation, pattern, replacement_pattern in (
            ("forward", law["lhs"], law["rhs"]),
            ("reverse", law["rhs"], law["lhs"]),
        ):
            # Deterministic substitution only; variables introduced solely by
            # the replacement side would require fresh search.
            if not _vars(replacement_pattern) <= _vars(pattern):
                continue
            for position, subterm in _positions(node):
                subst = {}
                if not _match(pattern, subterm, subst):
                    continue
                replacement = _instantiate(replacement_pattern, subst)
                candidate = _replace(node, position, replacement)
                if candidate == node or _apps(candidate) > MAX_TARGET_APPS or candidate in seen:
                    continue
                seen.add(candidate)
                out.append(
                    (
                        candidate,
                        {
                            "donor_id": law["donor_id"],
                            "lemma_name": law["lemma_name"],
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
        if depth[node] >= MAX_REWRITE_DEPTH:
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


def _rewrite_proof(lhs, rhs, laws):
    lp, ls, ld = _reachable(lhs, laws)
    rp, rs, rd = _reachable(rhs, laws)
    common = set(lp) & set(rp)
    if not common:
        return None
    meet = min(
        common,
        key=lambda node: (
            ld[node] + rd[node],
            _apps(node),
            _text(node),
        ),
    )
    if ld[meet] + rd[meet] == 0:
        return None
    return {
        "meeting_term": _text(meet),
        "left_steps": _path_to(meet, lp, ls),
        "right_steps_from_target": _path_to(meet, rp, rs),
        "total_steps": ld[meet] + rd[meet],
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
        if _verdict(proof.decode("utf-8", errors="replace")) == "true":
            true_by_source[int(row["eq1_id"])].append(donor_id)

    relevant_sources = {
        int(rows_by_id[problem_id]["eq1_id"])
        for problem_id in current
        if true_by_source.get(int(rows_by_id[problem_id]["eq1_id"]))
    }
    relevant_donors = sorted(
        {
            donor
            for source in relevant_sources
            for donor in true_by_source[source]
        }
    )

    lemma_bank_by_source = defaultdict(list)
    extraction_rejections = Counter()
    certificate_counts = {}
    structural_seen_by_source = defaultdict(set)
    total_raw_lemmas = 0
    total_unique_lemmas = 0

    for donor_id in relevant_donors:
        row = rows_by_id[donor_id]
        text = files[f"proofs/{donor_id}.lean"].decode("utf-8", errors="replace")
        lemmas, rejected = _extract_internal_equalities(text)
        extraction_rejections.update(rejected)
        total_raw_lemmas += len(lemmas)

        # Final published consequence is also a verified reusable law.
        final_lhs, final_rhs = _parse_equation(str(row["equation2"]))
        lemmas.append(
            {
                "name": "published_conclusion",
                "bound": [],
                "lhs": final_lhs,
                "rhs": final_rhs,
                "lhs_text": _text(final_lhs),
                "rhs_text": _text(final_rhs),
                "apps": max(_apps(final_lhs), _apps(final_rhs)),
            }
        )
        source = int(row["eq1_id"])
        admitted = 0
        for lemma in lemmas:
            key = (lemma["lhs"], lemma["rhs"])
            symmetric_key = (lemma["rhs"], lemma["lhs"])
            if key in structural_seen_by_source[source] or symmetric_key in structural_seen_by_source[source]:
                continue
            structural_seen_by_source[source].add(key)
            lemma_bank_by_source[source].append(
                {
                    "donor_id": donor_id,
                    "lemma_name": lemma["name"],
                    **lemma,
                }
            )
            total_unique_lemmas += 1
            admitted += 1
        certificate_counts[donor_id] = admitted

    specialization_hits = {}
    rewrite_hits = {}
    target_count = 0
    specialization_checks = 0
    rewrite_law_counts = {}

    for problem_id in current:
        row = rows_by_id[problem_id]
        source = int(row["eq1_id"])
        laws = lemma_bank_by_source.get(source, ())
        if not laws:
            continue
        target_count += 1
        target_lhs, target_rhs = _parse_equation(str(row["equation2"]))

        for law in laws:
            specialization_checks += 1
            match = _specializes(
                law["lhs"], law["rhs"], target_lhs, target_rhs
            )
            if match is not None:
                specialization_hits[problem_id] = {
                    "donor_id": law["donor_id"],
                    "lemma_name": law["lemma_name"],
                    "lemma": f'{law["lhs_text"]} = {law["rhs_text"]}',
                    **match,
                }
                break

        if problem_id in specialization_hits:
            continue

        rewrite_laws = [
            law for law in laws if law["apps"] <= MAX_LEMMA_APPS_FOR_REWRITE
        ]
        rewrite_law_counts[problem_id] = len(rewrite_laws)
        if not rewrite_laws:
            continue
        proof = _rewrite_proof(target_lhs, target_rhs, rewrite_laws)
        if proof is not None:
            rewrite_hits[problem_id] = {
                "available_internal_laws": len(laws),
                "rewrite_eligible_laws": len(rewrite_laws),
                **proof,
            }

    all_hits = dict(specialization_hits)
    for problem_id, hit in rewrite_hits.items():
        all_hits.setdefault(problem_id, hit)

    result = {
        "experiment": "realitygraph-internal-lemma-bank-v1",
        "upstream": {
            "commit": COMMIT,
            "archive_sha256": archive_hash,
            "dataset_sha256": source_hashes,
            "acquisition": "anonymous pinned codeload archive; no fork/star/watch/upstream write",
        },
        "scope": {
            "input_frontier": len(current),
            "current_residuals_with_true_donor": target_count,
            "relevant_premise_equations": len(relevant_sources),
            "relevant_true_certificates": len(relevant_donors),
        },
        "bank": {
            "raw_closed_internal_lemmas": total_raw_lemmas,
            "unique_verified_laws_including_published": total_unique_lemmas,
            "laws_by_premise": {
                str(source): len(laws)
                for source, laws in sorted(lemma_bank_by_source.items())
            },
            "certificate_admitted_counts": certificate_counts,
            "extraction_rejections": dict(extraction_rejections),
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
            "max_lemma_apps_for_rewrite": MAX_LEMMA_APPS_FOR_REWRITE,
            "max_rewrite_depth": MAX_REWRITE_DEPTH,
            "max_nodes_per_side": MAX_NODES_PER_SIDE,
            "max_target_apps": MAX_TARGET_APPS,
        },
        "signal": {
            "internal_verified_lemmas_add_capability": len(all_hits) > 0,
            "internal_lemmas_strictly_exceed_published_only": (
                total_unique_lemmas > len(relevant_donors)
            ),
        },
    }

    print(json.dumps(result, indent=2, sort_keys=True))
    out = Path("results/equational-internal-lemma-bank-v1.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
