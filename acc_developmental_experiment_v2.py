from __future__ import annotations

from typing import Any, Callable

import acc_developmental_experiment as v1
from acc_substitution_generator import SubstitutionGenerator, source_conditioned_candidates
from realitygraph.acc import State


def _source_conditioned_extra_callback(
    generator_id: str | None,
    row: dict[str, Any],
    components: v1.AcquisitionComponents,
) -> Callable[[State], tuple[Any, ...]]:
    """V2 generator adapter: retain V1 search/controller, change only substitution reach.

    The action budget remains 48.  For each source row, those 48 substitutions
    are built from at most 12 deterministic conjugators conditioned on the row's
    Miller--Schupp word instead of taking an arbitrary prefix of the global V1
    enumeration.  Every emitted action is still compiled to primitive AC moves
    and replay-checked by ``SubstitutionGenerator`` and the V1 search engine.
    """
    recurrence = v1._recurrence_callback(row)
    structural = components.structural_generator
    _, _, source_word = v1._row_source(row)
    substitution = SubstitutionGenerator(
        source_conditioned_candidates(source_word, max_words=12),
        max_total=120,
        max_path_length=400,
    )

    def callback(state: State) -> tuple[Any, ...]:
        baseline_actions = tuple(recurrence(state))
        if generator_id is None:
            return baseline_actions
        if generator_id == "structural_macro":
            generated = structural.generate(state)[:8]
        elif generator_id == "substitution":
            generated = substitution.generate(state)[:48]
        else:
            raise ValueError(f"unknown ACC generator id: {generator_id}")
        return baseline_actions + tuple(generated)

    return callback


def main() -> None:
    # V1's search resolves _extra_callback dynamically from its module globals.
    # Patch that single extension point, then reuse the complete sealed CLI,
    # split/freeze/controller/verifier machinery unchanged.
    v1._extra_callback = _source_conditioned_extra_callback
    v1.main()


if __name__ == "__main__":
    main()
