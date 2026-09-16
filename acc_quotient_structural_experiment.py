from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

import acc_developmental_experiment as v1
import acc_developmental_experiment_v3 as v3
from acc_developmental_search import developmental_search
from acc_prospective_transfer import _load_trajectories, _state
from acc_quotient_structural_generator import (
    GUARD_KINDS,
    QuotientStructuralGenerator,
    mine_quotient_structural_macros,
)
from acc_scientific_split import freeze_split, select_rows
from realitygraph.acc import State


DEFAULT_SEED = "acc-developmental-system-v1"


def baseline_preserving_choice(
    baseline: dict[str, Any], candidate: dict[str, Any]
) -> dict[str, Any]:
    """Candidate may add a rescue, but can never replace a baseline success."""
    if bool(baseline.get("solved", False)):
        return baseline
    if bool(candidate.get("solved", False)):
        return candidate
    return baseline


def _combined_callback(
    row: dict[str, Any],
    components: v1.AcquisitionComponents,
    quotient: QuotientStructuralGenerator,
) -> Callable[[State], tuple[Any, ...]]:
    v3_callback = v3._composite_extra_callback("substitution", row, components)

    def callback(state: State) -> tuple[Any, ...]:
        merged: list[Any] = []
        seen: set[tuple[int, ...]] = set()
        for action in tuple(v3_callback(state)) + tuple(quotient.generate(state)[:16]):
            moves = tuple(int(move) for move in action.moves)
            if moves in seen:
                continue
            seen.add(moves)
            merged.append(action)
        return tuple(merged)

    return callback


def _search_v3(
    start: State,
    row: dict[str, Any],
    components: v1.AcquisitionComponents,
    *,
    budget: int,
) -> dict[str, Any]:
    return developmental_search(
        start,
        orbit_closure=components.orbit_closure,
        bank=components.bank,
        start_macros=components.start_macros,
        budget=budget,
        extra_actions=v3._composite_extra_callback("substitution", row, components),
        max_total=120,
        max_path_length=400,
    )


def _search_v5(
    start: State,
    row: dict[str, Any],
    components: v1.AcquisitionComponents,
    quotient: QuotientStructuralGenerator,
    *,
    budget: int,
) -> dict[str, Any]:
    return developmental_search(
        start,
        orbit_closure=components.orbit_closure,
        bank=components.bank,
        start_macros=components.start_macros,
        budget=budget,
        extra_actions=_combined_callback(row, components, quotient),
        max_total=120,
        max_path_length=400,
    )


def run_quotient_evaluation(
    trajectories: list[dict[str, Any]],
    *,
    training_manifest_path: Path,
    official_tools: Path,
    budget: int = 100,
    seed: str = DEFAULT_SEED,
) -> dict[str, Any]:
    """Post-diagnostic evaluation of coarser structural applicability quotients.

    Only acquisition trajectories build the quotient macro banks.  V3 is the
    immutable baseline on the frozen future set.  A V5 search is attempted only
    when V3 failed, and every candidate rescue is checked by the official ACC
    verifier.  This is engineering evidence because the V4 diagnostic inspected
    the same future set; it is not represented as a fresh prospective result.
    """
    split = freeze_split(trajectories, seed)
    acquisition = select_rows(trajectories, split.acquisition_ids)
    future = select_rows(trajectories, split.future_ids)
    components = v1._build_components(acquisition)
    verify, challenges, limits = v1._training_verifier(
        training_manifest_path, official_tools
    )

    banks = {
        kind: mine_quotient_structural_macros(
            acquisition,
            guard_kind=kind,
            min_support=3,
            min_macro_len=2,
            max_macro_len=8,
        )
        for kind in GUARD_KINDS
    }
    generators = {
        kind: QuotientStructuralGenerator(bank, guard_kind=kind, max_actions=48)
        for kind, bank in banks.items()
    }

    baseline_by_id: dict[str, tuple[dict[str, Any], bool, dict[str, Any] | None]] = {}
    baseline_verified = 0
    for row in future:
        start = _state(row["states"][0]["state"])
        result = _search_v3(start, row, components, budget=budget)
        ok, receipt = v1._verified_training_solve(
            row, result, verify, challenges, limits
        )
        if bool(result["solved"]) and not ok:
            raise AssertionError(f"V3 local solve rejected: {row['training_id']}")
        baseline_by_id[str(row["training_id"])] = (result, ok, receipt)
        baseline_verified += int(ok)

    guard_summaries: dict[str, Any] = {}
    for kind in GUARD_KINDS:
        generator = generators[kind]
        rescues = 0
        candidate_invocations = 0
        events: list[dict[str, Any]] = []
        for row in future:
            training_id = str(row["training_id"])
            baseline, baseline_ok, baseline_receipt = baseline_by_id[training_id]
            if baseline_ok:
                events.append(
                    {
                        "training_id": training_id,
                        "baseline_verified": True,
                        "candidate_invoked": False,
                        "chosen": "v3",
                        "baseline_receipt": baseline_receipt,
                    }
                )
                continue

            candidate_invocations += 1
            start = _state(row["states"][0]["state"])
            candidate = _search_v5(
                start, row, components, generator, budget=budget
            )
            candidate_ok, candidate_receipt = v1._verified_training_solve(
                row, candidate, verify, challenges, limits
            )
            if bool(candidate["solved"]) and not candidate_ok:
                raise AssertionError(
                    f"V5 local solve rejected: {training_id} guard={kind}"
                )
            chosen = baseline_preserving_choice(baseline, candidate)
            rescue = (not baseline_ok) and candidate_ok and chosen is candidate
            rescues += int(rescue)
            events.append(
                {
                    "training_id": training_id,
                    "baseline_verified": False,
                    "candidate_invoked": True,
                    "candidate_local_solved": bool(candidate["solved"]),
                    "candidate_official_verified": bool(candidate_ok),
                    "rescue": bool(rescue),
                    "chosen": "v5" if rescue else "v3",
                    "candidate_expansions": int(candidate["expansions"]),
                    "generator_uses": {
                        str(key): int(value)
                        for key, value in sorted(candidate.get("generator_uses", {}).items())
                    },
                    "candidate_receipt": candidate_receipt,
                }
            )

        guard_summaries[kind] = {
            "bank_size": len(banks[kind]),
            "candidate_invocations": candidate_invocations,
            "rescues": rescues,
            "harms": 0,
            "warm_verified": baseline_verified + rescues,
            "events": events,
        }

    selected_kind = min(
        GUARD_KINDS,
        key=lambda kind: (
            -int(guard_summaries[kind]["rescues"]),
            int(guard_summaries[kind]["bank_size"]),
            GUARD_KINDS.index(kind),
        ),
    )
    return {
        "version": "acc-developmental-v5-quotient-structural",
        "evidence_class": "post-diagnostic-engineering",
        "seed": seed,
        "split_digest": split.manifest_digest,
        "split": {"acquisition": len(acquisition), "future": len(future)},
        "budget": int(budget),
        "component_digest": components.digest,
        "v3_verified": baseline_verified,
        "selected_guard_kind": selected_kind,
        "selected_warm_verified": guard_summaries[selected_kind]["warm_verified"],
        "selected_rescues": guard_summaries[selected_kind]["rescues"],
        "guards": guard_summaries,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trajectories", type=Path, required=True)
    parser.add_argument("--training-manifest", type=Path, required=True)
    parser.add_argument("--official-tools", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--budget", type=int, default=100)
    parser.add_argument("--seed", default=DEFAULT_SEED)
    args = parser.parse_args()

    summary = run_quotient_evaluation(
        _load_trajectories(args.trajectories),
        training_manifest_path=args.training_manifest,
        official_tools=args.official_tools,
        budget=args.budget,
        seed=args.seed,
    )
    args.summary.write_text(
        json.dumps(summary, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print("v3_verified", summary["v3_verified"])
    print("selected_guard_kind", summary["selected_guard_kind"])
    print("selected_warm_verified", summary["selected_warm_verified"])
    print("selected_rescues", summary["selected_rescues"])
    for kind in GUARD_KINDS:
        item = summary["guards"][kind]
        print(
            "guard",
            kind,
            "bank_size",
            item["bank_size"],
            "rescues",
            item["rescues"],
            "warm_verified",
            item["warm_verified"],
        )


if __name__ == "__main__":
    main()
