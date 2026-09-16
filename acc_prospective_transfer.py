from __future__ import annotations

import argparse
import csv
import hashlib
import heapq
import importlib
import json
import sys
from collections import Counter
from itertools import count
from pathlib import Path
from typing import Any, Iterable

from acc_capability_miner import (
    applicable_capabilities,
    canonical_bank,
    guard_for_state,
    mine_capabilities,
    restart_bank,
)
from realitygraph.acc import State, apply_move, free_reduce, invert, state_observables

STANDARD_TARGET: State = ((1,), (2,))


def _state(value: Iterable[Iterable[int]]) -> State:
    words = tuple(tuple(int(x) for x in word) for word in value)
    if len(words) != 2:
        raise ValueError("ordinary AC state must contain exactly two relators")
    return words  # type: ignore[return-value]


def deterministic_split(
    rows: list[dict[str, Any]], fraction: float, salt: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not 0.0 < fraction < 1.0:
        raise ValueError("fraction must be between zero and one")
    ordered = sorted(
        rows,
        key=lambda row: (
            hashlib.sha256(f"{salt}|{row['training_id']}".encode()).digest(),
            row["training_id"],
        ),
    )
    cut = max(1, min(len(ordered) - 1, int(round(fraction * len(ordered)))))
    return ordered[:cut], ordered[cut:]


def reconstruct_ms_state(n: int, w_vector: Iterable[int]) -> State:
    if n < 1:
        raise ValueError("Miller-Schupp n must be positive")
    w = tuple(int(x) for x in w_vector)
    r0 = free_reduce((-1,) + (2,) * n + (1,) + (-2,) * (n + 1))
    r1 = free_reduce((1,) + invert(w))
    return r0, r1


def _heuristic(state: State) -> tuple[int, int, int]:
    obs = state_observables(state)
    total = int(obs["total_length"])
    exps = obs["exponent_sums"]
    target = ((1, 0), (0, 1))
    exp_distance = sum(
        abs(int(exps[i][j]) - target[i][j])
        for i in range(2)
        for j in range(2)
    )
    singleton_penalty = sum(0 if state[i] == STANDARD_TARGET[i] else 1 for i in range(2))
    return (total + exp_distance + singleton_penalty, total, exp_distance)


def _apply_macro_checked(
    state: State, macro: Iterable[int], max_total: int
) -> State | None:
    current = state
    for move in macro:
        current = apply_move(current, int(move))
        if len(current[0]) + len(current[1]) > max_total:
            return None
    return current


def _bank_index(bank: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for cap in bank:
        key = json.dumps(cap["guard"], sort_keys=True, separators=(",", ":"))
        out.setdefault(key, []).append(cap)
    for caps in out.values():
        caps.sort(
            key=lambda cap: (
                cap["max_total_length_delta"],
                -cap["support"],
                len(cap["macro"]),
                cap["id"],
            )
        )
    return out


def best_first_search(
    start: State,
    *,
    bank: list[dict[str, Any]],
    start_macros: list[tuple[int, ...]],
    budget: int,
    max_total: int = 120,
    max_path_length: int = 400,
) -> dict[str, Any]:
    if start == STANDARD_TARGET:
        return {"solved": True, "moves": [], "expansions": 0, "generated": 0}

    index = _bank_index(bank)
    serial = count()
    queue: list[tuple[Any, ...]] = []
    heapq.heappush(queue, (_heuristic(start), 0, next(serial), start, ()))
    best_depth: dict[State, int] = {start: 0}
    expansions = 0
    generated = 0

    while queue and expansions < budget:
        _, depth, _, state, path = heapq.heappop(queue)
        if best_depth.get(state) != depth:
            continue
        expansions += 1
        if state == STANDARD_TARGET:
            return {
                "solved": True,
                "moves": list(path),
                "expansions": expansions,
                "generated": generated,
            }

        macros: list[tuple[int, ...]] = []
        guard_key = json.dumps(guard_for_state(state), sort_keys=True, separators=(",", ":"))
        for cap in index.get(guard_key, ())[:8]:
            macros.append(tuple(int(m) for m in cap["macro"]))
        if not path:
            macros.extend(start_macros)
        macros.extend((move,) for move in range(14))

        seen_macros: set[tuple[int, ...]] = set()
        for macro in macros:
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
            old_depth = best_depth.get(successor)
            if old_depth is not None and old_depth <= new_depth:
                continue
            best_depth[successor] = new_depth
            heapq.heappush(
                queue,
                (_heuristic(successor), new_depth, next(serial), successor, path + macro),
            )

    return {"solved": False, "moves": [], "expansions": expansions, "generated": generated}


def mine_start_macros(
    trajectories: list[dict[str, Any]],
    *,
    min_support: int = 10,
    min_len: int = 2,
    max_len: int = 8,
) -> list[tuple[int, ...]]:
    counts: Counter[tuple[int, ...]] = Counter()
    for trajectory in trajectories:
        moves = tuple(int(m) for m in trajectory["moves"])
        for length in range(min_len, min(max_len, len(moves)) + 1):
            counts[moves[:length]] += 1
    retained = [macro for macro, support in counts.items() if support >= min_support]
    return sorted(retained, key=lambda macro: (-counts[macro], -len(macro), macro))


def _exact_macro_reuse_metrics(
    heldout: list[dict[str, Any]], bank: list[dict[str, Any]]
) -> dict[str, int]:
    presentations_with_applicable = 0
    presentations_with_exact_reuse = 0
    applicable_events = 0
    exact_reuse_events = 0
    atomic_moves_covered = 0

    for trajectory in heldout:
        had_applicable = False
        had_exact = False
        moves = trajectory["moves"]
        for index, record in enumerate(trajectory["states"][:-1]):
            state = _state(record["state"])
            matches = applicable_capabilities(state, bank)
            if matches:
                had_applicable = True
                applicable_events += 1
            exact_lengths = []
            for cap in matches:
                macro = cap["macro"]
                if moves[index : index + len(macro)] == macro:
                    exact_lengths.append(len(macro))
            if exact_lengths:
                had_exact = True
                exact_reuse_events += 1
                atomic_moves_covered += max(exact_lengths)
        presentations_with_applicable += int(had_applicable)
        presentations_with_exact_reuse += int(had_exact)

    return {
        "presentations_with_applicable_capability": presentations_with_applicable,
        "presentations_with_exact_reuse": presentations_with_exact_reuse,
        "applicable_state_events": applicable_events,
        "exact_macro_reuse_events": exact_reuse_events,
        "atomic_moves_covered_by_longest_exact_macros": atomic_moves_covered,
    }


def audit_heldout(
    trajectories: list[dict[str, Any]],
    *,
    budget: int = 100,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[tuple[int, ...]]]:
    phase_a, heldout = deterministic_split(trajectories, 0.70, "acc-proof-discovery-v1")
    bank = mine_capabilities(phase_a, min_support=3, min_macro_len=2, max_macro_len=8)
    bank_text = canonical_bank(bank)
    restarted = restart_bank(bank_text)
    if canonical_bank(restarted) != bank_text:
        raise AssertionError("capability restart was not byte-exact")
    start_macros = mine_start_macros(phase_a, min_support=10)

    reuse = _exact_macro_reuse_metrics(heldout, restarted)
    cold_solved = 0
    warm_solved = 0
    warm_only = 0
    cold_only = 0
    both = 0
    cold_expansions = 0
    warm_expansions = 0
    ablation_mismatches = 0

    for trajectory in heldout:
        start = _state(trajectory["states"][0]["state"])
        cold = best_first_search(start, bank=[], start_macros=[], budget=budget)
        warm = best_first_search(start, bank=restarted, start_macros=start_macros, budget=budget)
        ablated = best_first_search(start, bank=[], start_macros=[], budget=budget)
        if ablated != cold:
            ablation_mismatches += 1
        cold_solved += int(cold["solved"])
        warm_solved += int(warm["solved"])
        if cold["solved"] and warm["solved"]:
            both += 1
            cold_expansions += cold["expansions"]
            warm_expansions += warm["expansions"]
        elif warm["solved"]:
            warm_only += 1
        elif cold["solved"]:
            cold_only += 1

    summary = {
        "phase_a_presentations": len(phase_a),
        "heldout_presentations": len(heldout),
        "capabilities": len(restarted),
        "start_macros": len(start_macros),
        "budget": budget,
        "cold_solved": cold_solved,
        "warm_solved": warm_solved,
        "warm_only_solved": warm_only,
        "cold_only_solved": cold_only,
        "both_solved": both,
        "cold_expansions_on_both": cold_expansions,
        "warm_expansions_on_both": warm_expansions,
        "ablation_mismatches": ablation_mismatches,
        "exact_restart": True,
        **reuse,
    }
    return summary, restarted, start_macros


def _load_trajectories(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _manifest_state_map(manifest: dict[str, Any]) -> dict[State, dict[str, Any]]:
    mapping: dict[State, dict[str, Any]] = {}
    for challenge in manifest["challenges"]:
        if challenge["move_spec_version"] != "ac-r2-v1":
            continue
        state = _state(challenge["initial_relators"])
        if state in mapping:
            raise ValueError("duplicate exact AC state in official manifest")
        mapping[state] = challenge
    return mapping


def _load_open_ms(metadata_path: Path) -> list[dict[str, Any]]:
    rows = []
    with metadata_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["status_at_freeze"] != "open":
                continue
            vector = tuple(int(x) for x in row["w_vector"].split()) if row["w_vector"].strip() else ()
            rows.append({"seq": int(row["seq"]), "n": int(row["n"]), "w_vector": vector})
    return rows


def attack_open_ms(
    trajectories: list[dict[str, Any]],
    metadata_path: Path,
    manifest: dict[str, Any],
    *,
    official_tools: Path | None,
    budget: int,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    bank = mine_capabilities(trajectories, min_support=3, min_macro_len=2, max_macro_len=8)
    bank = restart_bank(canonical_bank(bank))
    start_macros = mine_start_macros(trajectories, min_support=10)
    state_map = _manifest_state_map(manifest)
    open_rows = _load_open_ms(metadata_path)

    verify = None
    if official_tools is not None:
        sys.path.insert(0, str(official_tools.resolve()))
        core = importlib.import_module("verifier.core")
        verify = core.verify

    solved: list[dict[str, Any]] = []
    unmatched: list[dict[str, Any]] = []
    for row in open_rows:
        start = reconstruct_ms_state(row["n"], row["w_vector"])
        challenge = state_map.get(start)
        if challenge is None:
            unmatched.append(row)
            continue
        result = best_first_search(
            start,
            bank=bank,
            start_macros=start_macros,
            budget=budget,
            max_total=120,
            max_path_length=400,
        )
        if not result["solved"]:
            continue
        receipt = None
        if verify is not None:
            receipt = verify(
                challenge,
                result["moves"],
                "ac-r2-v1",
                manifest["limits"],
            )
            if not receipt["ok"]:
                raise AssertionError(
                    f"official verifier rejected generated path for {challenge['challenge_id']}: {receipt}"
                )
        solved.append(
            {
                "challenge_id": challenge["challenge_id"],
                "seq": row["seq"],
                "n": row["n"],
                "w_vector": list(row["w_vector"]),
                "moves": result["moves"],
                "length": len(result["moves"]),
                "search_expansions": result["expansions"],
                "official_receipt": receipt,
            }
        )

    summary = {
        "open_metadata_rows": len(open_rows),
        "exact_manifest_matches": len(open_rows) - len(unmatched),
        "unmatched_open_rows": len(unmatched),
        "frozen_capabilities": len(bank),
        "frozen_start_macros": len(start_macros),
        "search_budget": budget,
        "open_solved": len(solved),
        "officially_verified_open_solved": sum(
            1 for item in solved if item["official_receipt"] and item["official_receipt"]["ok"]
        ),
    }
    return summary, solved, unmatched


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trajectories", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--official-tools", type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--bank", required=True, type=Path)
    parser.add_argument("--submission", required=True, type=Path)
    parser.add_argument("--audit-budget", type=int, default=100)
    parser.add_argument("--open-budget", type=int, default=3000)
    args = parser.parse_args()

    trajectories = _load_trajectories(args.trajectories)
    audit, _, _ = audit_heldout(trajectories, budget=args.audit_budget)
    if audit["ablation_mismatches"] != 0:
        raise SystemExit("lineage ablation did not restore cold baseline")
    if audit["exact_macro_reuse_events"] <= 0:
        raise SystemExit("no held-out exact capability reuse events")

    full_bank = mine_capabilities(trajectories, min_support=3, min_macro_len=2, max_macro_len=8)
    bank_text = canonical_bank(full_bank)
    args.bank.write_text(bank_text, encoding="utf-8")
    if canonical_bank(restart_bank(bank_text)) != bank_text:
        raise SystemExit("full capability bank restart mismatch")

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    open_summary, solved, unmatched = attack_open_ms(
        trajectories,
        args.metadata,
        manifest,
        official_tools=args.official_tools,
        budget=args.open_budget,
    )

    args.submission.write_text(
        "\n".join(
            f"{item['challenge_id']}: [{','.join(str(m) for m in item['moves'])}]"
            for item in solved
            if item["official_receipt"] is None or item["official_receipt"]["ok"]
        )
        + ("\n" if solved else ""),
        encoding="utf-8",
    )

    summary = {
        "audit": audit,
        "open_transfer": open_summary,
        "open_solutions": solved,
        "unmatched_open_rows": unmatched,
    }
    args.summary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"audit": audit, "open_transfer": open_summary}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
