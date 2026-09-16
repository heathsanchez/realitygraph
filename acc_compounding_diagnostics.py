from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Callable

import acc_developmental_experiment as v1
import acc_developmental_experiment_v2 as v2
import acc_developmental_experiment_v3 as v3
from acc_consequence_closure import STANDARD_TARGET
from acc_developmental_search import developmental_search
from acc_prospective_transfer import _load_trajectories, _state
from acc_scientific_split import freeze_split, select_rows
from realitygraph.acc import State, replay


DEFAULT_SEED = "acc-developmental-system-v1"
VARIANT_ORDER = ("baseline", "v1", "v2", "v3")


def serialize_verified_solution(start: State, result: dict[str, Any]) -> dict[str, Any]:
    """Return the exact local certificate payload, rejecting false solved claims."""
    moves = [int(move) for move in result.get("moves", ())]
    solved = bool(result.get("solved", False))
    if solved:
        endpoint = replay(start, moves)[-1]
        assert endpoint == STANDARD_TARGET, "solved ACC result does not replay to target"
    return {
        "local_solved": solved,
        "moves": moves,
        "path_length": len(moves),
        "expansions": int(result.get("expansions", 0)),
        "generator_uses": {
            str(key): int(value)
            for key, value in sorted(result.get("generator_uses", {}).items())
        },
    }


def _callback_for(
    variant: str,
    row: dict[str, Any],
    components: v1.AcquisitionComponents,
) -> Callable[[State], tuple[Any, ...]]:
    if variant == "baseline":
        return v1._extra_callback(None, row, components)
    if variant == "v1":
        return v1._extra_callback("substitution", row, components)
    if variant == "v2":
        return v2._source_conditioned_extra_callback("substitution", row, components)
    if variant == "v3":
        return v3._composite_extra_callback("substitution", row, components)
    raise ValueError(f"unknown diagnostic variant: {variant}")


def _search_variant(
    start: State,
    row: dict[str, Any],
    components: v1.AcquisitionComponents,
    *,
    variant: str,
    budget: int,
) -> dict[str, Any]:
    return developmental_search(
        start,
        orbit_closure=components.orbit_closure,
        bank=components.bank,
        start_macros=components.start_macros,
        budget=budget,
        extra_actions=_callback_for(variant, row, components),
        max_total=120,
        max_path_length=400,
    )


def _ngrams(moves: tuple[int, ...] | list[int], lo: int = 2, hi: int = 8) -> set[tuple[int, ...]]:
    seq = tuple(int(move) for move in moves)
    grams: set[tuple[int, ...]] = set()
    for width in range(lo, min(hi, len(seq)) + 1):
        grams.update(seq[i : i + width] for i in range(len(seq) - width + 1))
    return grams


def _enriched_ngrams(
    positive_rows: list[dict[str, Any]],
    negative_rows: list[dict[str, Any]],
    *,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Rank exact official-proof n-grams by support enrichment in positives."""
    positive = Counter()
    negative = Counter()
    for row in positive_rows:
        positive.update(_ngrams(row.get("moves", ())))
    for row in negative_rows:
        negative.update(_ngrams(row.get("moves", ())))
    p_total = max(1, len(positive_rows))
    n_total = max(1, len(negative_rows))
    rows: list[dict[str, Any]] = []
    for gram, p_support in positive.items():
        n_support = int(negative.get(gram, 0))
        p_rate = p_support / p_total
        n_rate = n_support / n_total
        rows.append(
            {
                "moves": list(gram),
                "length": len(gram),
                "positive_support": int(p_support),
                "negative_support": n_support,
                "positive_rate": p_rate,
                "negative_rate": n_rate,
                "rate_gap": p_rate - n_rate,
            }
        )
    rows.sort(
        key=lambda item: (
            -float(item["rate_gap"]),
            -int(item["positive_support"]),
            int(item["negative_support"]),
            -int(item["length"]),
            tuple(item["moves"]),
        )
    )
    return rows[:limit]


def run_diagnostics(
    trajectories: list[dict[str, Any]],
    *,
    training_manifest_path: Path,
    official_tools: Path,
    budget: int,
    seed: str = DEFAULT_SEED,
) -> dict[str, Any]:
    """Compare sealed ACC generations on the same untouched future families.

    Acquisition rows alone build retained capabilities.  The diagnostic then
    evaluates baseline/V1/V2/V3 on the frozen future split, official-verifies
    every claimed solution, and mines only the *published certified* future
    trajectories to explain the remaining V3 residual.
    """
    split = freeze_split(trajectories, seed)
    acquisition = select_rows(trajectories, split.acquisition_ids)
    future = select_rows(trajectories, split.future_ids)
    components = v1._build_components(acquisition)
    verify, challenges, limits = v1._training_verifier(
        training_manifest_path, official_tools
    )

    verified_by_variant = {variant: 0 for variant in VARIANT_ORDER}
    rows: list[dict[str, Any]] = []
    future_by_id = {str(row["training_id"]): row for row in future}

    for row in future:
        start = _state(row["states"][0]["state"])
        variants: dict[str, Any] = {}
        for variant in VARIANT_ORDER:
            result = _search_variant(
                start, row, components, variant=variant, budget=budget
            )
            payload = serialize_verified_solution(start, result)
            official_ok, receipt = v1._verified_training_solve(
                row, result, verify, challenges, limits
            )
            if payload["local_solved"] and not official_ok:
                raise AssertionError(
                    f"local ACC solution rejected by official verifier: "
                    f"{row['training_id']} {variant}"
                )
            payload["official_verified"] = bool(official_ok)
            payload["receipt"] = receipt
            variants[variant] = payload
            verified_by_variant[variant] += int(official_ok)

        rows.append(
            {
                "training_id": str(row["training_id"]),
                "n": row.get("n"),
                "w_vector": [int(x) for x in row.get("w_vector", ())],
                "variants": variants,
            }
        )

    v3_only = [
        item["training_id"]
        for item in rows
        if item["variants"]["v3"]["official_verified"]
        and not item["variants"]["v2"]["official_verified"]
    ]
    v3_misses = [
        item["training_id"]
        for item in rows
        if not item["variants"]["v3"]["official_verified"]
    ]
    v3_hits = [
        item["training_id"]
        for item in rows
        if item["variants"]["v3"]["official_verified"]
    ]

    miss_rows = [future_by_id[training_id] for training_id in v3_misses]
    hit_rows = [future_by_id[training_id] for training_id in v3_hits]
    v3_only_rows = [future_by_id[training_id] for training_id in v3_only]
    non_v3_only_rows = [
        row for row in future if str(row["training_id"]) not in set(v3_only)
    ]

    return {
        "version": "acc-compounding-diagnostics-v1",
        "seed": seed,
        "split_digest": split.manifest_digest,
        "split": {
            "acquisition": len(acquisition),
            "future": len(future),
        },
        "budget": int(budget),
        "component_digest": components.digest,
        "verified_by_variant": verified_by_variant,
        "v3_only": v3_only,
        "v3_misses": v3_misses,
        # Top-level common_ngrams deliberately means motifs enriched in the
        # remaining residual, because those are candidates for the next
        # representation/action language.  They come from certified paths only.
        "common_ngrams": _enriched_ngrams(miss_rows, hit_rows),
        "v3_only_common_ngrams": _enriched_ngrams(
            v3_only_rows, non_v3_only_rows
        ),
        "rows": rows,
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

    trajectories = _load_trajectories(args.trajectories)
    summary = run_diagnostics(
        trajectories,
        training_manifest_path=args.training_manifest,
        official_tools=args.official_tools,
        budget=args.budget,
        seed=args.seed,
    )
    args.summary.write_text(
        json.dumps(summary, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
