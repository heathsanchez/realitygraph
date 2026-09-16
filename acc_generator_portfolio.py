from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from acc_developmental_core import GeneratedAction, primitive_expansion_ok
from acc_ms_recurrence import (
    N_REDUCTION_MACRO,
    commutes_with_y,
    macro_reduces_n,
    ms_state,
)
from acc_open_ms_transfer import find_orbit_bridge
from acc_orbit_closure import _orbit_key
from realitygraph.acc import State, replay


@dataclass(frozen=True)
class ACCGeneratorContext:
    exact_tail_bank: dict[State, tuple[int, ...]] | None = None
    orbit_closure: dict[str, dict[str, Any]] | None = None
    source_family: str | None = None
    n: int | None = None
    w_vector: tuple[int, ...] = ()


class ACCGenerator(Protocol):
    generator_id: str

    def generate(
        self, state: State, context: ACCGeneratorContext
    ) -> tuple[GeneratedAction, ...]: ...


@dataclass(frozen=True)
class ExactTailGenerator:
    generator_id: str = "exact_tail"

    def generate(
        self, state: State, context: ACCGeneratorContext
    ) -> tuple[GeneratedAction, ...]:
        bank = context.exact_tail_bank or {}
        moves = bank.get(state)
        if moves is None:
            return ()
        successor = replay(state, moves)[-1]
        action = GeneratedAction(
            self.generator_id,
            tuple(int(move) for move in moves),
            successor,
            ("exact_tail",),
        )
        return (action,) if primitive_expansion_ok(state, action) else ()


@dataclass(frozen=True)
class OrbitTailGenerator:
    generator_id: str = "orbit_tail"

    def generate(
        self, state: State, context: ACCGeneratorContext
    ) -> tuple[GeneratedAction, ...]:
        closure = context.orbit_closure or {}
        retained = closure.get(_orbit_key(state))
        if retained is None:
            return ()
        representative: State = tuple(
            tuple(int(x) for x in word)
            for word in retained["representative"]
        )  # type: ignore[assignment]
        bridge = tuple(int(move) for move in find_orbit_bridge(state, representative))
        suffix = tuple(int(move) for move in retained["moves"])
        moves = bridge + suffix
        successor = replay(state, moves)[-1]
        action = GeneratedAction(
            self.generator_id,
            moves,
            successor,
            (
                "orbit_tail",
                str(retained.get("training_id", "")),
                str(retained.get("index", "")),
            ),
        )
        return (action,) if primitive_expansion_ok(state, action) else ()


@dataclass(frozen=True)
class RecurrenceGenerator:
    generator_id: str = "ms_recurrence"

    def generate(
        self, state: State, context: ACCGeneratorContext
    ) -> tuple[GeneratedAction, ...]:
        if context.source_family != "ms" or context.n is None or context.n < 2:
            return ()
        w = tuple(int(x) for x in context.w_vector)
        if state != ms_state(context.n, w):
            return ()
        if not commutes_with_y(w) or not macro_reduces_n(context.n, w):
            return ()
        successor = ms_state(context.n - 1, w)
        action = GeneratedAction(
            self.generator_id,
            N_REDUCTION_MACRO,
            successor,
            ("ms_centralizer_recurrence", f"n={context.n}"),
        )
        return (action,) if primitive_expansion_ok(state, action) else ()


@dataclass(frozen=True)
class GeneratorPortfolio:
    generators: tuple[ACCGenerator, ...]

    @classmethod
    def default(cls) -> "GeneratorPortfolio":
        return cls(
            (
                ExactTailGenerator(),
                OrbitTailGenerator(),
                RecurrenceGenerator(),
            )
        )

    def generate(
        self, state: State, context: ACCGeneratorContext
    ) -> tuple[GeneratedAction, ...]:
        out: list[GeneratedAction] = []
        seen: set[tuple[str, tuple[int, ...], State]] = set()
        for generator in self.generators:
            for action in generator.generate(state, context):
                if not primitive_expansion_ok(state, action):
                    raise AssertionError(
                        f"generator {generator.generator_id} emitted an invalid primitive expansion"
                    )
                key = (action.generator_id, action.moves, action.successor)
                if key in seen:
                    continue
                seen.add(key)
                out.append(action)
        return tuple(out)
