from __future__ import annotations

import heapq
import json
from itertools import count
from typing import Any

from acc_capability_miner import guard_for_state
from acc_prospective_transfer import (
    STANDARD_TARGET,
    _apply_macro_checked,
    _bank_index,
    _heuristic,
    _state,
)
from realitygraph.acc import State, replay


def build_tail_bank(
    trajectories: list[dict[str, Any]],
) -> dict[State, tuple[int, ...]]:
    """Compile every exact certified state into its shortest verified suffix.

    This memory is intentionally exact-state keyed: no quotienting or heuristic
    similarity is treated as equivalence. Every retained suffix is replayed to
    the ordered standard target before promotion.
    """
    bank: dict[State, tuple[int, ...]] = {}
    for trajectory in trajectories:
        moves = tuple(int(m) for m in trajectory["moves"])
        states = [_state(record["state"]) for record in trajectory["states"]]
        if len(states) != len(moves) + 1:
            raise ValueError(f"trajectory length mismatch: {trajectory['training_id']}")
        for index, state in enumerate(states):
            suffix = moves[index:]
            if replay(state, suffix)[-1] != STANDARD_TARGET:
                raise ValueError(
                    f"unverified tail in {trajectory['training_id']} at {index}"
                )
            existing = bank.get(state)
            if existing is None or len(suffix) < len(existing) or (
                len(suffix) == len(existing) and suffix < existing
            ):
                bank[state] = suffix
    return bank


def search_with_tail(
    start: State,
    *,
    tail_bank: dict[State, tuple[int, ...]],
    budget: int,
    bank: list[dict[str, Any]] | None = None,
    start_macros: list[tuple[int, ...]] | None = None,
    max_total: int = 120,
    max_path_length: int = 400,
) -> dict[str, Any]:
    """Best-first search with exact certified-tail closure.

    The search policy is otherwise the existing ACC policy: learned guarded
    macros, optional start macros, and all 14 atomic moves. An exact tail hit is
    accepted only when its stored suffix fits the path bound.
    """
    bank = [] if bank is None else bank
    start_macros = [] if start_macros is None else start_macros

    direct = tail_bank.get(start)
    if direct is not None and len(direct) <= max_path_length:
        return {
            "solved": True,
            "moves": list(direct),
            "expansions": 0,
            "generated": 0,
            "tail_hit": True,
            "tail_length": len(direct),
        }
    if start == STANDARD_TARGET:
        return {
            "solved": True,
            "moves": [],
            "expansions": 0,
            "generated": 0,
            "tail_hit": False,
            "tail_length": 0,
        }

    index = _bank_index(bank)
    serial = count()
    queue: list[tuple[Any, ...]] = []
    heapq.heappush(queue, (_heuristic(start), 0, next(serial), start, ()))
    best_depth: dict[State, int] = {start: 0}
    expansions = 0
    generated = 0

    while queue and expansions < budget:
        _, depth, _, state, path = heapq.heappop(queue)
        if best_depth.get(state) != depth:
            continue
        expansions += 1

        suffix = tail_bank.get(state)
        if suffix is not None and depth + len(suffix) <= max_path_length:
            return {
                "solved": True,
                "moves": list(path + suffix),
                "expansions": expansions,
                "generated": generated,
                "tail_hit": True,
                "tail_length": len(suffix),
            }
        if state == STANDARD_TARGET:
            return {
                "solved": True,
                "moves": list(path),
                "expansions": expansions,
                "generated": generated,
                "tail_hit": False,
                "tail_length": 0,
            }

        macros: list[tuple[int, ...]] = []
        guard_key = json.dumps(
            guard_for_state(state), sort_keys=True, separators=(",", ":")
        )
        for cap in index.get(guard_key, ())[:8]:
            macros.append(tuple(int(m) for m in cap["macro"]))
        if not path:
            macros.extend(start_macros)
        macros.extend((move,) for move in range(14))

        seen_macros: set[tuple[int, ...]] = set()
        for macro in macros:
            if macro in seen_macros:
                continue
            seen_macros.add(macro)
            new_depth = depth + len(macro)
            if new_depth > max_path_length:
                continue
            successor = _apply_macro_checked(state, macro, max_total)
            if successor is None:
                continue
            generated += 1

            successor_tail = tail_bank.get(successor)
            if successor_tail is not None and new_depth + len(successor_tail) <= max_path_length:
                return {
                    "solved": True,
                    "moves": list(path + macro + successor_tail),
                    "expansions": expansions,
                    "generated": generated,
                    "tail_hit": True,
                    "tail_length": len(successor_tail),
                }

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
        "tail_hit": False,
        "tail_length": 0,
    }
