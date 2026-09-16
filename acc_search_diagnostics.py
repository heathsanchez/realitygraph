from __future__ import annotations

import argparse
import heapq
import json
from itertools import count
from pathlib import Path
from typing import Any

from acc_capability_miner import canonical_bank, guard_for_state, mine_capabilities, restart_bank
from acc_open_ms_transfer import _load_open_ms
from acc_prospective_transfer import (
    STANDARD_TARGET,
    _apply_macro_checked,
    _bank_index,
    _heuristic,
    _load_trajectories,
    mine_start_macros,
    reconstruct_ms_state,
)
from realitygraph.acc import State


def diagnose_search(
    start: State,
    *,
    bank: list[dict[str, Any]],
    start_macros: list[tuple[int, ...]],
    budget: int,
    max_total: int = 120,
    max_path_length: int = 400,
) -> dict[str, Any]:
    """Mirror the current search exactly while exposing target-free progress metrics."""
    initial_heuristic = _heuristic(start)
    initial_total = len(start[0]) + len(start[1])
    best_heuristic = initial_heuristic
    min_total = initial_total
    best_depth_reached = 0
    capability_state_expansions = 0
    capability_macros_generated = 0

    if start == STANDARD_TARGET:
        return {
            "solved": True,
            "moves": [],
            "expansions": 0,
            "generated": 0,
            "initial_heuristic": initial_heuristic,
            "best_heuristic": best_heuristic,
            "min_total_length_reached": min_total,
            "best_depth_reached": 0,
            "capability_state_expansions": 0,
            "capability_macros_generated": 0,
        }

    index = _bank_index(bank)
    serial = count()
    queue: list[tuple[Any, ...]] = []
    heapq.heappush(queue, (initial_heuristic, 0, next(serial), start, ()))
    best_depth: dict[State, int] = {start: 0}
    expansions = 0
    generated = 0

    while queue and expansions < budget:
        score, depth, _, state, path = heapq.heappop(queue)
        if best_depth.get(state) != depth:
            continue
        expansions += 1
        if score < best_heuristic:
            best_heuristic = score
        min_total = min(min_total, len(state[0]) + len(state[1]))
        best_depth_reached = max(best_depth_reached, depth)

        if state == STANDARD_TARGET:
            return {
                "solved": True,
                "moves": list(path),
                "expansions": expansions,
                "generated": generated,
                "initial_heuristic": initial_heuristic,
                "best_heuristic": best_heuristic,
                "min_total_length_reached": min_total,
                "best_depth_reached": best_depth_reached,
                "capability_state_expansions": capability_state_expansions,
                "capability_macros_generated": capability_macros_generated,
            }

        guard_key = json.dumps(
            guard_for_state(state), sort_keys=True, separators=(",", ":")
        )
        caps = index.get(guard_key, ())[:8]
        if caps:
            capability_state_expansions += 1

        macros: list[tuple[tuple[int, ...], bool]] = [
            (tuple(int(m) for m in cap["macro"]), True) for cap in caps
        ]
        if not path:
            macros.extend((tuple(macro), False) for macro in start_macros)
        macros.extend(((move,), False) for move in range(14))

        seen_macros: set[tuple[int, ...]] = set()
        for macro, is_capability in macros:
            if macro in seen_macros:
                continue
            seen_macros.add(macro)
            new_depth = depth + len(macro)
            if new_depth > max_path_length:
                continue
            successor = _apply_macro_checked(state, macro, max_total)
            if successor is None:
                continue
            generated += 1
            if is_capability:
                capability_macros_generated += 1
            successor_score = _heuristic(successor)
            if successor_score < best_heuristic:
                best_heuristic = successor_score
            min_total = min(min_total, len(successor[0]) + len(successor[1]))
            best_depth_reached = max(best_depth_reached, new_depth)
            old_depth = best_depth.get(successor)
            if old_depth is not None and old_depth <= new_depth:
                continue
            best_depth[successor] = new_depth
            heapq.heappush(
                queue,
                (successor_score, new_depth, next(serial), successor, path + macro),
            )

    return {
        "solved": False,
        "moves": [],
        "expansions": expansions,
        "generated": generated,
        "initial_heuristic": initial_heuristic,
        "best_heuristic": best_heuristic,
        "min_total_length_reached": min_total,
        "best_depth_reached": best_depth_reached,
        "capability_state_expansions": capability_state_expansions,
        "capability_macros_generated": capability_macros_generated,
    }


def diagnose_open_ms(
    trajectories: list[dict[str, Any]],
    metadata_path: Path,
    *,
    budget: int,
) -> dict[str, Any]:
    bank = restart_bank(
        canonical_bank(
            mine_capabilities(
                trajectories, min_support=3, min_macro_len=2, max_macro_len=8
            )
        )
    )
    start_macros = mine_start_macros(trajectories, min_support=10)
    rows = _load_open_ms(metadata_path)

    records: list[dict[str, Any]] = []
    with_root_capability = 0
    with_capability_state = 0
    heuristic_improved = 0
    total_improved = 0
    total_capability_state_expansions = 0
    total_capability_macros_generated = 0

    index = _bank_index(bank)
    for row in rows:
        start = reconstruct_ms_state(row["n"], row["w_vector"])
        root_key = json.dumps(
            guard_for_state(start), sort_keys=True, separators=(",", ":")
        )
        root_caps = len(index.get(root_key, ()))
        with_root_capability += int(root_caps > 0)

        result = diagnose_search(
            start,
            bank=bank,
            start_macros=start_macros,
            budget=budget,
            max_total=120,
            max_path_length=400,
        )
        had_capability = result["capability_state_expansions"] > 0
        with_capability_state += int(had_capability)
        heuristic_improved += int(result["best_heuristic"] < result["initial_heuristic"])
        total_improved += int(
            result["min_total_length_reached"] < result["initial_heuristic"][1]
        )
        total_capability_state_expansions += result["capability_state_expansions"]
        total_capability_macros_generated += result["capability_macros_generated"]
        records.append(
            {
                "seq": row["seq"],
                "n": row["n"],
                "w_length": len(row["w_vector"]),
                "root_capabilities": root_caps,
                "initial_heuristic": list(result["initial_heuristic"]),
                "best_heuristic": list(result["best_heuristic"]),
                "min_total_length_reached": result["min_total_length_reached"],
                "best_depth_reached": result["best_depth_reached"],
                "capability_state_expansions": result["capability_state_expansions"],
                "capability_macros_generated": result["capability_macros_generated"],
                "expansions": result["expansions"],
                "generated": result["generated"],
            }
        )

    near_misses = sorted(
        records,
        key=lambda item: (
            item["best_heuristic"],
            item["min_total_length_reached"],
            -item["capability_state_expansions"],
            item["seq"],
        ),
    )[:25]

    return {
        "open_rows": len(rows),
        "budget": budget,
        "frozen_capabilities": len(bank),
        "start_macros": len(start_macros),
        "root_capability_presentations": with_root_capability,
        "searches_entering_capability_states": with_capability_state,
        "heuristic_improved_presentations": heuristic_improved,
        "total_length_improved_presentations": total_improved,
        "total_capability_state_expansions": total_capability_state_expansions,
        "total_capability_macros_generated": total_capability_macros_generated,
        "near_misses": near_misses,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trajectories", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--budget", type=int, default=1000)
    args = parser.parse_args()

    trajectories = _load_trajectories(args.trajectories)
    summary = diagnose_open_ms(trajectories, args.metadata, budget=args.budget)
    args.output.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
