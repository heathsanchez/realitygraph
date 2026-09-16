from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path
from typing import Any

from acc_capability_miner import canonical_bank, mine_capabilities, restart_bank
from acc_open_ms_transfer import (
    _load_open_ms,
    _manifest_orbit_map,
    _manifest_state_map,
    find_orbit_bridge,
    presentation_orbit_key,
)
from acc_prospective_transfer import (
    _load_trajectories,
    _state,
    best_first_search,
    mine_start_macros,
    reconstruct_ms_state,
)
from acc_source_entry import source_entry_macros, source_family_split
from realitygraph.acc import replay


def _dedupe_macros(macros: list[tuple[int, ...]]) -> list[tuple[int, ...]]:
    result: list[tuple[int, ...]] = []
    seen: set[tuple[int, ...]] = set()
    for macro in macros:
        if macro in seen:
            continue
        seen.add(macro)
        result.append(macro)
    return result


def audit_source_conditioning(
    trajectories: list[dict[str, Any]], *, budget: int = 50
) -> dict[str, Any]:
    acquisition, heldout = source_family_split(trajectories)
    bank = restart_bank(
        canonical_bank(
            mine_capabilities(
                acquisition, min_support=3, min_macro_len=2, max_macro_len=8
            )
        )
    )
    generic_start = mine_start_macros(acquisition, min_support=10)

    cold_solved = 0
    generic_solved = 0
    source_solved = 0
    source_only_vs_generic = 0
    generic_only_vs_source = 0
    both_generic_source = 0
    generic_expansions_on_both = 0
    source_expansions_on_both = 0
    source_macro_presentations = 0
    source_macro_count = 0
    ablation_mismatches = 0

    for row in heldout:
        start = _state(row["states"][0]["state"])
        source_macros = source_entry_macros(
            acquisition,
            target_n=int(row["n"]),
            target_w=row["w_vector"],
            min_len=2,
            max_len=8,
            include_full=True,
        )
        source_macro_presentations += int(bool(source_macros))
        source_macro_count += len(source_macros)

        cold = best_first_search(start, bank=[], start_macros=[], budget=budget)
        generic = best_first_search(
            start, bank=bank, start_macros=generic_start, budget=budget
        )
        source = best_first_search(
            start,
            bank=bank,
            start_macros=_dedupe_macros(source_macros + generic_start),
            budget=budget,
        )
        ablated = best_first_search(
            start, bank=bank, start_macros=generic_start, budget=budget
        )
        if ablated != generic:
            ablation_mismatches += 1

        cold_solved += int(cold["solved"])
        generic_solved += int(generic["solved"])
        source_solved += int(source["solved"])
        if generic["solved"] and source["solved"]:
            both_generic_source += 1
            generic_expansions_on_both += int(generic["expansions"])
            source_expansions_on_both += int(source["expansions"])
        elif source["solved"]:
            source_only_vs_generic += 1
        elif generic["solved"]:
            generic_only_vs_source += 1

    return {
        "acquisition_presentations": len(acquisition),
        "heldout_presentations": len(heldout),
        "budget": budget,
        "frozen_capabilities": len(bank),
        "generic_start_macros": len(generic_start),
        "source_macro_presentations": source_macro_presentations,
        "source_macro_count": source_macro_count,
        "cold_solved": cold_solved,
        "generic_solved": generic_solved,
        "source_solved": source_solved,
        "source_only_vs_generic": source_only_vs_generic,
        "generic_only_vs_source": generic_only_vs_source,
        "both_generic_source": both_generic_source,
        "generic_expansions_on_both": generic_expansions_on_both,
        "source_expansions_on_both": source_expansions_on_both,
        "ablation_mismatches": ablation_mismatches,
    }


def attack_open_source_conditioned(
    trajectories: list[dict[str, Any]],
    metadata_path: Path,
    manifest: dict[str, Any],
    *,
    official_tools: Path | None,
    budget: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    bank = restart_bank(
        canonical_bank(
            mine_capabilities(
                trajectories, min_support=3, min_macro_len=2, max_macro_len=8
            )
        )
    )
    generic_start = mine_start_macros(trajectories, min_support=10)
    exact_map = _manifest_state_map(manifest)
    orbit_map = _manifest_orbit_map(manifest)
    open_rows = _load_open_ms(metadata_path)

    verify = None
    if official_tools is not None:
        sys.path.insert(0, str(official_tools.resolve()))
        verify = importlib.import_module("verifier.core").verify

    eligible = 0
    attempted = 0
    solved: list[dict[str, Any]] = []

    for row in open_rows:
        source_macros = source_entry_macros(
            trajectories,
            target_n=int(row["n"]),
            target_w=row["w_vector"],
            min_len=2,
            max_len=8,
            include_full=True,
        )
        if not source_macros:
            continue
        eligible += 1

        native_start = reconstruct_ms_state(row["n"], row["w_vector"])
        challenge = exact_map.get(native_start)
        bridge: tuple[int, ...] = ()
        if challenge is None:
            challenge = orbit_map.get(presentation_orbit_key(native_start))
            if challenge is None:
                raise AssertionError(f"missing official representative for MS seq {row['seq']}")
            challenge_start = _state(challenge["initial_relators"])
            bridge = find_orbit_bridge(challenge_start, native_start)
            if replay(challenge_start, bridge)[-1] != native_start:
                raise AssertionError(f"bridge replay mismatch for {challenge['challenge_id']}")

        attempted += 1
        start_macros = _dedupe_macros(source_macros + generic_start)
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
                    f"official verifier rejected {challenge['challenge_id']}: {receipt}"
                )
        solved.append(
            {
                "challenge_id": challenge["challenge_id"],
                "seq": row["seq"],
                "n": row["n"],
                "w_vector": list(row["w_vector"]),
                "source_macros_available": len(source_macros),
                "bridge_moves": list(bridge),
                "search_moves": result["moves"],
                "moves": full_moves,
                "length": len(full_moves),
                "search_expansions": result["expansions"],
                "official_receipt": receipt,
            }
        )

    return {
        "open_rows": len(open_rows),
        "source_eligible_open_rows": eligible,
        "attempted_open_rows": attempted,
        "budget": budget,
        "frozen_capabilities": len(bank),
        "generic_start_macros": len(generic_start),
        "open_solved": len(solved),
        "officially_verified_open_solved": sum(
            1
            for item in solved
            if item["official_receipt"] and item["official_receipt"]["ok"]
        ),
    }, solved


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trajectories", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--official-tools", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--submission", required=True, type=Path)
    parser.add_argument("--audit-budget", type=int, default=50)
    parser.add_argument("--open-budget", type=int, default=3000)
    args = parser.parse_args()

    trajectories = _load_trajectories(args.trajectories)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    audit = audit_source_conditioning(trajectories, budget=args.audit_budget)
    if audit["ablation_mismatches"]:
        raise SystemExit("source-entry ablation did not restore generic baseline")

    open_summary, solved = attack_open_source_conditioned(
        trajectories,
        args.metadata,
        manifest,
        official_tools=args.official_tools,
        budget=args.open_budget,
    )
    summary = {"source_audit": audit, "open_transfer": open_summary}
    args.summary.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    args.submission.write_text(
        "".join(
            f"{item['challenge_id']}: [{','.join(str(m) for m in item['moves'])}]\n"
            for item in solved
        ),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
