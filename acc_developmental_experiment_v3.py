from __future__ import annotations

from typing import Any, Callable

import acc_developmental_experiment as v1
from acc_substitution_generator import SubstitutionGenerator, source_conditioned_candidates
from realitygraph.acc import State


def _composite_extra_callback(
    generator_id: str | None,
    row: dict[str, Any],
    components: v1.AcquisitionComponents,
) -> Callable[[State], tuple[Any, ...]]:
    """V3 adapter: compose the two independently useful substitution portfolios.

    V1 contributes its frozen first 48 globally enumerated substitutions.  V2
    contributes up to 48 source-conditioned substitutions derived from the row's
    Miller--Schupp word.  Actions are deduplicated by exact primitive move tuple.
    Search, replay checks, controller learning, and official verification remain
    the sealed V1 machinery.
    """
    recurrence = v1._recurrence_callback(row)
    structural = components.structural_generator
    _, _, source_word = v1._row_source(row)
    frozen = v1._substitution_generator()
    conditioned = SubstitutionGenerator(
        source_conditioned_candidates(source_word, max_words=12),
        max_total=120,
        max_path_length=400,
    )

    def callback(state: State) -> tuple[Any, ...]:
        baseline_actions = tuple(recurrence(state))
        if generator_id is None:
            return baseline_actions
        if generator_id == "structural_macro":
            generated = tuple(structural.generate(state)[:8])
        elif generator_id == "substitution":
            seen: set[tuple[int, ...]] = set()
            merged: list[Any] = []
            for action in tuple(frozen.generate(state)[:48]) + tuple(
                conditioned.generate(state)[:48]
            ):
                moves = tuple(int(move) for move in action.moves)
                if moves in seen:
                    continue
                seen.add(moves)
                merged.append(action)
            generated = tuple(merged)
        else:
            raise ValueError(f"unknown ACC generator id: {generator_id}")
        return baseline_actions + generated

    return callback


def main() -> None:
    v1._extra_callback = _composite_extra_callback
    v1.main()


if __name__ == "__main__":
    main()
