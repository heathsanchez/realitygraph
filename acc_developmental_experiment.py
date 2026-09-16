from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import sys
from dataclasses import dataclass
from itertools import product
from pathlib import Path
from typing import Any, Callable

from acc_capability_miner import canonical_bank, mine_capabilities, restart_bank
from acc_consequence_closure import build_suffix_closure
from acc_developmental_core import ACCResidual, residual_from_search
from acc_developmental_search import developmental_search
from acc_generator_controller import (
    GeneratorObservation,
    GeneratorPolicy,
    apply_policy,
    learn_generator_policy,
)
from acc_ms_recurrence import commutes_with_y, ms_state
from acc_open_ms_transfer import (
    _load_open_ms,
    _manifest_orbit_map,
    _manifest_state_map,
    find_orbit_bridge,
    presentation_orbit_key,
)
from acc_orbit_closure import build_orbit_closure
from acc_prospective_transfer import (
    _load_trajectories,
    _state,
    mine_start_macros,
    reconstruct_ms_state,
)
from acc_scientific_split import ScientificSplit, freeze_split, select_rows
from acc_structural_generator import StructuralMacroGenerator, mine_structural_macros
from acc_substitution_generator import SubstitutionCandidate, SubstitutionGenerator
from acc_generator_portfolio import ACCGeneratorContext, RecurrenceGenerator
from realitygraph.acc import State, replay


FREEZE_VERSION = "acc-developmental-freeze-v1"
SCIENTIFIC_VERSION = "acc-developmental-scientific-v1"
GENERATOR_IDS = ("structural_macro", "substitution")


def policy_sha256(policy_text: str) -> str:
    return hashlib.sha256(policy_text.encode("utf-8")).hexdigest()


def write_freeze_marker(
    path: Path,
    policy_text: str,
    *,
    split_digest: str,
) -> dict[str, Any]:
    payload = {
        "version": FREEZE_VERSION,
        "policy_sha256": policy_sha256(policy_text),
        "split_digest": str(split_digest),
        "open_rows_loaded": False,
    }
    path.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def _validated_freeze_marker(
    marker_path: Path,
    *,
    expected_policy_sha256: str,
) -> dict[str, Any]:
    if not marker_path.exists():
        raise RuntimeError("open ACC rows require a frozen policy marker")
    try:
        payload = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("open ACC rows require a valid frozen policy marker") from exc
    if payload.get("version") != FREEZE_VERSION:
        raise RuntimeError("open ACC rows require a frozen policy marker")
    actual = str(payload.get("policy_sha256", ""))
    if actual != str(expected_policy_sha256):
        raise RuntimeError("frozen policy hash mismatch before open ACC row access")
    if payload.get("open_rows_loaded") is not False:
        raise RuntimeError("freeze marker was already mutated before open-row access")
    if not payload.get("split_digest"):
        raise RuntimeError("frozen policy marker is missing the sealed split digest")
    return payload


def load_open_rows(
    metadata_path: Path,
    freeze_marker_path: Path,
    *,
    expected_policy_sha256: str,
) -> list[dict[str, Any]]:
    _validated_freeze_marker(
        freeze_marker_path,
        expected_policy_sha256=expected_policy_sha256,
    )
    return _load_open_ms(metadata_path)


@dataclass(frozen=True)
class AcquisitionComponents:
    orbit_closure: dict[str, dict[str, Any]]
    bank: list[dict[str, Any]]
    start_macros: list[tuple[int, ...]]
    structural_bank: list[dict[str, Any]]
    digest: str

    @property
    def structural_generator(self) -> StructuralMacroGenerator:
        return StructuralMacroGenerator(self.structural_bank)


_ALPHABET = (1, -1, 2, -2)
_SUBSTITUTION_WORDS = tuple((x,) for x in _ALPHABET) + tuple(
    tuple(word) for word in product(_ALPHABET, repeat=2)
)
_SUBSTITUTION_CANDIDATES = tuple(
    SubstitutionCandidate(target, word, inverse_other)
    for word in _SUBSTITUTION_WORDS
    for target in (0, 1)
    for inverse_other in (False, True)
)


def _substitution_generator() -> SubstitutionGenerator:
    return SubstitutionGenerator(
        _SUBSTITUTION_CANDIDATES,
        max_total=120,
        max_path_length=400,
    )


def _build_components(acquisition: list[dict[str, Any]]) -> AcquisitionComponents:
    exact = build_suffix_closure(acquisition)
    orbit = build_orbit_closure(exact)
    bank = restart_bank(
        canonical_bank(
            mine_capabilities(
                acquisition,
                min_support=3,
                min_macro_len=2,
                max_macro_len=8,
            )
        )
    )
    start_macros = mine_start_macros(acquisition, min_support=5)
    structural = mine_structural_macros(
        acquisition,
        min_support=3,
        min_macro_len=2,
        max_macro_len=8,
    )
    digest_payload = json.dumps(
        {
            "orbit_classes": len(orbit),
            "bank_ids": [str(cap.get("id", "")) for cap in bank],
            "start_macros": [list(macro) for macro in start_macros],
            "structural_ids": [str(cap.get("id", "")) for cap in structural],
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(digest_payload.encode()).hexdigest()
    return AcquisitionComponents(orbit, bank, start_macros, structural, digest)


def _row_source(row: dict[str, Any]) -> tuple[str, int | None, tuple[int, ...]]:
    family = str(row.get("family") or "ms")
    n = row.get("n")
    word = tuple(int(x) for x in row.get("w_vector", ()))
    return family, None if n is None else int(n), word


def _recurrence_callback(row: dict[str, Any]) -> Callable[[State], tuple[Any, ...]]:
    family, n, word = _row_source(row)
    if family != "ms" or n is None or n < 2 or not commutes_with_y(word):
        return lambda _state: ()
    generator = RecurrenceGenerator()
    actions_by_state: dict[State, tuple[Any, ...]] = {}
    for current_n in range(2, n + 1):
        state = ms_state(current_n, word)
        actions = generator.generate(
            state,
            ACCGeneratorContext(
                source_family="ms",
                n=current_n,
                w_vector=word,
            ),
        )
        if actions:
            actions_by_state[state] = actions
    return lambda state: actions_by_state.get(state, ())


def _extra_callback(
    generator_id: str | None,
    row: dict[str, Any],
    components: AcquisitionComponents,
) -> Callable[[State], tuple[Any, ...]]:
    recurrence = _recurrence_callback(row)
    structural = components.structural_generator
    substitution = _substitution_generator()

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


def _search_state(
    start: State,
    row: dict[str, Any],
    components: AcquisitionComponents,
    *,
    generator_id: str | None,
    budget: int,
) -> dict[str, Any]:
    return developmental_search(
        start,
        orbit_closure=components.orbit_closure,
        bank=components.bank,
        start_macros=components.start_macros,
        budget=budget,
        extra_actions=_extra_callback(generator_id, row, components),
        max_total=120,
        max_path_length=400,
    )


def _residual_for(
    start: State,
    row: dict[str, Any],
    baseline: dict[str, Any],
) -> ACCResidual:
    family, n, word = _row_source(row)
    return residual_from_search(
        start,
        source_family=family,
        n=n,
        w_vector=word,
        diagnostics=baseline["diagnostics"],
    )


def _training_verifier(
    training_manifest_path: Path,
    official_tools: Path,
):
    if str(official_tools.resolve()) not in sys.path:
        sys.path.insert(0, str(official_tools.resolve()))
    verify = importlib.import_module("verifier.core").verify
    manifest = json.loads(training_manifest_path.read_text(encoding="utf-8"))
    challenges = {
        challenge["challenge_id"]: challenge
        for challenge in manifest["challenges"]
        if challenge["move_spec_version"] == "ac-r2-v1"
    }
    return verify, challenges, manifest["limits"]


def _verified_training_solve(
    row: dict[str, Any],
    result: dict[str, Any],
    verify,
    challenges: dict[str, dict[str, Any]],
    limits: dict[str, Any],
) -> tuple[bool, dict[str, Any] | None]:
    if not result["solved"]:
        return False, None
    training_id = str(row["training_id"])
    challenge = challenges.get(training_id)
    if challenge is None:
        raise ValueError(f"missing official training challenge: {training_id}")
    receipt = verify(challenge, result["moves"], "ac-r2-v1", limits)
    return bool(receipt["ok"]), receipt


def _calibration_observations(
    rows: list[dict[str, Any]],
    components: AcquisitionComponents,
    *,
    budget: int,
    verify,
    challenges: dict[str, dict[str, Any]],
    limits: dict[str, Any],
) -> tuple[list[GeneratorObservation], list[dict[str, Any]]]:
    observations: list[GeneratorObservation] = []
    events: list[dict[str, Any]] = []
    for row in rows:
        start = _state(row["states"][0]["state"])
        baseline = _search_state(
            start, row, components, generator_id=None, budget=budget
        )
        baseline_ok, baseline_receipt = _verified_training_solve(
            row, baseline, verify, challenges, limits
        )
        residual = _residual_for(start, row, baseline)
        generated_rows: dict[str, Any] = {}
        for generator_id in GENERATOR_IDS:
            generated = _search_state(
                start,
                row,
                components,
                generator_id=generator_id,
                budget=budget,
            )
            generated_ok, receipt = _verified_training_solve(
                row, generated, verify, challenges, limits
            )
            observations.append(
                GeneratorObservation(
                    residual=residual,
                    generator_id=generator_id,
                    baseline_solved=baseline_ok,
                    generated_solved=bool(generated["solved"]),
                    official_verified=generated_ok,
                    baseline_expansions=int(baseline["expansions"]),
                    generated_expansions=int(generated["expansions"]),
                    generator_cost=int(
                        generated["generator_uses"].get(generator_id, 0)
                    ),
                )
            )
            generated_rows[generator_id] = {
                "local_solved": bool(generated["solved"]),
                "official_verified": generated_ok,
                "expansions": int(generated["expansions"]),
                "generator_uses": int(
                    generated["generator_uses"].get(generator_id, 0)
                ),
                "receipt": receipt,
            }
        events.append(
            {
                "training_id": row["training_id"],
                "baseline_local_solved": bool(baseline["solved"]),
                "baseline_official_verified": baseline_ok,
                "baseline_expansions": int(baseline["expansions"]),
                "baseline_receipt": baseline_receipt,
                "residual": json.loads(residual.canonical_json()),
                "generators": generated_rows,
            }
        )
    return observations, events


def _future_evaluation(
    rows: list[dict[str, Any]],
    components: AcquisitionComponents,
    policy: GeneratorPolicy,
    *,
    budget: int,
    verify,
    challenges: dict[str, dict[str, Any]],
    limits: dict[str, Any],
) -> dict[str, Any]:
    baseline_solved = 0
    warm_solved = 0
    rescues = 0
    harms = 0
    invoked = 0
    ablation_mismatches = 0
    events: list[dict[str, Any]] = []
    ablated = policy.ablate()

    for row in rows:
        start = _state(row["states"][0]["state"])
        baseline = _search_state(
            start, row, components, generator_id=None, budget=budget
        )
        baseline_ok, baseline_receipt = _verified_training_solve(
            row, baseline, verify, challenges, limits
        )
        baseline_solved += int(baseline_ok)
        residual = _residual_for(start, row, baseline)
        selected = () if baseline_ok else apply_policy(policy, residual)
        if apply_policy(ablated, residual):
            ablation_mismatches += 1

        generated = None
        generated_ok = False
        generated_receipt = None
        if selected:
            invoked += 1
            generator_id = selected[0]
            generated = _search_state(
                start,
                row,
                components,
                generator_id=generator_id,
                budget=budget,
            )
            generated_ok, generated_receipt = _verified_training_solve(
                row, generated, verify, challenges, limits
            )

        warm_ok = baseline_ok or generated_ok
        warm_solved += int(warm_ok)
        rescue = (not baseline_ok) and generated_ok
        rescues += int(rescue)
        if baseline_ok and not warm_ok:
            harms += 1

        events.append(
            {
                "training_id": row["training_id"],
                "baseline_verified": baseline_ok,
                "baseline_expansions": int(baseline["expansions"]),
                "selected_generators": list(selected),
                "generated_verified": generated_ok,
                "generated_expansions": (
                    None if generated is None else int(generated["expansions"])
                ),
                "rescue": rescue,
                "baseline_receipt": baseline_receipt,
                "generated_receipt": generated_receipt,
                "residual": json.loads(residual.canonical_json()),
            }
        )

    return {
        "presentations": len(rows),
        "budget": budget,
        "baseline_solved": baseline_solved,
        "warm_solved": warm_solved,
        "rescues": rescues,
        "harms": harms,
        "controller_invocations": invoked,
        "ablation_mismatches": ablation_mismatches,
        "events": events,
    }


def run_scientific(
    trajectories_path: Path,
    training_manifest_path: Path,
    official_tools: Path,
    *,
    split_path: Path,
    policy_path: Path,
    summary_path: Path,
    freeze_marker_path: Path,
    seed: str,
    budget: int,
) -> dict[str, Any]:
    trajectories = _load_trajectories(trajectories_path)
    split = freeze_split(trajectories, seed)
    acquisition = select_rows(trajectories, split.acquisition_ids)
    calibration = select_rows(trajectories, split.calibration_ids)
    future = select_rows(trajectories, split.future_ids)
    if not acquisition or not calibration or not future:
        raise RuntimeError("sealed ACC split must contain acquisition, calibration, and future rows")

    components = _build_components(acquisition)
    verify, challenges, limits = _training_verifier(
        training_manifest_path, official_tools
    )
    observations, calibration_events = _calibration_observations(
        calibration,
        components,
        budget=budget,
        verify=verify,
        challenges=challenges,
        limits=limits,
    )
    policy = learn_generator_policy(observations)
    policy_text = policy.canonical_json()
    restarted = GeneratorPolicy.from_json(policy_text)
    restart_exact = restarted.canonical_json() == policy_text

    future_summary = _future_evaluation(
        future,
        components,
        restarted,
        budget=budget,
        verify=verify,
        challenges=challenges,
        limits=limits,
    )

    calibration_rescues = {
        generator_id: sum(
            1
            for obs in observations
            if obs.generator_id == generator_id
            and (not obs.baseline_solved)
            and obs.generated_solved
            and obs.official_verified
        )
        for generator_id in GENERATOR_IDS
    }
    calibration_harms = {
        generator_id: sum(
            1
            for obs in observations
            if obs.generator_id == generator_id
            and obs.baseline_solved
            and not obs.generated_solved
        )
        for generator_id in GENERATOR_IDS
    }

    gates = {
        "split_frozen_and_disjoint": (
            len(split.acquisition_ids)
            + len(split.calibration_ids)
            + len(split.future_ids)
            == len(trajectories)
        ),
        "policy_restart_exact": restart_exact,
        "policy_promoted": restarted.promoted,
        "calibration_has_verified_rescue": restarted.rescues > 0,
        "calibration_zero_harms_for_promoted_rule": restarted.harms == 0,
        "future_zero_harms": future_summary["harms"] == 0,
        "future_ablation_exact": future_summary["ablation_mismatches"] == 0,
        "future_verified_rescue": future_summary["rescues"] > 0,
    }
    passed = all(gates.values())

    split_path.write_text(split.canonical_json() + "\n", encoding="utf-8")
    policy_path.write_text(policy_text + "\n", encoding="utf-8")
    result = {
        "version": SCIENTIFIC_VERSION,
        "split_digest": split.manifest_digest,
        "split": {
            "acquisition": len(acquisition),
            "calibration": len(calibration),
            "future": len(future),
        },
        "components": {
            "digest": components.digest,
            "orbit_classes": len(components.orbit_closure),
            "guarded_capabilities": len(components.bank),
            "start_macros": len(components.start_macros),
            "structural_capabilities": len(components.structural_bank),
            "substitution_candidates": len(_SUBSTITUTION_CANDIDATES),
        },
        "calibration": {
            "observations": len(observations),
            "verified_rescues_by_generator": calibration_rescues,
            "harms_by_generator": calibration_harms,
            "events": calibration_events,
        },
        "policy": json.loads(policy_text),
        "policy_sha256": policy_sha256(policy_text),
        "policy_restart_exact": restart_exact,
        "future": future_summary,
        "gates": gates,
        "passed": passed,
    }
    summary_path.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    if passed:
        write_freeze_marker(
            freeze_marker_path,
            policy_text,
            split_digest=split.manifest_digest,
        )
    elif freeze_marker_path.exists():
        freeze_marker_path.unlink()
    return result


def _scientific_split_from_file(path: Path) -> ScientificSplit:
    payload = json.loads(path.read_text(encoding="utf-8"))
    split = ScientificSplit(
        seed=str(payload["seed"]),
        acquisition_ids=tuple(str(x) for x in payload["acquisition_ids"]),
        calibration_ids=tuple(str(x) for x in payload["calibration_ids"]),
        future_ids=tuple(str(x) for x in payload["future_ids"]),
        manifest_digest=str(payload["manifest_digest"]),
    )
    if split.canonical_json() != path.read_text(encoding="utf-8").strip():
        raise RuntimeError("sealed ACC split did not restart byte-exactly")
    return split


def _official_open_verifier(official_tools: Path):
    if str(official_tools.resolve()) not in sys.path:
        sys.path.insert(0, str(official_tools.resolve()))
    return importlib.import_module("verifier.core").verify


def run_open(
    trajectories_path: Path,
    split_path: Path,
    policy_path: Path,
    freeze_marker_path: Path,
    metadata_path: Path,
    manifest_path: Path,
    official_tools: Path,
    *,
    summary_path: Path,
    submission_path: Path,
    probe_budget: int,
    open_budget: int,
) -> dict[str, Any]:
    policy_text = policy_path.read_text(encoding="utf-8").strip()
    policy = GeneratorPolicy.from_json(policy_text)
    digest = policy_sha256(policy_text)
    split = _scientific_split_from_file(split_path)
    marker = _validated_freeze_marker(
        freeze_marker_path,
        expected_policy_sha256=digest,
    )
    if marker["split_digest"] != split.manifest_digest:
        raise RuntimeError("frozen split digest mismatch before open ACC row access")

    # This is the first call that is permitted to open the 550 metadata file.
    open_rows = load_open_rows(
        metadata_path,
        freeze_marker_path,
        expected_policy_sha256=digest,
    )
    trajectories = _load_trajectories(trajectories_path)
    acquisition = select_rows(trajectories, split.acquisition_ids)
    components = _build_components(acquisition)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    exact_map = _manifest_state_map(manifest)
    orbit_map = _manifest_orbit_map(manifest)
    verify = _official_open_verifier(official_tools)

    solved: list[dict[str, Any]] = []
    invoked = 0
    unmatched = 0
    for row in open_rows:
        native_start = reconstruct_ms_state(row["n"], row["w_vector"])
        challenge = exact_map.get(native_start)
        bridge: tuple[int, ...] = ()
        if challenge is None:
            challenge = orbit_map.get(presentation_orbit_key(native_start))
            if challenge is None:
                unmatched += 1
                continue
            challenge_start = _state(challenge["initial_relators"])
            bridge = find_orbit_bridge(challenge_start, native_start)
            if replay(challenge_start, bridge)[-1] != native_start:
                raise AssertionError("official/native open bridge replay mismatch")

        context = {
            "family": "ms",
            "n": int(row["n"]),
            "w_vector": tuple(int(x) for x in row["w_vector"]),
        }
        baseline = _search_state(
            native_start,
            context,
            components,
            generator_id=None,
            budget=probe_budget,
        )
        candidate = baseline if baseline["solved"] else None
        selected: tuple[str, ...] = ()
        if candidate is None:
            residual = _residual_for(native_start, context, baseline)
            selected = apply_policy(policy, residual)
            if selected:
                invoked += 1
                generated = _search_state(
                    native_start,
                    context,
                    components,
                    generator_id=selected[0],
                    budget=open_budget,
                )
                if generated["solved"]:
                    candidate = generated

        if candidate is None:
            continue
        full_moves = list(bridge) + list(candidate["moves"])
        receipt = verify(
            challenge,
            full_moves,
            "ac-r2-v1",
            manifest["limits"],
        )
        if not receipt["ok"]:
            continue
        solved.append(
            {
                "challenge_id": challenge["challenge_id"],
                "seq": int(row["seq"]),
                "n": int(row["n"]),
                "w_vector": list(row["w_vector"]),
                "selected_generators": list(selected),
                "bridge_moves": list(bridge),
                "native_moves": list(candidate["moves"]),
                "moves": full_moves,
                "length": len(full_moves),
                "receipt": receipt,
            }
        )

    result = {
        "version": SCIENTIFIC_VERSION,
        "policy_sha256": digest,
        "split_digest": split.manifest_digest,
        "open_rows": len(open_rows),
        "unmatched_rows": unmatched,
        "controller_invocations": invoked,
        "officially_verified_open_solved": len(solved),
        "solutions": solved,
    }
    summary_path.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    submission_path.write_text(
        "".join(
            f"{item['challenge_id']}: [{','.join(str(move) for move in item['moves'])}]\n"
            for item in solved
        ),
        encoding="utf-8",
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    scientific = sub.add_parser("scientific")
    scientific.add_argument("--trajectories", required=True, type=Path)
    scientific.add_argument("--training-manifest", required=True, type=Path)
    scientific.add_argument("--official-tools", required=True, type=Path)
    scientific.add_argument("--split", required=True, type=Path)
    scientific.add_argument("--policy", required=True, type=Path)
    scientific.add_argument("--summary", required=True, type=Path)
    scientific.add_argument("--freeze-marker", required=True, type=Path)
    scientific.add_argument("--seed", default="acc-developmental-system-v1")
    scientific.add_argument("--budget", type=int, default=100)

    open_cmd = sub.add_parser("open")
    open_cmd.add_argument("--trajectories", required=True, type=Path)
    open_cmd.add_argument("--split", required=True, type=Path)
    open_cmd.add_argument("--policy", required=True, type=Path)
    open_cmd.add_argument("--freeze-marker", required=True, type=Path)
    open_cmd.add_argument("--metadata", required=True, type=Path)
    open_cmd.add_argument("--manifest", required=True, type=Path)
    open_cmd.add_argument("--official-tools", required=True, type=Path)
    open_cmd.add_argument("--summary", required=True, type=Path)
    open_cmd.add_argument("--submission", required=True, type=Path)
    open_cmd.add_argument("--probe-budget", type=int, default=100)
    open_cmd.add_argument("--open-budget", type=int, default=3000)

    args = parser.parse_args()
    if args.command == "scientific":
        result = run_scientific(
            args.trajectories,
            args.training_manifest,
            args.official_tools,
            split_path=args.split,
            policy_path=args.policy,
            summary_path=args.summary,
            freeze_marker_path=args.freeze_marker,
            seed=args.seed,
            budget=args.budget,
        )
        print(json.dumps(result, sort_keys=True, indent=2))
        if not result["passed"]:
            raise SystemExit(2)
        return

    result = run_open(
        args.trajectories,
        args.split,
        args.policy,
        args.freeze_marker,
        args.metadata,
        args.manifest,
        args.official_tools,
        summary_path=args.summary,
        submission_path=args.submission,
        probe_budget=args.probe_budget,
        open_budget=args.open_budget,
    )
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
