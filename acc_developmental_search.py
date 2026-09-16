from __future__ import annotations

import heapq
from collections import Counter
from itertools import count
from typing import Any, Callable, Iterable

from acc_capability_miner import guard_for_state
from acc_consequence_closure import (
    STANDARD_TARGET,
    _apply_macro_checked,
    _bank_index,
    _guard_key,
    _heuristic,
)
from acc_developmental_core import GeneratedAction, primitive_expansion_ok
from acc_open_ms_transfer import find_orbit_bridge
from acc_orbit_closure import _orbit_key
from realitygraph.acc import State, replay


ExtraActions = Callable[[State], Iterable[GeneratedAction]]


def developmental_search(
    start: State,
    *,
    orbit_closure: dict[str, dict[str, Any]],
    bank: list[dict[str, Any]],
    start_macros: list[tuple[int, ...]],
    budget: int,
    extra_actions: ExtraActions | None,
    max_total: int = 120,
    max_path_length: int = 400,
) -> dict[str, Any]:
    """Instrumented best-first ACC search with optional verified generators.

    The queue/search heuristic is the existing ACC baseline.  Generator actions
    are additional primitive-move macros and are accepted only after exact
    replay to their claimed successor.  Search diagnostics contain no target
    certificate, withheld move sequence, or outcome label.
    """
    index = _bank_index(bank)
    serial = count()
    queue: list[tuple[Any, ...]] = []
    initial_heuristic = _heuristic(start)
    heapq.heappush(queue, (initial_heuristic, 0, next(serial), start, ()))
    best_depth: dict[State, int] = {start: 0}

    expansions = 0
    generated = 0
    attempted_successors = 0
    max_total_rejects = 0
    best_heuristic = initial_heuristic
    best_heuristic_depth = 0
    min_total_length = len(start[0]) + len(start[1])
    last_improvement_expansion = 0
    first_capability_depth: int | None = None
    capability_expansions = 0
    exact_tail_near_hits = 0
    orbit_tail_near_hits = 0
    generator_uses: Counter[str] = Counter()

    def diagnostics() -> dict[str, Any]:
        return {
            "initial_heuristic": initial_heuristic,
            "best_heuristic": best_heuristic,
            "min_total_length": min_total_length,
            "best_depth": best_heuristic_depth,
            "first_capability_depth": first_capability_depth,
            "capability_expansions": capability_expansions,
            "exact_tail_near_hits": exact_tail_near_hits,
            "orbit_tail_near_hits": orbit_tail_near_hits,
            "plateau_length": max(0, expansions - last_improvement_expansion),
            "max_total_reject_fraction": (
                max_total_rejects / attempted_successors
                if attempted_successors
                else 0.0
            ),
            "budget_consumed": expansions,
        }

    def solved_result(moves: tuple[int, ...] | list[int]) -> dict[str, Any]:
        path = list(moves)
        if replay(start, path)[-1] != STANDARD_TARGET:
            raise AssertionError("developmental search composed an invalid solution")
        return {
            "solved": True,
            "moves": path,
            "expansions": expansions,
            "generated": generated,
            "generator_uses": dict(sorted(generator_uses.items())),
            "diagnostics": diagnostics(),
        }

    while queue and expansions < budget:
        _, depth, _, current, path = heapq.heappop(queue)
        if best_depth.get(current) != depth:
            continue
        expansions += 1

        current_heuristic = _heuristic(current)
        current_total = len(current[0]) + len(current[1])
        min_total_length = min(min_total_length, current_total)
        if current_heuristic < best_heuristic:
            best_heuristic = current_heuristic
            best_heuristic_depth = depth
            last_improvement_expansion = expansions

        if current == STANDARD_TARGET:
            return solved_result(path)

        retained = orbit_closure.get(_orbit_key(current))
        if retained is not None:
            orbit_tail_near_hits += 1
            representative: State = tuple(
                tuple(int(x) for x in word)
                for word in retained["representative"]
            )  # type: ignore[assignment]
            if representative == current:
                exact_tail_near_hits += 1
            bridge = tuple(int(move) for move in find_orbit_bridge(current, representative))
            suffix = tuple(int(move) for move in retained["moves"])
            tail = bridge + suffix
            if depth + len(tail) <= max_path_length:
                attempted_successors += 1
                endpoint = _apply_macro_checked(current, tail, max_total)
                if endpoint is None:
                    max_total_rejects += 1
                elif endpoint == STANDARD_TARGET:
                    return solved_result(path + tail)

        guard_key = _guard_key(guard_for_state(current))
        capabilities = index.get(guard_key, ())[:8]
        if capabilities:
            capability_expansions += 1
            if first_capability_depth is None:
                first_capability_depth = depth

        baseline_macros: list[tuple[int, ...]] = [
            tuple(int(move) for move in capability["macro"])
            for capability in capabilities
        ]
        if not path:
            baseline_macros.extend(
                tuple(int(move) for move in macro) for macro in start_macros
            )
        baseline_macros.extend((move,) for move in range(14))

        seen_macros: set[tuple[int, ...]] = set()
        for macro in baseline_macros:
            if macro in seen_macros:
                continue
            seen_macros.add(macro)
            new_depth = depth + len(macro)
            if new_depth > max_path_length:
                continue
            attempted_successors += 1
            successor = _apply_macro_checked(current, macro, max_total)
            if successor is None:
                max_total_rejects += 1
                continue
            generated += 1
            old_depth = best_depth.get(successor)
            if old_depth is not None and old_depth <= new_depth:
                continue
            best_depth[successor] = new_depth
            heapq.heappush(
                queue,
                (
                    _heuristic(successor),
                    new_depth,
                    next(serial),
                    successor,
                    path + macro,
                ),
            )

        if extra_actions is None:
            continue
        for action in extra_actions(current):
            if not primitive_expansion_ok(current, action):
                raise AssertionError(
                    f"invalid generated action from {action.generator_id}"
                )
            macro = tuple(int(move) for move in action.moves)
            if not macro or depth + len(macro) > max_path_length:
                continue
            attempted_successors += 1
            endpoint = _apply_macro_checked(current, macro, max_total)
            if endpoint is None:
                max_total_rejects += 1
                continue
            if endpoint != action.successor:
                raise AssertionError(
                    f"generated action successor drift from {action.generator_id}"
                )
            generator_uses[action.generator_id] += 1
            generated += 1
            if endpoint == STANDARD_TARGET:
                return solved_result(path + macro)
            new_depth = depth + len(macro)
            old_depth = best_depth.get(endpoint)
            if old_depth is not None and old_depth <= new_depth:
                continue
            best_depth[endpoint] = new_depth
            heapq.heappush(
                queue,
                (
                    _heuristic(endpoint),
                    new_depth,
                    next(serial),
                    endpoint,
                    path + macro,
                ),
            )

    return {
        "solved": False,
        "moves": [],
        "expansions": expansions,
        "generated": generated,
        "generator_uses": dict(sorted(generator_uses.items())),
        "diagnostics": diagnostics(),
    }
