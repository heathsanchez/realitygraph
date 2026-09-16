from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from statistics import median
from typing import Any, Iterable

from realitygraph.acc import State, apply_move, state_observables


def _state(value: Any) -> State:
    return tuple(tuple(int(x) for x in word) for word in value)  # type: ignore[return-value]


def _sign(value: int) -> int:
    return -1 if value < 0 else 1 if value > 0 else 0


def guard_for_state(state: State) -> dict[str, Any]:
    obs = state_observables(state)
    lengths = obs["lengths"]
    exponent_sums = obs["exponent_sums"]
    return {
        "length_relation": _sign(lengths[0] - lengths[1]),
        "nonempty": [bool(lengths[0]), bool(lengths[1])],
        "exponent_signs": [
            [_sign(exponent_sums[0][0]), _sign(exponent_sums[0][1])],
            [_sign(exponent_sums[1][0]), _sign(exponent_sums[1][1])],
        ],
        "boundaries": [list(obs["boundaries"][0]), list(obs["boundaries"][1])],
        "mul_cancellation": list(obs["mul_cancellation"]),
    }


def _guard_key(guard: dict[str, Any]) -> str:
    return json.dumps(guard, sort_keys=True, separators=(",", ":"))


def apply_macro(state: State, macro: Iterable[int]) -> State:
    current = state
    for move in macro:
        current = apply_move(current, int(move))
    return current


def _capability_id(guard: dict[str, Any], macro: tuple[int, ...]) -> str:
    payload = json.dumps(
        {"guard": guard, "macro": list(macro)},
        sort_keys=True,
        separators=(",", ":"),
    )
    return "acc-cap-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]


def mine_capabilities(
    trajectories: list[dict[str, Any]],
    *,
    min_support: int = 3,
    min_macro_len: int = 2,
    max_macro_len: int = 8,
) -> list[dict[str, Any]]:
    if min_macro_len < 1 or max_macro_len < min_macro_len:
        raise ValueError("invalid macro length range")

    states_by_guard: dict[str, list[State]] = defaultdict(list)
    guard_values: dict[str, dict[str, Any]] = {}
    occurrences: dict[tuple[str, tuple[int, ...]], list[tuple[str, int]]] = defaultdict(list)

    for trajectory in trajectories:
        moves = tuple(int(m) for m in trajectory["moves"])
        states = [_state(record["state"]) for record in trajectory["states"]]
        if len(states) != len(moves) + 1:
            raise ValueError(f"trajectory length mismatch: {trajectory.get('training_id')}")

        for state in states[:-1]:
            guard = guard_for_state(state)
            key = _guard_key(guard)
            states_by_guard[key].append(state)
            guard_values[key] = guard

        for index, state in enumerate(states[:-1]):
            guard = guard_for_state(state)
            key = _guard_key(guard)
            for length in range(min_macro_len, max_macro_len + 1):
                if index + length > len(moves):
                    break
                macro = moves[index : index + length]
                occurrences[(key, macro)].append((str(trajectory["training_id"]), index))

    bank: list[dict[str, Any]] = []
    for (guard_key, macro), support_rows in occurrences.items():
        if len(support_rows) < min_support:
            continue
        guard_states = states_by_guard[guard_key]
        deltas: list[int] = []
        all_reduce = True
        for state in guard_states:
            before = len(state[0]) + len(state[1])
            after_state = apply_macro(state, macro)
            after = len(after_state[0]) + len(after_state[1])
            delta = after - before
            deltas.append(delta)
            if delta >= 0:
                all_reduce = False
                break
        if not all_reduce:
            continue

        guard = guard_values[guard_key]
        bank.append(
            {
                "id": _capability_id(guard, macro),
                "guard": guard,
                "macro": list(macro),
                "support": len(support_rows),
                "guard_population": len(guard_states),
                "max_total_length_delta": max(deltas),
                "median_total_length_delta": median(deltas),
                "examples": [
                    {"training_id": training_id, "index": index}
                    for training_id, index in support_rows[:8]
                ],
            }
        )

    return sorted(
        bank,
        key=lambda cap: (
            cap["max_total_length_delta"],
            -cap["support"],
            len(cap["macro"]),
            cap["id"],
        ),
    )


def applicable_capabilities(state: State, bank: list[dict[str, Any]]) -> list[dict[str, Any]]:
    guard = guard_for_state(state)
    return [cap for cap in bank if cap["guard"] == guard]


def canonical_bank(bank: list[dict[str, Any]]) -> str:
    ordered = sorted(bank, key=lambda cap: cap["id"])
    return json.dumps(ordered, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"


def restart_bank(text: str) -> list[dict[str, Any]]:
    value = json.loads(text)
    if not isinstance(value, list):
        raise ValueError("capability bank must be a JSON array")
    if canonical_bank(value) != text:
        raise ValueError("capability bank is not canonical or byte-exact")
    return value
