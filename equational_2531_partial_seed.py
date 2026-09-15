from __future__ import annotations

import itertools
import json
from collections import deque
from pathlib import Path

# We search finite partial H-magmas satisfying exactly the invariant used by
# Q.Greedy.flOK in the historical 2531_to_47 certificate:
#
#   if H(x,y)=xy and H(x,xy)=xxy,
#   then there exists z with H(xxy,y)=z and H(y,z)=x;
#   and H(x,x) != x whenever defined.
#
# The completed total H-model is converted to the target magma D by
# D(a,b) = H(b,a), exactly as in the accepted certificate.

TARGETS = {
    "2531_to_30128": "x = (x ◇ (x ◇ ((x ◇ x) ◇ x))) ◇ x",
    "2531_to_43283": "x ◇ x = x ◇ ((x ◇ x) ◇ (x ◇ x))",
}

MAX_BASE = 5
MAX_ENTRIES = 14
MAX_NEW_VALUES = 6


class Conflict(Exception):
    pass


def put(table, a, b, c):
    old = table.get((a, b))
    if old is not None and old != c:
        raise Conflict((a, b, old, c))
    if a == b and c == a:
        raise Conflict(("idempotent", a))
    table[(a, b)] = c


def closure_obligations(table):
    out = []
    for (x, y), xy in sorted(table.items()):
        xxy = table.get((x, xy))
        if xxy is None:
            continue
        # Need some z with H(xxy,y)=z and H(y,z)=x.
        z = table.get((xxy, y))
        if z is not None and table.get((y, z)) == x:
            continue
        out.append((x, y, xy, xxy, z))
    return out


def normalize(table):
    # Canonical relabeling by first appearance in sorted table triples.
    triples = sorted((a, b, c) for (a, b), c in table.items())
    mapping = {}
    nxt = 0
    def ren(v):
        nonlocal nxt
        if v not in mapping:
            mapping[v] = nxt
            nxt += 1
        return mapping[v]
    normalized = tuple(sorted((ren(a), ren(b), ren(c)) for a, b, c in triples))
    return normalized


def eval_D(expr, x, table):
    # D(a,b)=H(b,a). Expression is represented as nested tuples.
    if expr == "x":
        return x
    left = eval_D(expr[1], x, table)
    right = eval_D(expr[2], x, table)
    return table.get((right, left))


# Target 30128:
#   x = D(D(x, D(x, D(D(x,x),x))), x)
# Target 43283:
#   D(x,x) = D(x, D(D(x,x), D(x,x)))
X = "x"
XX = ("D", X, X)
T301_R = ("D", ("D", X, ("D", X, ("D", XX, X))), X)
T432_L = XX
T432_R = ("D", X, ("D", XX, XX))


def target_value(target, witness_x, table):
    if target == "2531_to_30128":
        rhs = eval_D(T301_R, witness_x, table)
        if rhs is None:
            return None
        return witness_x, rhs
    lhs = eval_D(T432_L, witness_x, table)
    rhs = eval_D(T432_R, witness_x, table)
    if lhs is None or rhs is None:
        return None
    return lhs, rhs


def witness_requirements(target, x, vals):
    # Rather than enumerate all partial tables, enumerate just the intermediate
    # values along the target expression and materialize the required H entries.
    t = {}
    if target == "2531_to_30128":
        # a=D(x,x)=H(x,x)
        # b=D(a,x)=H(x,a)
        # c=D(x,b)=H(b,x)
        # d=D(x,c)=H(c,x)
        # r=D(d,x)=H(x,d), require r != x.
        a,b,c,d,r = vals
        put(t, x, x, a)
        put(t, x, a, b)
        put(t, b, x, c)
        put(t, c, x, d)
        put(t, x, d, r)
        if r == x:
            raise Conflict("target holds")
    else:
        # a=D(x,x)=H(x,x)
        # b=D(a,a)=H(a,a)
        # r=D(x,b)=H(b,x), require r != a.
        a,b,r = vals
        put(t, x, x, a)
        put(t, a, a, b)
        put(t, b, x, r)
        if r == a:
            raise Conflict("target holds")
    return t


def complete_horn(seed):
    # Backtracking completion of only triggered Horn obligations.
    seen = set()
    q = deque([(dict(seed), max([0] + [v for k,c in seed.items() for v in (*k,c)]) + 1)])
    while q:
        table, fresh = q.popleft()
        if len(table) > MAX_ENTRIES or fresh > MAX_BASE + MAX_NEW_VALUES:
            continue
        key = normalize(table)
        if key in seen:
            continue
        seen.add(key)

        obs = closure_obligations(table)
        if not obs:
            return table

        x,y,xy,xxy,z_existing = obs[0]
        choices = []

        if z_existing is not None:
            choices = [z_existing]
        else:
            # Prefer existing small values, then one fresh value.
            values = sorted({0,1,2,3,4} | {v for (a,b),c in table.items() for v in (a,b,c)})
            choices = values[:MAX_BASE + 2] + [fresh]

        for z in choices:
            nt = dict(table)
            try:
                put(nt, xxy, y, z)
                put(nt, y, z, x)
            except Conflict:
                continue
            nfresh = max(fresh, z + 1)
            q.append((nt, nfresh))
    return None


def search_target(target):
    attempts = 0
    conflicts = 0
    completed = 0

    if target == "2531_to_30128":
        arity = 5
    else:
        arity = 3

    for domain_size in range(2, MAX_BASE + 1):
        x = 0
        for vals in itertools.product(range(domain_size), repeat=arity):
            attempts += 1
            try:
                seed = witness_requirements(target, x, vals)
            except Conflict:
                conflicts += 1
                continue
            full = complete_horn(seed)
            if full is None:
                continue
            completed += 1
            tv = target_value(target, x, full)
            if tv is None or tv[0] == tv[1]:
                continue

            triples = sorted((a,b,c) for (a,b),c in full.items())
            # Recheck exact flOK-style invariants.
            functional = len({(a,b) for a,b,c in triples}) == len(triples)
            nonidempotent = all(not (a == b == c) for a,b,c in triples)
            law_ok = not closure_obligations(full)
            if not (functional and nonidempotent and law_ok):
                raise AssertionError("internal invariant mismatch")

            return {
                "target": target,
                "domain_search_size": domain_size,
                "witness_x": x,
                "target_values": {"lhs": tv[0], "rhs": tv[1]},
                "seed_entries": triples,
                "entry_count": len(triples),
                "max_symbol": max(v for triple in triples for v in triple),
                "attempts": attempts,
                "conflicts": conflicts,
                "horn_completed_candidates": completed,
                "invariants": {
                    "functional": functional,
                    "nonidempotent": nonidempotent,
                    "eq1076_partial_horn_closed": law_ok,
                },
            }
    return {
        "target": target,
        "found": False,
        "attempts": attempts,
        "conflicts": conflicts,
        "horn_completed_candidates": completed,
    }


def main():
    results = {target: search_target(target) for target in TARGETS}
    for v in results.values():
        v.setdefault("found", "seed_entries" in v)
    out = {
        "experiment": "realitygraph-2531-partial-seed-synthesis-v1",
        "representation": (
            "finite partial H-magma satisfying the exact Q.Greedy.flOK Horn invariant; "
            "historical completion theorem totalizes it; target magma is opposite H"
        ),
        "results": results,
        "found_count": sum(int(v["found"]) for v in results.values()),
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    p = Path("results/equational-2531-partial-seed-v1.json")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
