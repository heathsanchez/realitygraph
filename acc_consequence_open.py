from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path
from typing import Any

from acc_capability_miner import canonical_bank, mine_capabilities, restart_bank
from acc_consequence_closure import (
    build_suffix_closure,
    canonical_closure,
    closure_search,
    restart_closure,
)
from acc_open_ms_transfer import (
    _load_open_ms,
    _manifest_orbit_map,
    _manifest_state_map,
    find_orbit_bridge,
    presentation_orbit_key,
)
from acc_prospective_transfer import _state, mine_start_macros, reconstruct_ms_state
from realitygraph.acc import replay


def attack_open_rows(
    trajectories: list[dict[str, Any]],
    open_rows: list[dict[str, Any]],
    manifest: dict[str, Any],
    *,
    official_tools: Path | None,
    budget: int,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Attack open MS rows using only frozen, verifier-backed consequences.

    Every known training state is retained with an exact primitive-move suffix
    to the ordered standard target. Search may terminate at any such state and
    splice that suffix. Existing guarded macros remain search accelerators, but
    every final candidate is still a plain list of official AC primitive moves.
    """
    closure = restart_closure(canonical_closure(build_suffix_closure(trajectories)))
    bank = restart_bank(
        canonical_bank(
            mine_capabilities(
                trajectories,
                min_support=3,
                min_macro_len=2,
                max_macro_len=8,
            )
        )
    )
    start_macros = mine_start_macros(trajectories, min_support=10)
    exact_map = _manifest_state_map(manifest)
    orbit_map = _manifest_orbit_map(manifest)

    verify = None
    if official_tools is not None:
        sys.path.insert(0, str(official_tools.resolve()))
        verify = importlib.import_module("verifier.core").verify

    solved: list[dict[str, Any]] = []
    unmatched: list[dict[str, Any]] = []
    exact_matches = 0
    orbit_matches = 0
    bridged = 0
    closure_join_solved = 0

    for row in open_rows:
        native_start = reconstruct_ms_state(int(row["n"]), row["w_vector"])
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

        result = closure_search(
            native_start,
            closure=closure,
            bank=bank,
            start_macros=start_macros,
            budget=budget,
            max_total=120,
            max_path_length=400,
        )
        if not result["solved"]:
            continue

        search_moves = [int(move) for move in result["moves"]]
        if replay(native_start, search_moves)[-1] != ((1,), (2,)):
            raise AssertionError(
                f"closure search returned invalid native path for {challenge['challenge_id']}"
            )
        full_moves = list(bridge) + search_moves
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
                    "official verifier rejected consequence-closure path for "
                    f"{challenge['challenge_id']}: {receipt}"
                )

        if result["join_training_id"] is not None:
            closure_join_solved += 1
        solved.append(
            {
                "challenge_id": challenge["challenge_id"],
                "seq": int(row["seq"]),
                "n": int(row["n"]),
                "w_vector": [int(x) for x in row["w_vector"]],
                "bridge_moves": list(bridge),
                "search_moves": search_moves,
                "moves": full_moves,
                "length": len(full_moves),
                "search_expansions": int(result["expansions"]),
                "join_training_id": result["join_training_id"],
                "join_index": result["join_index"],
                "join_depth": result["join_depth"],
                "retained_suffix_length": result["retained_suffix_length"],
                "official_receipt": receipt,
            }
        )

    summary = {
        "open_rows": len(open_rows),
        "closure_states": len(closure),
        "frozen_capabilities": len(bank),
        "frozen_start_macros": len(start_macros),
        "search_budget": budget,
        "exact_manifest_matches": exact_matches,
        "orbit_manifest_matches": orbit_matches,
        "bridged_manifest_matches": bridged,
        "unmatched_open_rows": len(unmatched),
        "open_solved": len(solved),
        "closure_join_solved": closure_join_solved,
        "officially_verified_open_solved": sum(
            1
            for item in solved
            if item["official_receipt"] is not None
            and item["official_receipt"]["ok"]
        ),
    }
    return summary, solved, unmatched


def _load_trajectories(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trajectories", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--official-tools", type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--closure", required=True, type=Path)
    parser.add_argument("--submission", required=True, type=Path)
    parser.add_argument("--budget", type=int, default=3000)
    args = parser.parse_args()

    trajectories = _load_trajectories(args.trajectories)
    open_rows = _load_open_ms(args.metadata)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    summary, solved, unmatched = attack_open_rows(
        trajectories,
        open_rows,
        manifest,
        official_tools=args.official_tools,
        budget=args.budget,
    )

    closure = restart_closure(canonical_closure(build_suffix_closure(trajectories)))
    args.closure.write_text(canonical_closure(closure), encoding="utf-8")
    args.summary.write_text(
        json.dumps(summary, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    args.submission.write_text(
        "\n".join(
            f"{item['challenge_id']}: [{','.join(str(m) for m in item['moves'])}]"
            for item in solved
        )
        + ("\n" if solved else ""),
        encoding="utf-8",
    )
    print(json.dumps(summary, sort_keys=True, indent=2))

    if unmatched:
        raise SystemExit(f"unmatched open MS rows: {len(unmatched)}")
    if args.official_tools is not None and summary["officially_verified_open_solved"] != summary["open_solved"]:
        raise SystemExit("one or more generated open-MS paths failed official verification")


if __name__ == "__main__":
    main()
