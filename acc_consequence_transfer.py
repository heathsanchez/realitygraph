from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import median
from typing import Any, Iterable

from acc_consequence_closure import (
    build_suffix_closure,
    canonical_closure,
    closure_search,
    restart_closure,
)
from acc_prospective_transfer import deterministic_split
from realitygraph.acc import State, replay

STANDARD_TARGET: State = ((1,), (2,))


def _state(value: Iterable[Iterable[int]]) -> State:
    words = tuple(tuple(int(x) for x in word) for word in value)
    if len(words) != 2:
        raise ValueError("ordinary AC state must contain exactly two relators")
    return words  # type: ignore[return-value]


def compare_closure_on_split(
    acquisition: list[dict[str, Any]],
    heldout: list[dict[str, Any]],
    *,
    budget: int = 100,
) -> dict[str, Any]:
    """Compare cold primitive search with exact retained consequence closure.

    Acquisition proofs are compiled into exact states with verified suffixes.
    The warm search gets no new heuristic and no new move generator: its only
    extra ability is to stop when it reaches an acquisition state and append
    that state's already-verified suffix.  The ablation is therefore exactly
    the same primitive search with the closure removed.
    """
    closure = build_suffix_closure(acquisition)
    closure_text = canonical_closure(closure)
    restarted = restart_closure(closure_text)
    exact_restart = canonical_closure(restarted) == closure_text

    cold_solved = 0
    warm_solved = 0
    warm_only = 0
    cold_only = 0
    both = 0
    closure_joins = 0
    cold_expansions_on_both = 0
    warm_expansions_on_both = 0
    ablation_mismatches = 0
    join_depths: list[int] = []
    suffix_lengths: list[int] = []

    for trajectory in heldout:
        start = _state(trajectory["states"][0]["state"])
        cold = closure_search(
            start,
            closure={},
            bank=[],
            start_macros=[],
            budget=budget,
        )
        warm = closure_search(
            start,
            closure=restarted,
            bank=[],
            start_macros=[],
            budget=budget,
        )
        ablated = closure_search(
            start,
            closure={},
            bank=[],
            start_macros=[],
            budget=budget,
        )
        if ablated != cold:
            ablation_mismatches += 1

        if warm["solved"]:
            if replay(start, warm["moves"])[-1] != STANDARD_TARGET:
                raise AssertionError(
                    f"closure search returned invalid path for {trajectory['training_id']}"
                )
            warm_solved += 1
            if warm["join_training_id"] is not None:
                closure_joins += 1
                join_depths.append(int(warm["join_depth"]))
                suffix_lengths.append(int(warm["retained_suffix_length"]))
        if cold["solved"]:
            if replay(start, cold["moves"])[-1] != STANDARD_TARGET:
                raise AssertionError(
                    f"cold search returned invalid path for {trajectory['training_id']}"
                )
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
        "closure_states": len(restarted),
        "budget": budget,
        "cold_solved": cold_solved,
        "warm_solved": warm_solved,
        "warm_only_solved": warm_only,
        "cold_only_solved": cold_only,
        "both_solved": both,
        "closure_joins": closure_joins,
        "cold_expansions_on_both": cold_expansions_on_both,
        "warm_expansions_on_both": warm_expansions_on_both,
        "ablation_mismatches": ablation_mismatches,
        "exact_restart": exact_restart,
        "join_depth_min": min(join_depths) if join_depths else None,
        "join_depth_median": median(join_depths) if join_depths else None,
        "join_depth_max": max(join_depths) if join_depths else None,
        "retained_suffix_median": median(suffix_lengths) if suffix_lengths else None,
    }


def audit_consequence_closure(
    trajectories: list[dict[str, Any]],
    *,
    budget: int = 100,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    acquisition, heldout = deterministic_split(
        trajectories, 0.70, "acc-proof-discovery-v1"
    )
    summary = compare_closure_on_split(acquisition, heldout, budget=budget)
    closure = restart_closure(canonical_closure(build_suffix_closure(acquisition)))
    return summary, closure


def _load_trajectories(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trajectories", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--closure", required=True, type=Path)
    parser.add_argument("--budget", type=int, default=100)
    args = parser.parse_args()

    trajectories = _load_trajectories(args.trajectories)
    summary, closure = audit_consequence_closure(
        trajectories,
        budget=args.budget,
    )
    args.summary.write_text(
        json.dumps(summary, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    args.closure.write_text(canonical_closure(closure), encoding="utf-8")
    print(json.dumps(summary, sort_keys=True, indent=2))

    if not summary["exact_restart"]:
        raise SystemExit("consequence closure restart was not byte-exact")
    if summary["ablation_mismatches"] != 0:
        raise SystemExit("consequence closure ablation did not restore cold search")
    if summary["warm_only_solved"] <= 0:
        raise SystemExit("consequence closure produced no prospective warm-only solve")
    if summary["warm_solved"] <= summary["cold_solved"]:
        raise SystemExit("consequence closure did not improve prospective solve count")


if __name__ == "__main__":
    main()
