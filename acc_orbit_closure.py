from __future__ import annotations

import heapq
import json
from itertools import count
from typing import Any

from acc_capability_miner import guard_for_state
from acc_consequence_closure import (
    STANDARD_TARGET,
    _apply_macro_checked,
    _bank_index,
    _guard_key,
    _heuristic,
)
from acc_open_ms_transfer import find_orbit_bridge, presentation_orbit_key
from realitygraph.acc import State, replay


def _parse_state_key(key: str) -> State:
    left, right = key.split("|", 1)
    return (
        tuple(int(x) for x in left.split(",") if x),
        tuple(int(x) for x in right.split(",") if x),
    )


def _json_state(state: State) -> list[list[int]]:
    return [list(state[0]), list(state[1])]


def _orbit_key(state: State) -> str:
    return json.dumps(
        [list(word) for word in presentation_orbit_key(state)],
        separators=(",", ":"),
    )


def build_orbit_closure(
    exact_closure: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Quotient an exact solved-state closure by primitive-realizable symmetries.

    Cyclic rotation, relator inversion, and relator order are used only as an
    index. A search hit must still construct and replay an explicit primitive
    AC bridge to the retained representative before appending its known suffix.
    """
    orbit: dict[str, dict[str, Any]] = {}
    for exact_key, entry in exact_closure.items():
        representative = _parse_state_key(exact_key)
        key = _orbit_key(representative)
        candidate = {
            "representative": _json_state(representative),
            "training_id": str(entry["training_id"]),
            "index": int(entry["index"]),
            "moves": [int(move) for move in entry["moves"]],
        }
        incumbent = orbit.get(key)
        candidate_rank = (
            len(candidate["moves"]),
            candidate["training_id"],
            candidate["index"],
            candidate["representative"],
        )
        if incumbent is None:
            orbit[key] = candidate
            continue
        incumbent_rank = (
            len(incumbent["moves"]),
            incumbent["training_id"],
            incumbent["index"],
            incumbent["representative"],
        )
        if candidate_rank < incumbent_rank:
            orbit[key] = candidate
    return orbit


def orbit_closure_search(
    start: State,
    *,
    orbit_closure: dict[str, dict[str, Any]],
    bank: list[dict[str, Any]],
    start_macros: list[tuple[int, ...]],
    budget: int,
    max_total: int = 120,
    max_path_length: int = 400,
) -> dict[str, Any]:
    """Search until reaching the AC-symmetry orbit of any retained solved state."""
    index = _bank_index(bank)
    serial = count()
    queue: list[tuple[Any, ...]] = []
    heapq.heappush(queue, (_heuristic(start), 0, next(serial), start, ()))
    best_depth: dict[State, int] = {start: 0}
    expansions = 0
    generated = 0

    while queue and expansions < budget:
        _, depth, _, current, path = heapq.heappop(queue)
        if best_depth.get(current) != depth:
            continue
        expansions += 1

        if current == STANDARD_TARGET:
            return {
                "solved": True,
                "moves": list(path),
                "expansions": expansions,
                "generated": generated,
                "orbit_join": False,
                "join_training_id": None,
                "join_index": None,
                "join_depth": depth,
                "bridge_length": 0,
                "retained_suffix_length": 0,
            }

        retained = orbit_closure.get(_orbit_key(current))
        if retained is not None:
            representative: State = tuple(
                tuple(int(x) for x in word)
                for word in retained["representative"]
            )  # type: ignore[assignment]
            bridge = find_orbit_bridge(current, representative)
            suffix = tuple(int(move) for move in retained["moves"])
            tail = tuple(int(move) for move in bridge) + suffix
            if depth + len(tail) <= max_path_length:
                endpoint = _apply_macro_checked(current, tail, max_total)
                if endpoint == STANDARD_TARGET:
                    moves = list(path + tail)
                    if replay(start, moves)[-1] != STANDARD_TARGET:
                        raise AssertionError("orbit closure composed an invalid path")
                    return {
                        "solved": True,
                        "moves": moves,
                        "expansions": expansions,
                        "generated": generated,
                        "orbit_join": True,
                        "join_training_id": retained["training_id"],
                        "join_index": retained["index"],
                        "join_depth": depth,
                        "bridge_length": len(bridge),
                        "retained_suffix_length": len(suffix),
                    }

        macros: list[tuple[int, ...]] = []
        guard_key = _guard_key(guard_for_state(current))
        for capability in index.get(guard_key, ())[:8]:
            macros.append(tuple(int(move) for move in capability["macro"]))
        if not path:
            macros.extend(tuple(int(move) for move in macro) for macro in start_macros)
        macros.extend((move,) for move in range(14))

        seen: set[tuple[int, ...]] = set()
        for macro in macros:
            if macro in seen:
                continue
            seen.add(macro)
            new_depth = depth + len(macro)
            if new_depth > max_path_length:
                continue
            successor = _apply_macro_checked(current, macro, max_total)
            if successor is None:
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

    return {
        "solved": False,
        "moves": [],
        "expansions": expansions,
        "generated": generated,
        "orbit_join": False,
        "join_training_id": None,
        "join_index": None,
        "join_depth": None,
        "bridge_length": None,
        "retained_suffix_length": None,
    }
