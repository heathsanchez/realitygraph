from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Mapping

from realitygraph.acc import NUM_MOVES, State, free_reduce, replay, state_observables


@dataclass(frozen=True)
class GeneratedAction:
    generator_id: str
    moves: tuple[int, ...]
    successor: State
    provenance: tuple[str, ...] = ()


@dataclass(frozen=True)
class GeneratorResult:
    generator_id: str
    actions: tuple[GeneratedAction, ...]
    diagnostics: tuple[tuple[str, object], ...] = ()


@dataclass(frozen=True)
class ACCResidual:
    source_family: str
    n: int | None
    w_signature: tuple[int, ...]
    relator_lengths: tuple[int, int]
    exponent_sum_matrix: tuple[tuple[int, int], tuple[int, int]]
    initial_heuristic: tuple[int, ...]
    best_heuristic: tuple[int, ...]
    min_total_length: int
    best_depth: int
    first_capability_depth: int | None
    capability_expansions: int
    exact_tail_near_hits: int
    orbit_tail_near_hits: int
    plateau_length: int
    max_total_reject_fraction: float
    budget_consumed: int

    def canonical_json(self) -> str:
        return json.dumps(
            asdict(self),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )


_FORBIDDEN_DIAGNOSTIC_FRAGMENTS = (
    "target",
    "solution",
    "solved",
    "outcome",
    "verdict",
    "answer",
    "move_sequence",
    "target_moves",
)

_REQUIRED_DIAGNOSTICS = (
    "initial_heuristic",
    "best_heuristic",
    "min_total_length",
    "best_depth",
    "first_capability_depth",
    "capability_expansions",
    "exact_tail_near_hits",
    "orbit_tail_near_hits",
    "plateau_length",
    "max_total_reject_fraction",
    "budget_consumed",
)


def primitive_expansion_ok(start: State, action: GeneratedAction) -> bool:
    if not action.generator_id:
        return False
    if any(not isinstance(move, int) or move < 0 or move >= NUM_MOVES for move in action.moves):
        return False
    try:
        return replay(start, action.moves)[-1] == action.successor
    except (TypeError, ValueError):
        return False


def _tuple_ints(value: object) -> tuple[int, ...]:
    if not isinstance(value, (tuple, list)):
        raise ValueError("heuristic must be a sequence")
    return tuple(int(item) for item in value)


def residual_from_search(
    start: State,
    *,
    source_family: str,
    n: int | None,
    w_vector: tuple[int, ...] | list[int],
    diagnostics: Mapping[str, Any],
) -> ACCResidual:
    lower_keys = tuple(str(key).lower() for key in diagnostics)
    if any(
        fragment in key
        for key in lower_keys
        for fragment in _FORBIDDEN_DIAGNOSTIC_FRAGMENTS
    ):
        raise ValueError("ACC residual diagnostics must be target-free")

    missing = [key for key in _REQUIRED_DIAGNOSTICS if key not in diagnostics]
    if missing:
        raise ValueError(f"missing residual diagnostics: {','.join(missing)}")

    observables = state_observables(start)
    lengths = tuple(int(x) for x in observables["lengths"])
    exponent_sums = tuple(
        tuple(int(x) for x in row) for row in observables["exponent_sums"]
    )
    first_depth = diagnostics["first_capability_depth"]

    return ACCResidual(
        source_family=str(source_family),
        n=None if n is None else int(n),
        w_signature=free_reduce(tuple(int(x) for x in w_vector)),
        relator_lengths=(lengths[0], lengths[1]),
        exponent_sum_matrix=(exponent_sums[0], exponent_sums[1]),
        initial_heuristic=_tuple_ints(diagnostics["initial_heuristic"]),
        best_heuristic=_tuple_ints(diagnostics["best_heuristic"]),
        min_total_length=int(diagnostics["min_total_length"]),
        best_depth=int(diagnostics["best_depth"]),
        first_capability_depth=None if first_depth is None else int(first_depth),
        capability_expansions=int(diagnostics["capability_expansions"]),
        exact_tail_near_hits=int(diagnostics["exact_tail_near_hits"]),
        orbit_tail_near_hits=int(diagnostics["orbit_tail_near_hits"]),
        plateau_length=int(diagnostics["plateau_length"]),
        max_total_reject_fraction=float(diagnostics["max_total_reject_fraction"]),
        budget_consumed=int(diagnostics["budget_consumed"]),
    )
