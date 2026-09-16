from __future__ import annotations

import heapq
import json
from itertools import count
from typing import Any, Iterable

from acc_capability_miner import guard_for_state
from realitygraph.acc import State, apply_move

STANDARD_TARGET: State = ((1,), (2,))


def _state(value: Iterable[Iterable[int]]) -> State:
    words = tuple(tuple(int(x) for x in word) for word in value)
    if len(words) != 2:
        raise ValueError("ordinary AC state must contain exactly two relators")
    return words  # type: ignore[return-value]


def state_key(state: State) -> str:
    return ",".join(str(x) for x in state[0]) + "|" + ",".join(
        str(x) for x in state[1]
    )


def _exponent_sums(word: tuple[int, ...]) -> tuple[int, int]:
    return (
        sum(1 if x == 1 else -1 if x == -1 else 0 for x in word),
        sum(1 if x == 2 else -1 if x == -2 else 0 for x in word),
    )


def _heuristic(state: State) -> tuple[int, int, int]:
    total = len(state[0]) + len(state[1])
    exps = (_exponent_sums(state[0]), _exponent_sums(state[1]))
    target = ((1, 0), (0, 1))
    exp_distance = sum(
        abs(exps[i][j] - target[i][j]) for i in range(2) for j in range(2)
    )
    singleton_penalty = sum(
        0 if state[i] == STANDARD_TARGET[i] else 1 for i in range(2)
    )
    return total + exp_distance + singleton_penalty, total, exp_distance


def _guard_key(guard: dict[str, Any]) -> str:
    return json.dumps(guard, sort_keys=True, separators=(",", ":"))


def _bank_index(bank: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    for capability in bank:
        index.setdefault(_guard_key(capability["guard"]), []).append(capability)
    for capabilities in index.values():
        capabilities.sort(
            key=lambda cap: (
                cap.get("max_total_length_delta", 0),
                -int(cap.get("support", 0)),
                len(cap["macro"]),
                str(cap.get("id", "")),
            )
        )
    return index


def _apply_macro_checked(
    state: State, macro: Iterable[int], max_total: int
) -> State | None:
    current = state
    for move in macro:
        current = apply_move(current, int(move))
        if len(current[0]) + len(current[1]) > max_total:
            return None
    return current


def build_suffix_closure(
    trajectories: Iterable[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Compile every verified trajectory state into a shortest known suffix.

    The closure is exact-state only. It does not quotient by rotations,
    inversions, relator order, or any other equivalence relation. When the same
    state occurs in multiple proofs we retain the shortest remaining primitive
    AC path; ties are broken deterministically by source id and state index.
    """
    closure: dict[str, dict[str, Any]] = {}
    for trajectory in trajectories:
        training_id = str(trajectory["training_id"])
        moves = tuple(int(move) for move in trajectory["moves"])
        states = [_state(record["state"]) for record in trajectory["states"]]
        if len(states) != len(moves) + 1:
            raise ValueError(f"trajectory length mismatch: {training_id}")
        if states[-1] != STANDARD_TARGET:
            raise ValueError(f"trajectory does not end at ordered standard target: {training_id}")

        for index, current in enumerate(states):
            suffix = list(moves[index:])
            key = state_key(current)
            candidate = {
                "training_id": training_id,
                "index": index,
                "moves": suffix,
            }
            incumbent = closure.get(key)
            if incumbent is None:
                closure[key] = candidate
                continue
            candidate_rank = (
                len(candidate["moves"]),
                candidate["training_id"],
                candidate["index"],
            )
            incumbent_rank = (
                len(incumbent["moves"]),
                incumbent["training_id"],
                incumbent["index"],
            )
            if candidate_rank < incumbent_rank:
                closure[key] = candidate
    return closure


def canonical_closure(closure: dict[str, dict[str, Any]]) -> str:
    return json.dumps(
        closure,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ) + "\n"


def restart_closure(text: str) -> dict[str, dict[str, Any]]:
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("consequence closure must be a JSON object")
    if canonical_closure(value) != text:
        raise ValueError("consequence closure is not canonical or byte-exact")
    return value


def closure_search(
    start: State,
    *,
    closure: dict[str, dict[str, Any]],
    bank: list[dict[str, Any]],
    start_macros: list[tuple[int, ...]],
    budget: int,
    max_total: int = 120,
    max_path_length: int = 400,
) -> dict[str, Any]:
    """Search only until a state with a verified retained suffix is reached."""
    if budget < 0:
        raise ValueError("budget must be nonnegative")

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
                "join_training_id": None,
                "join_index": None,
                "join_depth": depth,
                "retained_suffix_length": 0,
            }

        retained = closure.get(state_key(current))
        if retained is not None:
            suffix = tuple(int(move) for move in retained["moves"])
            if depth + len(suffix) <= max_path_length:
                return {
                    "solved": True,
                    "moves": list(path + suffix),
                    "expansions": expansions,
                    "generated": generated,
                    "join_training_id": retained["training_id"],
                    "join_index": retained["index"],
                    "join_depth": depth,
                    "retained_suffix_length": len(suffix),
                }

        macros: list[tuple[int, ...]] = []
        guard_key = _guard_key(guard_for_state(current))
        for capability in index.get(guard_key, ())[:8]:
            macros.append(tuple(int(move) for move in capability["macro"]))
        if not path:
            macros.extend(tuple(int(move) for move in macro) for macro in start_macros)
        macros.extend((move,) for move in range(14))

        seen_macros: set[tuple[int, ...]] = set()
        for macro in macros:
            if macro in seen_macros:
                continue
            seen_macros.add(macro)
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
        "join_training_id": None,
        "join_index": None,
        "join_depth": None,
        "retained_suffix_length": None,
    }
