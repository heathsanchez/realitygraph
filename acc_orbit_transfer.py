from __future__ import annotations

from typing import Any, Iterable

from acc_consequence_closure import build_suffix_closure
from acc_orbit_closure import build_orbit_closure, orbit_closure_search
from realitygraph.acc import State, replay

STANDARD_TARGET: State = ((1,), (2,))


def _state(value: Iterable[Iterable[int]]) -> State:
    words = tuple(tuple(int(x) for x in word) for word in value)
    if len(words) != 2:
        raise ValueError("ordinary AC state must contain exactly two relators")
    return words  # type: ignore[return-value]


def compare_orbit_on_split(
    acquisition: list[dict[str, Any]],
    heldout: list[dict[str, Any]],
    *,
    budget: int = 100,
) -> dict[str, Any]:
    exact = build_suffix_closure(acquisition)
    orbit = build_orbit_closure(exact)

    cold_solved = warm_solved = 0
    warm_only = cold_only = both = 0
    orbit_joins = 0
    cold_expansions_on_both = warm_expansions_on_both = 0
    ablation_mismatches = 0

    for trajectory in heldout:
        start = _state(trajectory["states"][0]["state"])
        cold = orbit_closure_search(
            start,
            orbit_closure={},
            bank=[],
            start_macros=[],
            budget=budget,
        )
        warm = orbit_closure_search(
            start,
            orbit_closure=orbit,
            bank=[],
            start_macros=[],
            budget=budget,
        )
        ablated = orbit_closure_search(
            start,
            orbit_closure={},
            bank=[],
            start_macros=[],
            budget=budget,
        )
        if ablated != cold:
            ablation_mismatches += 1

        if warm["solved"]:
            if replay(start, warm["moves"])[-1] != STANDARD_TARGET:
                raise AssertionError("orbit warm search returned invalid path")
            warm_solved += 1
            orbit_joins += int(bool(warm["orbit_join"]))
        if cold["solved"]:
            if replay(start, cold["moves"])[-1] != STANDARD_TARGET:
                raise AssertionError("orbit cold search returned invalid path")
            cold_solved += 1

        if cold["solved"] and warm["solved"]:
            both += 1
            cold_expansions_on_both += int(cold["expansions"])
            warm_expansions_on_both += int(warm["expansions"])
        elif warm["solved"]:
            warm_only += 1
        elif cold["solved"]:
            cold_only += 1

    return {
        "acquisition_presentations": len(acquisition),
        "heldout_presentations": len(heldout),
        "exact_states": len(exact),
        "orbit_classes": len(orbit),
        "budget": budget,
        "cold_solved": cold_solved,
        "warm_solved": warm_solved,
        "warm_only_solved": warm_only,
        "cold_only_solved": cold_only,
        "both_solved": both,
        "orbit_joins": orbit_joins,
        "cold_expansions_on_both": cold_expansions_on_both,
        "warm_expansions_on_both": warm_expansions_on_both,
        "ablation_mismatches": ablation_mismatches,
    }
