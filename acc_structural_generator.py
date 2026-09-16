from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from statistics import median
from typing import Any, Iterable

from acc_capability_miner import guard_for_state
from acc_developmental_core import GeneratedAction, primitive_expansion_ok
from realitygraph.acc import State, replay


def _state(value: Any) -> State:
    words = tuple(tuple(int(x) for x in word) for word in value)
    if len(words) != 2:
        raise ValueError("ordinary AC state must contain exactly two relators")
    return words  # type: ignore[return-value]


def _guard_key(guard: dict[str, Any]) -> str:
    return json.dumps(guard, sort_keys=True, separators=(",", ":"))


def _total(state: State) -> int:
    return len(state[0]) + len(state[1])


def _capability_id(guard: dict[str, Any], macro: tuple[int, ...]) -> str:
    payload = json.dumps(
        {"guard": guard, "macro": list(macro)},
        sort_keys=True,
        separators=(",", ":"),
    )
    return "acc-struct-" + hashlib.sha256(payload.encode()).hexdigest()[:20]


def _validated_trace(trajectory: dict[str, Any]) -> tuple[tuple[int, ...], tuple[State, ...]]:
    moves = tuple(int(move) for move in trajectory["moves"])
    states = tuple(_state(record["state"]) for record in trajectory["states"])
    if len(states) != len(moves) + 1:
        raise ValueError(f"trajectory length mismatch: {trajectory.get('training_id')}")
    current = states[0]
    for index, move in enumerate(moves):
        successor = replay(current, (move,))[-1]
        if successor != states[index + 1]:
            raise ValueError(
                f"trajectory replay mismatch: {trajectory.get('training_id')} at {index}"
            )
        current = successor
    return moves, states


def mine_structural_macros(
    trajectories: list[dict[str, Any]],
    *,
    min_support: int = 3,
    min_macro_len: int = 2,
    max_macro_len: int = 8,
) -> list[dict[str, Any]]:
    if min_support < 1:
        raise ValueError("min_support must be positive")
    if min_macro_len < 1 or max_macro_len < min_macro_len:
        raise ValueError("invalid macro length range")

    occurrences: dict[
        tuple[str, tuple[int, ...]], list[dict[str, Any]]
    ] = defaultdict(list)
    guards: dict[str, dict[str, Any]] = {}

    for trajectory in trajectories:
        moves, states = _validated_trace(trajectory)
        training_id = str(trajectory.get("training_id", ""))
        for index, state in enumerate(states[:-1]):
            guard = guard_for_state(state)
            guard_key = _guard_key(guard)
            guards[guard_key] = guard
            for length in range(min_macro_len, max_macro_len + 1):
                end = index + length
                if end > len(moves):
                    break
                macro = moves[index:end]
                segment = states[index : end + 1]
                before = _total(segment[0])
                deltas = tuple(_total(item) - before for item in segment[1:])
                occurrences[(guard_key, macro)].append(
                    {
                        "training_id": training_id,
                        "index": index,
                        "final_delta": deltas[-1],
                        "peak_delta": max((0,) + deltas),
                    }
                )

    bank: list[dict[str, Any]] = []
    for (guard_key, macro), rows in occurrences.items():
        if len(rows) < min_support:
            continue
        guard = guards[guard_key]
        final_deltas = [int(row["final_delta"]) for row in rows]
        peak_deltas = [int(row["peak_delta"]) for row in rows]
        bank.append(
            {
                "id": _capability_id(guard, macro),
                "guard": guard,
                "macro": list(macro),
                "support": len(rows),
                "max_final_total_length_delta": max(final_deltas),
                "median_final_total_length_delta": median(final_deltas),
                "max_peak_total_length_delta": max(peak_deltas),
                "examples": [
                    {"training_id": row["training_id"], "index": row["index"]}
                    for row in rows[:8]
                ],
            }
        )

    return sorted(
        bank,
        key=lambda cap: (
            -int(cap["support"]),
            int(cap["max_final_total_length_delta"]),
            len(cap["macro"]),
            str(cap["id"]),
        ),
    )


class StructuralMacroGenerator:
    generator_id = "structural_macro"

    def __init__(self, bank: Iterable[dict[str, Any]]):
        self.bank = tuple(bank)

    def generate(self, state: State) -> tuple[GeneratedAction, ...]:
        guard = guard_for_state(state)
        actions: list[GeneratedAction] = []
        for cap in self.bank:
            if cap["guard"] != guard:
                continue
            moves = tuple(int(move) for move in cap["macro"])
            successor = replay(state, moves)[-1]
            action = GeneratedAction(
                self.generator_id,
                moves,
                successor,
                (str(cap["id"]), f"support={cap['support']}"),
            )
            if primitive_expansion_ok(state, action):
                actions.append(action)
        return tuple(actions)
