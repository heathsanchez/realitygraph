from __future__ import annotations

import argparse
import csv
import importlib
import json
import sys
from pathlib import Path
from typing import Any, Iterable

from acc_capability_miner import canonical_bank, mine_capabilities, restart_bank
from acc_prospective_transfer import (
    _load_trajectories,
    _state,
    audit_heldout,
    best_first_search,
    mine_start_macros,
    reconstruct_ms_state,
)
from realitygraph.acc import State, apply_move, invert, replay

SWAP_RELATORS = (2, 0, 4, 3, 0, 1)
CONJ_MOVE = {
    0: {1: 6, -1: 7, 2: 8, -2: 9},
    1: {1: 10, -1: 11, 2: 12, -2: 13},
}


def _word_orbit(word: tuple[int, ...]) -> set[tuple[int, ...]]:
    if not word:
        return {()}
    inv = invert(word)
    return {
        variant[i:] + variant[:i]
        for variant in (word, inv)
        for i in range(len(variant))
    }


def presentation_orbit_key(state: State) -> tuple[tuple[int, ...], tuple[int, ...]]:
    return tuple(
        sorted((min(_word_orbit(state[0])), min(_word_orbit(state[1]))))
    )  # type: ignore[return-value]


def _relator_transform_path(
    state: State, index: int, target: tuple[int, ...]
) -> tuple[int, ...] | None:
    inv_move = index
    for invert_first in (False, True):
        base = apply_move(state, inv_move) if invert_first else state
        prefix = (inv_move,) if invert_first else ()
        if base[index] == target:
            return prefix
        for direction in ("left", "right"):
            current = base
            path = list(prefix)
            for _ in range(max(0, len(base[index]) - 1)):
                word = current[index]
                if not word:
                    break
                conjugator = -word[0] if direction == "left" else word[-1]
                move = CONJ_MOVE[index][conjugator]
                current = apply_move(current, move)
                path.append(move)
                if current[index] == target:
                    return tuple(path)
    return None


def find_orbit_bridge(source: State, target: State) -> tuple[int, ...]:
    if presentation_orbit_key(source) != presentation_orbit_key(target):
        raise ValueError(
            "presentations are not in the relator-order/rotation/inversion orbit"
        )
    for swap in (False, True):
        current = source
        path: list[int] = []
        if swap:
            for move in SWAP_RELATORS:
                current = apply_move(current, move)
                path.append(move)
        first = _relator_transform_path(current, 0, target[0])
        if first is None:
            continue
        for move in first:
            current = apply_move(current, move)
            path.append(move)
        second = _relator_transform_path(current, 1, target[1])
        if second is None:
            continue
        for move in second:
            current = apply_move(current, move)
            path.append(move)
        if current == target:
            return tuple(path)
    raise ValueError("orbit matched but no exact atomic AC bridge was found")


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


def _manifest_orbit_map(
    manifest: dict[str, Any],
) -> dict[tuple[tuple[int, ...], tuple[int, ...]], dict[str, Any]]:
    mapping: dict[tuple[tuple[int, ...], tuple[int, ...]], dict[str, Any]] = {}
    for challenge in manifest["challenges"]:
        if challenge["move_spec_version"] != "ac-r2-v1":
            continue
        state = _state(challenge["initial_relators"])
        key = presentation_orbit_key(state)
        if key in mapping:
            raise ValueError("duplicate AC presentation orbit in official manifest")
        mapping[key] = challenge
    return mapping


def _load_open_ms(metadata_path: Path) -> list[dict[str, Any]]:
    rows = []
    with metadata_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["status_at_freeze"] != "open":
                continue
            vector = (
                tuple(int(x) for x in row["w_vector"].split())
                if row["w_vector"].strip()
                else ()
            )
            rows.append(
                {"seq": int(row["seq"]), "n": int(row["n"]), "w_vector": vector}
            )
    return rows


def attack_open_ms(
    trajectories: list[dict[str, Any]],
    metadata_path: Path,
    manifest: dict[str, Any],
    *,
    official_tools: Path | None,
    budget: int,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    bank = mine_capabilities(
        trajectories, min_support=3, min_macro_len=2, max_macro_len=8
    )
    bank = restart_bank(canonical_bank(bank))
    start_macros = mine_start_macros(trajectories, min_support=10)
    exact_map = _manifest_state_map(manifest)
    orbit_map = _manifest_orbit_map(manifest)
    open_rows = _load_open_ms(metadata_path)

    verify = None
    if official_tools is not None:
        sys.path.insert(0, str(official_tools.resolve()))
        verify = importlib.import_module("verifier.core").verify

    solved: list[dict[str, Any]] = []
    unmatched: list[dict[str, Any]] = []
    exact_matches = 0
    orbit_matches = 0
    bridged = 0
    bridge_moves_total = 0
    bridge_moves_max = 0

    for row in open_rows:
        native_start = reconstruct_ms_state(row["n"], row["w_vector"])
        challenge = exact_map.get(native_start)
        bridge: tuple[int, ...] = ()
        if challenge is not None:
            exact_matches += 1
            orbit_matches += 1
        else:
            challenge = orbit_map.get(presentation_orbit_key(native_start))
            if challenge is None:
                unmatched.append(row)
                continue
            orbit_matches += 1
            challenge_start = _state(challenge["initial_relators"])
            bridge = find_orbit_bridge(challenge_start, native_start)
            if replay(challenge_start, bridge)[-1] != native_start:
                raise AssertionError(
                    f"bridge replay mismatch for {challenge['challenge_id']}"
                )
            bridged += 1
            bridge_moves_total += len(bridge)
            bridge_moves_max = max(bridge_moves_max, len(bridge))

        result = best_first_search(
            native_start,
            bank=bank,
            start_macros=start_macros,
            budget=budget,
            max_total=120,
            max_path_length=400,
        )
        if not result["solved"]:
            continue

        full_moves = list(bridge) + result["moves"]
        receipt = None
        if verify is not None:
            receipt = verify(
                challenge,
                full_moves,
                "ac-r2-v1",
                manifest["limits"],
            )
            if not receipt["ok"]:
                raise AssertionError(
                    "official verifier rejected generated path for "
                    f"{challenge['challenge_id']}: {receipt}"
                )
        solved.append(
            {
                "challenge_id": challenge["challenge_id"],
                "seq": row["seq"],
                "n": row["n"],
                "w_vector": list(row["w_vector"]),
                "bridge_moves": list(bridge),
                "search_moves": result["moves"],
                "moves": full_moves,
                "length": len(full_moves),
                "search_expansions": result["expansions"],
                "official_receipt": receipt,
            }
        )

    summary = {
        "open_metadata_rows": len(open_rows),
        "exact_manifest_matches": exact_matches,
        "orbit_manifest_matches": orbit_matches,
        "bridged_manifest_matches": bridged,
        "unmatched_open_rows": len(unmatched),
        "bridge_moves_total": bridge_moves_total,
        "bridge_moves_max": bridge_moves_max,
        "frozen_capabilities": len(bank),
        "frozen_start_macros": len(start_macros),
        "search_budget": budget,
        "open_solved": len(solved),
        "officially_verified_open_solved": sum(
            1
            for item in solved
            if item["official_receipt"] and item["official_receipt"]["ok"]
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

    full_bank = mine_capabilities(
        trajectories, min_support=3, min_macro_len=2, max_macro_len=8
    )
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
    args.summary.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {"audit": audit, "open_transfer": open_summary}, indent=2, sort_keys=True
        )
    )


if __name__ == "__main__":
    main()
