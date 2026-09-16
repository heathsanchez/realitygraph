from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import Any, Iterable

from acc_capability_miner import guard_for_state
from acc_developmental_core import GeneratedAction, primitive_expansion_ok
from realitygraph.acc import State, replay, state_observables


GUARD_KINDS = ("shape", "algebraic", "boundary")


def _state(value: Any) -> State:
    words = tuple(tuple(int(x) for x in word) for word in value)
    if len(words) != 2:
        raise ValueError("ordinary AC state must contain exactly two relators")
    return words  # type: ignore[return-value]


def _sign(value: int) -> int:
    return -1 if value < 0 else 1 if value > 0 else 0


def quotient_guard(state: State, kind: str) -> dict[str, Any]:
    """Target-free structural quotient used only for macro applicability.

    `shape` deliberately forgets boundary letters and cancellation details.
    `algebraic` adds exponent-sum signs.  `boundary` also adds first/last
    letters, while still omitting the brittle multiplication-cancellation
    signature from the legacy structural guard.
    """
    if kind not in GUARD_KINDS:
        raise ValueError(f"unknown quotient guard kind: {kind}")
    obs = state_observables(state)
    lengths = obs["lengths"]
    guard: dict[str, Any] = {
        "kind": kind,
        "length_relation": _sign(int(lengths[0]) - int(lengths[1])),
        "nonempty": [bool(lengths[0]), bool(lengths[1])],
    }
    if kind in ("algebraic", "boundary"):
        exponent_sums = obs["exponent_sums"]
        guard["exponent_signs"] = [
            [_sign(int(exponent_sums[0][0])), _sign(int(exponent_sums[0][1]))],
            [_sign(int(exponent_sums[1][0])), _sign(int(exponent_sums[1][1]))],
        ]
    if kind == "boundary":
        guard["boundaries"] = [
            list(obs["boundaries"][0]),
            list(obs["boundaries"][1]),
        ]
    return guard


def _guard_key(guard: dict[str, Any]) -> str:
    return json.dumps(guard, sort_keys=True, separators=(",", ":"))


def _capability_id(kind: str, guard: dict[str, Any], macro: tuple[int, ...]) -> str:
    payload = json.dumps(
        {"kind": kind, "guard": guard, "macro": list(macro)},
        sort_keys=True,
        separators=(",", ":"),
    )
    return "acc-qstruct-" + hashlib.sha256(payload.encode()).hexdigest()[:20]


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


def mine_quotient_structural_macros(
    trajectories: list[dict[str, Any]],
    *,
    guard_kind: str,
    min_support: int = 3,
    min_macro_len: int = 2,
    max_macro_len: int = 8,
) -> list[dict[str, Any]]:
    if guard_kind not in GUARD_KINDS:
        raise ValueError(f"unknown quotient guard kind: {guard_kind}")
    if min_support < 1:
        raise ValueError("min_support must be positive")
    if min_macro_len < 1 or max_macro_len < min_macro_len:
        raise ValueError("invalid macro length range")

    guards: dict[str, dict[str, Any]] = {}
    occurrences: dict[tuple[str, tuple[int, ...]], dict[str, list[int]]] = defaultdict(
        lambda: defaultdict(list)
    )

    for trajectory in trajectories:
        moves, states = _validated_trace(trajectory)
        training_id = str(trajectory.get("training_id", ""))
        for index, state in enumerate(states[:-1]):
            guard = quotient_guard(state, guard_kind)
            key = _guard_key(guard)
            guards[key] = guard
            for length in range(min_macro_len, max_macro_len + 1):
                end = index + length
                if end > len(moves):
                    break
                macro = moves[index:end]
                occurrences[(key, macro)][training_id].append(index)

    bank: list[dict[str, Any]] = []
    for (guard_key, macro), by_trajectory in occurrences.items():
        support = len(by_trajectory)
        if support < min_support:
            continue
        guard = guards[guard_key]
        examples = [
            {"training_id": training_id, "index": indices[0]}
            for training_id, indices in sorted(by_trajectory.items())[:8]
        ]
        bank.append(
            {
                "id": _capability_id(guard_kind, guard, macro),
                "guard_kind": guard_kind,
                "guard": guard,
                "macro": list(macro),
                "support": support,
                "occurrences": sum(len(indices) for indices in by_trajectory.values()),
                "examples": examples,
            }
        )

    return sorted(
        bank,
        key=lambda cap: (
            -int(cap["support"]),
            -int(cap["occurrences"]),
            len(cap["macro"]),
            str(cap["id"]),
        ),
    )


class QuotientStructuralGenerator:
    generator_id = "quotient_structural"

    def __init__(
        self,
        bank: Iterable[dict[str, Any]],
        *,
        guard_kind: str,
        max_actions: int = 48,
    ):
        if guard_kind not in GUARD_KINDS:
            raise ValueError(f"unknown quotient guard kind: {guard_kind}")
        self.bank = tuple(bank)
        self.guard_kind = guard_kind
        self.max_actions = int(max_actions)

    def generate(self, state: State) -> tuple[GeneratedAction, ...]:
        guard = quotient_guard(state, self.guard_kind)
        actions: list[GeneratedAction] = []
        seen: set[tuple[int, ...]] = set()
        for cap in self.bank:
            if cap.get("guard_kind") != self.guard_kind or cap["guard"] != guard:
                continue
            moves = tuple(int(move) for move in cap["macro"])
            if moves in seen:
                continue
            seen.add(moves)
            successor = replay(state, moves)[-1]
            action = GeneratedAction(
                self.generator_id,
                moves,
                successor,
                (
                    str(cap["id"]),
                    f"guard={self.guard_kind}",
                    f"support={cap['support']}",
                ),
            )
            if primitive_expansion_ok(state, action):
                actions.append(action)
            if len(actions) >= self.max_actions:
                break
        return tuple(actions)
