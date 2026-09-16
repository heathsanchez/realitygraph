"""Exact finite NAND-DAG support quotients used by the P-vs-NP spike."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, combinations_with_replacement, product
from typing import Iterable


Support = frozenset[int]
SupportFamilies = dict[int, tuple[Support, ...]]
_ENUMERATION_CALLS = 0


def input_masks(n: int) -> tuple[int, ...]:
    rows = 1 << n
    return tuple(
        sum(((row >> variable) & 1) << row for row in range(rows))
        for variable in range(n)
    )


def nand(left: int, right: int, n: int) -> int:
    return (~(left & right)) & ((1 << (1 << n)) - 1)


@dataclass(frozen=True)
class StateEnumeration:
    n: int
    max_gates: int
    layers: tuple[tuple[frozenset[int], ...], ...]
    min_size: dict[int, int]

    @property
    def inputs(self) -> frozenset[int]:
        return frozenset(input_masks(self.n))

    @property
    def cumulative_state_count(self) -> int:
        return sum(len(layer) for layer in self.layers)


def enumerate_available_states(n: int, max_gates: int) -> StateEnumeration:
    global _ENUMERATION_CALLS
    _ENUMERATION_CALLS += 1
    inputs = frozenset(input_masks(n))
    states = {inputs}
    layers: list[tuple[frozenset[int], ...]] = [(inputs,)]
    minima = {mask: 0 for mask in inputs}
    for size in range(1, max_gates + 1):
        next_states: set[frozenset[int]] = set()
        for available in states:
            for left, right in combinations_with_replacement(sorted(available), 2):
                output = nand(left, right, n)
                if output in available:
                    continue
                child = available | {output}
                next_states.add(child)
                minima.setdefault(output, size)
        states = next_states
        layers.append(tuple(sorted(states, key=lambda row: tuple(sorted(row)))))
    return StateEnumeration(n, max_gates, tuple(layers), minima)


def enumeration_call_count() -> int:
    return _ENUMERATION_CALLS


def joint_cost_from_states(
    enumeration: StateEnumeration, functions: Iterable[int]
) -> int | None:
    required = frozenset(functions)
    for size, layer in enumerate(enumeration.layers):
        if any(required <= state for state in layer):
            return size
    return None


def _insert_minimal(family: set[Support], candidate: Support) -> bool:
    if any(existing <= candidate for existing in family):
        return False
    supersets = {existing for existing in family if candidate < existing}
    family.difference_update(supersets)
    family.add(candidate)
    return True


def provenance_antichains(n: int, max_gates: int) -> SupportFamilies:
    """Least fixed point of minimal semantic gate-output supports.

    A support records non-input behaviours, not syntax, gate order, or wire IDs.
    The size cap makes this finite and is sufficient for all consequences up to
    ``max_gates`` gates.
    """

    inputs = frozenset(input_masks(n))
    families: dict[int, set[Support]] = {mask: {frozenset()} for mask in inputs}
    changed = True
    while changed:
        changed = False
        functions = sorted(families)
        additions: list[tuple[int, Support]] = []
        for left, right in combinations_with_replacement(functions, 2):
            output = nand(left, right, n)
            for left_support, right_support in product(
                tuple(families[left]), tuple(families[right])
            ):
                support = left_support | right_support
                if output not in inputs:
                    support = support | {output}
                if len(support) <= max_gates:
                    additions.append((output, support))
        for output, support in additions:
            family = families.setdefault(output, set())
            if _insert_minimal(family, support):
                changed = True
    return {
        function: tuple(sorted(family, key=lambda support: (len(support), tuple(sorted(support)))))
        for function, family in families.items()
    }


def state_antichains(enumeration: StateEnumeration) -> SupportFamilies:
    inputs = enumeration.inputs
    families: dict[int, set[Support]] = {}
    for layer in enumeration.layers:
        for state in layer:
            support = state - inputs
            for function in state:
                _insert_minimal(families.setdefault(function, set()), support)
    return {
        function: tuple(sorted(family, key=lambda support: (len(support), tuple(sorted(support)))))
        for function, family in families.items()
    }


def support_union_cost(
    functions: Iterable[int], families: SupportFamilies
) -> int | None:
    requested = tuple(dict.fromkeys(functions))
    if any(function not in families for function in requested):
        return None
    best: int | None = None
    for chosen in product(*(families[function] for function in requested)):
        cost = len(frozenset().union(*chosen))
        if best is None or cost < best:
            best = cost
    return best


def factorization_census(n: int, max_gates: int, arity: int) -> dict[str, int]:
    enumeration = enumerate_available_states(n, max_gates)
    families = provenance_antichains(n, max_gates)
    checked = unavailable = errors = 0
    for requested in combinations(sorted(enumeration.min_size), arity):
        exact = joint_cost_from_states(enumeration, requested)
        factored = support_union_cost(requested, families)
        predicted_available = factored is not None and factored <= max_gates
        actually_available = exact is not None
        checked += 1
        unavailable += int(not actually_available)
        errors += int(predicted_available != actually_available)
        if actually_available and factored != exact:
            errors += 1
    return {
        "checked": checked,
        "unavailable": unavailable,
        "errors": errors,
    }


def singleton_relaxation_cost(target: int, n: int, costs: dict[int, int]) -> int | None:
    best: int | None = None
    functions = sorted(costs)
    for left, right in combinations_with_replacement(functions, 2):
        if nand(left, right, n) != target:
            continue
        candidate = 1 + max(costs[left], costs[right])
        best = candidate if best is None else min(best, candidate)
    return best


def direct_nand_family_cost(n: int, pairs: Iterable[tuple[int, int]]) -> int:
    normalized = {
        tuple(sorted(pair))
        for pair in pairs
    }
    if any(left < 0 or right >= n for left, right in normalized):
        raise ValueError("direct NAND family references an unavailable input")
    inputs = input_masks(n)
    outputs = tuple(nand(inputs[left], inputs[right], n) for left, right in normalized)
    families = {
        output: (frozenset({output}),)
        for output in outputs
    }
    cost = support_union_cost(outputs, families)
    if cost is None:
        raise ValueError("direct NAND family did not produce semantic supports")
    return cost
