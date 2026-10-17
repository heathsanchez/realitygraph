"""Independent, finite batch semantics for the frozen CLC/FLASH/MDA v1 fixture.

No imports from RealityGraph; no invocation of its closure or quotient functions.
This is NOT the full CLC semantics or a generic formal proof.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

CAPS = {
    'f': ('X', 'Y', {'x0': 'y0', 'x1': 'y1'}, 2),
    'g': ('Y', 'Z', {'y0': 'z0', 'y1': 'z1'}, 2),
    'alt': ('X', 'Z', {'x0': 'z0', 'x1': 'z1'}, 9),
}
OBSERVATIONS = {
    'p0': {'a': '0', 'b': '0', 'c': '1'},
    'p1': {'a': '0', 'b': '1', 'c': '1'},
    'p0_alt': {'a': '0', 'b': '0', 'c': '1'},
}
STATES = ('a', 'b', 'c')
TARGET = {'x0': 'z0', 'x1': 'z1'}


def batch_state(events: tuple[str, ...]) -> dict[str, object]:
    """Reconstruct from the surviving source events, never incremental state."""
    included: set[str] = set()
    revoked: set[str] = set()
    obstructions: set[str] = set()
    continuations: set[str] = set()
    for event in events:
        what, _, name = event.partition(':')
        if what == 'admit':
            assert name not in included
            included.add(name)
        elif what == 'revoke':
            assert name in included
            revoked.add(name)
        elif what == 'obstruct':
            obstructions.add(name)
        elif what == 'unobstruct':
            assert name in obstructions
            obstructions.remove(name)
        elif what == 'protect':
            assert name not in continuations
            continuations.add(name)
        elif what == 'unprotect':
            assert name in continuations
            continuations.remove(name)
        else:
            raise ValueError('unexpected frozen event ' + event)
    active = included - revoked
    if {'f', 'g'} <= active:
        first = CAPS['f'][2]
        second = CAPS['g'][2]
        h = {x: second[first[x]] for x in TARGET}
        assert h == TARGET
        active.add('h')
    solutions = []
    for cap in sorted(active):
        if cap == 'h':
            typin, typout, table, cost = 'X', 'Z', TARGET, 4
        else:
            typin, typout, table, cost = CAPS[cap]
        if typin == 'X' and typout == 'Z' and all(table.get(x) == y for x, y in TARGET.items()):
            solutions.append((cost, cap))
    solutions.sort()
    signatures = {}
    for s in STATES:
        signatures[s] = tuple(OBSERVATIONS[q][s] for q in sorted(continuations))
    groups = {}
    for s in STATES:
        groups.setdefault(signatures[s], []).append(s)
    classes = tuple(sorted(tuple(group) for group in groups.values()))
    return {
        'active': tuple(sorted(active)),
        'status': 'DISCHARGED' if solutions else 'OPEN',
        'best': solutions[0][1] if solutions else None,
        'all_eligible': tuple(cap for _, cap in solutions),
        'pruned': ('bad',) if 'bad' in obstructions else (),
        'classes': classes,
    }


@dataclass(frozen=True)
class FiniteForm:
    states: tuple[str, ...]
    tests: tuple[str, ...]
    protected: tuple[str, ...]
    outcomes: dict[tuple[str, str], str]

    def validate(self) -> None:
        assert self.protected and set(self.protected) <= set(self.tests)
        assert set(self.outcomes) == {(s, t) for s in self.states for t in self.tests}
        assert set(self.outcomes.values()) <= {'UNKNOWN', 'EQ', 'DIST'}


@dataclass(frozen=True)
class FiniteTransport:
    forward: dict[str, str]
    pull: dict[str, str]
    lift: dict[str, str]


def check_clc_transport(A: FiniteForm, B: FiniteForm, tr: FiniteTransport, *, strict: bool) -> bool:
    """Exhaustively check CLC v1 refinement and protected split for two finite forms."""
    A.validate(); B.validate()
    if set(tr.forward) != set(A.states) or set(tr.pull) != set(B.tests):
        return False
    if set(tr.lift) != set(A.protected):
        return False
    if not set(tr.forward.values()) <= set(B.states):
        return False
    if not set(tr.pull.values()) <= set(A.tests) or not set(tr.lift.values()) <= set(B.protected):
        return False
    if any(tr.pull[t] not in A.protected for t in B.protected):
        return False
    if any(tr.pull[tr.lift[p]] != p for p in A.protected):
        return False
    for s in A.states:
        for t in B.tests:
            pre = A.outcomes[s, tr.pull[t]]
            post = B.outcomes[tr.forward[s], t]
            if strict:
                if pre != post:
                    return False
            else:
                if pre != post and pre != 'UNKNOWN':
                    return False
    return True


def strict_reference() -> tuple[FiniteForm, FiniteForm, FiniteTransport]:
    A = FiniteForm(('0','1'), ('p','constant'), ('p',),
                   {(s, t): ('EQ' if s == '0' else 'DIST') if t == 'p' else 'UNKNOWN'
                    for s in ('0','1') for t in ('p','constant')})
    B = FiniteForm(('alpha','beta'), ('q','constant-b'), ('q',),
                   {(s, t): ('EQ' if s == 'alpha' else 'DIST') if t == 'q' else 'UNKNOWN'
                    for s in ('alpha','beta') for t in ('q','constant-b')})
    return A, B, FiniteTransport({'0':'alpha','1':'beta'}, {'q':'p','constant-b':'constant'}, {'p':'q'})


def refinement_reference() -> tuple[FiniteForm, FiniteForm, FiniteTransport]:
    A = FiniteForm(('0','1'), ('prior',), ('prior',),
                   {(s,'prior'):'UNKNOWN' for s in ('0','1')})
    B = FiniteForm(('alpha','beta'), ('old','new'), ('old',),
                   {(s,t): ('UNKNOWN' if t == 'old' else ('EQ' if s == 'alpha' else 'DIST'))
                    for s in ('alpha','beta') for t in ('old','new')})
    return A, B, FiniteTransport({'0':'alpha','1':'beta'}, {'old':'prior','new':'prior'}, {'prior':'old'})


def witness_spurious_path() -> dict[str, object]:
    """Independent quotient reachability-check negative: spurious two-edge join."""
    vertices = ('a','b0','b1','c')
    arcs = {('a','b0'), ('b1','c')}
    rep = {'a':'a', 'b0':'b', 'b1':'b', 'c':'c'}
    abstract_arcs = {(rep[u],rep[v]) for u,v in arcs}
    assert ('a','b') in abstract_arcs and ('b','c') in abstract_arcs
    # Enumerate original raw paths of length two, do not infer from abstract arcs.
    raw_paths = {(x,z) for x,y in arcs for yy,z in arcs if y == yy}
    abstract_paths = {(x,z) for x,y in abstract_arcs for yy,z in abstract_arcs if y == yy}
    spurious = ('a','c') in abstract_paths and ('a','c') not in {(rep[u],rep[v]) for u,v in raw_paths}
    return {'raw_paths':len(raw_paths), 'abstract_two_hop_paths':len(abstract_paths),
            'spurious_a_to_c':spurious, 'conservative_quotient':not spurious}


def test_reference_contracts() -> dict[str, object]:
    A,B,t = strict_reference()
    assert check_clc_transport(A,B,t,strict=True)
    # Only specific finite checked maps are claimed, not an arbitrary categorical theorem.
    bad_forward = FiniteTransport({'0':'beta','1':'alpha'}, t.pull, t.lift)
    bad_pull = FiniteTransport(t.forward, {'q':'constant','constant-b':'constant'}, t.lift)
    bad_lift = FiniteTransport(t.forward, t.pull, {'p':'constant-b'})
    no_pull = FiniteTransport(t.forward, {'q':'p'}, t.lift)
    bads = [bad_forward,bad_pull,bad_lift,no_pull]
    assert all(not check_clc_transport(A,B,m,strict=True) for m in bads)
    R,S,t2 = refinement_reference()
    assert check_clc_transport(R,S,t2,strict=False)
    assert not check_clc_transport(R,S,t2,strict=True)  # genuinely resolves UNKNOWN
    # No non-constant source test can pull back a protected target test if absent.
    c = witness_spurious_path()
    assert c['spurious_a_to_c'] and not c['conservative_quotient']
    return {'strict_transport':True,'refinement_unknown_to_decisive':True,
            'transport_mutants_rejected':len(bads), 'spurious_path_guard':True}


if __name__ == '__main__':
    print(test_reference_contracts())
