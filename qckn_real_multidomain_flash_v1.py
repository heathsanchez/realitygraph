from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import urllib.request
from pathlib import Path
from typing import Any

from realitygraph.real_flash import (
    AuthorityEvidence,
    ProtocolResidual,
    RealFlashGraph,
)


USER_AGENT = "RealityGraph-QCKN-Real-Multidomain-Flash-V1"

SAIR_REPO = "metalogiclabs/mathgraph"
SAIR_COMMIT = "4c1152987c99bbe221ac418644488802417a6c81"
SAIR_V6_PATH = "docs/evidence/openrouter_sair_sealed_reserve_confirmation_v6.md"
SAIR_BANK_PATH = "experiments/openrouter_sair_v5/frozen_model_acquired_verified_bank.json"
SAIR_MANIFEST_PATH = "experiments/openrouter_sair_v5/frozen_bank_manifest.json"
SAIR_V6_RUN = 35402936630

ARC_REPO = "heathsanchez/Minimal-Sufficient-Interface"
ARC_COMMIT = "8fc6faba693c2b730d621ce14fcb2710a69b7c61"
ARC_WORKFLOW_PATH = ".github/workflows/arc3-qckn-flash-multigame-v3.yml"
ARC_RUN = 35405566334
ARC_ARTIFACT = 10571953522
ARC_ARTIFACT_DIGEST = "sha256:9a67b25659386f969bfae546038b958e4edd1cf0e2b85519d1e612d09d8f210b"

LEAN_REPO = "heathsanchez/lean-kernel-arena"
LEAN_COMMIT = "d965b8b790f69ae388b41feb08df59e3c7ce8648"
LEAN_MEMORY_PATH = "genesis/evidence/kernel-realitygraph-memory-v1.json"
LEAN_PERF_COMMIT = "919937fb4a58becfb31ad7cbcce9351b601d8e11"
LEAN_QUAL_PATH = "genesis/evidence/qualification-flat-9b39e94.json"

GPU_REPO = "heathsanchez/test"
GPU_COMMIT = "c5402d50000b5e20f64318edcb113479e313db19"
GPU_EVIDENCE_PATH = "experiments/gpu_developmental_optimization_v1/evidence-summary.json"
GPU_RUN = 35405925307


def _request(url: str) -> bytes:
    headers = {"User-Agent": USER_AGENT}
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token and url.startswith("https://api.github.com/"):
        headers["Authorization"] = f"Bearer {token}"
        headers["X-GitHub-Api-Version"] = "2022-11-28"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read()


def _raw(repo: str, commit: str, path: str) -> tuple[bytes, str]:
    url = f"https://raw.githubusercontent.com/{repo}/{commit}/{path}"
    data = _request(url)
    return data, url


def _api(path: str) -> dict[str, Any]:
    data = _request("https://api.github.com/" + path.lstrip("/"))
    value = json.loads(data)
    if not isinstance(value, dict):
        raise ValueError(f"expected API object for {path}")
    return value


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _scope(**kwargs: str) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((str(k), str(v)) for k, v in kwargs.items()))


def _metrics(**kwargs: Any) -> tuple[tuple[str, Any], ...]:
    return tuple(sorted(kwargs.items()))


def load_sair() -> tuple[list[AuthorityEvidence], dict[str, Any]]:
    v6_bytes, v6_url = _raw(SAIR_REPO, SAIR_COMMIT, SAIR_V6_PATH)
    bank_bytes, bank_url = _raw(SAIR_REPO, SAIR_COMMIT, SAIR_BANK_PATH)
    manifest_bytes, manifest_url = _raw(SAIR_REPO, SAIR_COMMIT, SAIR_MANIFEST_PATH)
    v6 = v6_bytes.decode("utf-8")
    bank = json.loads(bank_bytes)
    manifest = json.loads(manifest_bytes)
    run = _api(f"repos/{SAIR_REPO}/actions/runs/{SAIR_V6_RUN}")

    if run.get("conclusion") != "success":
        raise AssertionError("pinned SAIR V6 run is not successful")
    if len(bank) != 3 or not all(
        row.get("verifier_evidence", {}).get("terminal_candidate_ok") is True
        for row in bank
    ):
        raise AssertionError("frozen SAIR bank failed source integrity")
    if manifest.get("untouched_reserve_false_count") != 250:
        raise AssertionError("SAIR reserve boundary changed")

    expected = {
        "cold_model_calls": 531,
        "warm_model_calls": 300,
        "cold_tokens": 77514,
        "warm_tokens": 44028,
        "cold_verified_post_acquisition": 148,
        "warm_verified_post_acquisition": 231,
    }
    required_phrases = (
        "| model calls | 531 | 300 |",
        "| tokens | 77,514 | 44,028 |",
        "cold produced 148 verified",
        "verified reuse produced 231",
    )
    if not all(phrase in v6 for phrase in required_phrases):
        raise AssertionError("SAIR V6 published evidence changed")

    bundle = AuthorityEvidence(
        evidence_id="sair:v6:compiled-verified-state",
        domain="sair",
        kind="verified_capability_bundle",
        contract="developmental:verified-state-compilation:v1",
        scope=_scope(
            task_family="equational-theory-false",
            artifact="finite-magma-countermodel",
            model="google/gemma-4-31b-it",
        ),
        consequence_signature=(
            "model_generated",
            "independently_verified",
            "persisted",
            "restart_reused",
            "ablation_restores_cold",
        ),
        source_ref=v6_url,
        source_sha256=_sha256(v6_bytes),
        metrics=_metrics(**expected),
        pattern_ids=("verified_state_compilation", "restartable_capability_reuse"),
    )
    content = AuthorityEvidence(
        evidence_id="sair:v5:three-countermodels",
        domain="sair",
        kind="mathematical_content",
        contract="math:magma-countermodel:v1",
        scope=_scope(
            carrier="Fin2",
            source="three_model_generated_tables",
        ),
        consequence_signature=tuple(row["capability_id"] for row in bank),
        source_ref=bank_url,
        source_sha256=_sha256(bank_bytes),
        metrics=_metrics(capability_count=3),
        pattern_ids=(),
    )
    return [bundle, content], {
        "run_id": SAIR_V6_RUN,
        "run_head_sha": run.get("head_sha"),
        "v6_sha256": _sha256(v6_bytes),
        "bank_sha256": _sha256(bank_bytes),
        "manifest_sha256": _sha256(manifest_bytes),
        "bank_source_ref": bank_url,
        "manifest_source_ref": manifest_url,
    }


def load_arc() -> tuple[list[AuthorityEvidence], dict[str, Any]]:
    workflow_bytes, workflow_url = _raw(ARC_REPO, ARC_COMMIT, ARC_WORKFLOW_PATH)
    workflow = workflow_bytes.decode("utf-8")
    run = _api(f"repos/{ARC_REPO}/actions/runs/{ARC_RUN}")
    artifact = _api(f"repos/{ARC_REPO}/actions/artifacts/{ARC_ARTIFACT}")

    if run.get("conclusion") != "success":
        raise AssertionError("pinned ARC Flash V3 run is not successful")
    if artifact.get("digest") != ARC_ARTIFACT_DIGEST:
        raise AssertionError("ARC Flash V3 artifact digest changed")
    required = (
        "assert r['first_generation']['destination_verifier_calls']==1",
        "assert r['restart']['destination_verifier_calls_after_restart']==0",
        "assert r['restart']['blocked_after_restart']==8",
        "assert r['ablation']['destination_verifier_calls_restored']==1",
        "assert r['stale_control']['destination_evidence_rejected'] is True",
    )
    if not all(row in workflow for row in required):
        raise AssertionError("ARC V3 qualification gates changed")

    evidence = AuthorityEvidence(
        evidence_id="arc:v3:restarted-exact-refutation",
        domain="arc",
        kind="verified_obstruction_compilation",
        contract="developmental:verified-state-compilation:v1",
        scope=_scope(
            source_game="ft09",
            destination_game="vc33",
            exact_claim="generic-fatal-family-transfer",
        ),
        consequence_signature=(
            "destination_refutation",
            "compiled_obstruction",
            "restart_zero_verifier_calls",
            "changed_scope_not_blocked",
            "stale_authority_rejected",
        ),
        source_ref=workflow_url,
        source_sha256=_sha256(workflow_bytes),
        metrics=_metrics(
            first_generation_verifier_calls=1,
            restart_verifier_calls=0,
            blocked_after_restart=8,
            ablation_restored_calls=1,
        ),
        pattern_ids=(
            "verified_state_compilation",
            "restartable_capability_reuse",
            "exact_refutation_cache",
        ),
    )
    content = AuthorityEvidence(
        evidence_id="arc:v3:action6-fatal-transfer-refutation",
        domain="arc",
        kind="domain_content_obstruction",
        contract="arc3:complex-action6:v1",
        scope=_scope(source_game="ft09", destination_game="vc33"),
        consequence_signature=(
            "bounded-fatal-5454-family",
            "generic-transfer-refuted-at-vc33",
        ),
        source_ref=workflow_url,
        source_sha256=_sha256(workflow_bytes),
        metrics=_metrics(blocked_identical_future_proposals=8),
        pattern_ids=(),
    )
    return [evidence, content], {
        "run_id": ARC_RUN,
        "artifact_id": ARC_ARTIFACT,
        "artifact_digest": artifact.get("digest"),
        "workflow_sha256": _sha256(workflow_bytes),
        "run_head_sha": run.get("head_sha"),
    }


def load_lean_kernel() -> tuple[list[AuthorityEvidence], dict[str, Any]]:
    memory_bytes, memory_url = _raw(LEAN_REPO, LEAN_COMMIT, LEAN_MEMORY_PATH)
    qual_bytes, qual_url = _raw(LEAN_REPO, LEAN_PERF_COMMIT, LEAN_QUAL_PATH)
    memory = json.loads(memory_bytes)
    qual = json.loads(qual_bytes)

    retained = memory.get("retained_kernel", {})
    if retained != {"accept": 111, "reject": 71, "unknown": 6, "wrong": 0}:
        raise AssertionError("Lean retained-kernel memory changed")
    probes = memory.get("evidence", [])
    if len(probes) < 8 or not all("FALSIFIED" in row.get("status", "") for row in probes):
        raise AssertionError("Lean negative-evidence bank changed")
    totals = qual.get("totals", {})
    if totals.get("wrong") != 0 or totals.get("correct") != 183:
        raise AssertionError("Lean qualification evidence changed")

    diagnostic = AuthorityEvidence(
        evidence_id="lean-kernel:negative-consequence-bank",
        domain="lean-kernel",
        kind="diagnostic_obstruction_bank",
        contract="lean-kernel:diagnostic-routing:v1",
        scope=_scope(
            frontier=memory["current_signature"]["frontier"],
            fallback=memory["current_signature"]["fallback"],
        ),
        consequence_signature=tuple(row["probe"] + ":" + row["status"] for row in probes),
        source_ref=memory_url,
        source_sha256=_sha256(memory_bytes),
        metrics=_metrics(
            falsified_probe_count=len(probes),
            accept=retained["accept"],
            reject=retained["reject"],
            unknown=retained["unknown"],
            wrong=retained["wrong"],
        ),
        pattern_ids=("negative_evidence_as_search_capital",),
    )
    qualification = AuthorityEvidence(
        evidence_id="lean-kernel:qualification-snapshot",
        domain="lean-kernel",
        kind="kernel_qualification",
        contract="lean-kernel:verdict-semantics:v1",
        scope=_scope(runtime_revision=str(qual.get("runtime_revision"))),
        consequence_signature=(
            "correct=183",
            "wrong=0",
            "unknown=7",
            "errors=0",
        ),
        source_ref=qual_url,
        source_sha256=_sha256(qual_bytes),
        metrics=_metrics(**totals),
        pattern_ids=(),
    )
    return [diagnostic, qualification], {
        "memory_sha256": _sha256(memory_bytes),
        "qualification_sha256": _sha256(qual_bytes),
        "negative_probe_count": len(probes),
    }


def load_gpu_ir() -> tuple[list[AuthorityEvidence], dict[str, Any]]:
    evidence_bytes, evidence_url = _raw(GPU_REPO, GPU_COMMIT, GPU_EVIDENCE_PATH)
    evidence = json.loads(evidence_bytes)
    run = _api(f"repos/{GPU_REPO}/actions/runs/{GPU_RUN}")
    if run.get("conclusion") != "success":
        raise AssertionError("GPU developmental V1 run is not successful")
    if evidence.get("finite_ir_verdict") != "PASS":
        raise AssertionError("GPU finite IR gate is not PASS")
    if evidence.get("cold_search") != 120 or evidence.get("warm_search") != 24:
        raise AssertionError("GPU frozen search economics changed")
    if evidence.get("hardware_authority", {}).get("status") != "GPU_HARDWARE_AUTHORITY_UNAVAILABLE":
        raise AssertionError("GPU hardware boundary unexpectedly changed")

    finite = AuthorityEvidence(
        evidence_id="gpu-ir:v1:verified-developmental-optimization",
        domain="gpu-ir",
        kind="verified_optimization_capability",
        contract="developmental:verified-state-compilation:v1",
        scope=_scope(
            substrate="finite-kernel-ir",
            hardware="unclaimed",
        ),
        consequence_signature=(
            "source_acquire",
            "verify",
            "persist",
            "restart",
            "reuse",
            "ablation_restores_cold",
        ),
        source_ref=evidence_url,
        source_sha256=_sha256(evidence_bytes),
        metrics=_metrics(
            cold_search=evidence["cold_search"],
            warm_search=evidence["warm_search"],
            restart_search=evidence["restart_search"],
            sham_search=evidence["sham_search"],
            ablation_search=evidence["ablation_search"],
            search_reduction=evidence["search_reduction"],
        ),
        pattern_ids=("verified_state_compilation", "restartable_capability_reuse"),
    )
    hardware_boundary = AuthorityEvidence(
        evidence_id="gpu-hardware:v1:no-authority",
        domain="gpu-hardware",
        kind="authority_boundary",
        contract="gpu-hardware:latency:v1",
        scope=_scope(runner="github-ubuntu"),
        consequence_signature=("GPU_HARDWARE_AUTHORITY_UNAVAILABLE",),
        source_ref=evidence_url,
        source_sha256=_sha256(evidence_bytes),
        metrics=_metrics(nvidia_smi_present=False),
        pattern_ids=(),
    )
    return [finite, hardware_boundary], {
        "run_id": GPU_RUN,
        "run_head_sha": run.get("head_sha"),
        "evidence_sha256": _sha256(evidence_bytes),
    }


def destination_verifier_factory(graph: RealFlashGraph):
    def verify(source, destination_domain, claim, exact_scope):
        # Direct semantic content never crosses domains merely because names look similar.
        if claim == "direct_semantic_content":
            if source.domain == destination_domain:
                return "VERIFIED", "same-domain contract; destination identity preserved", source.evidence_id
            return (
                "TYPE_MISMATCH",
                f"source contract {source.contract} has no declared semantic adapter into {destination_domain}",
                None,
            )

        if claim == "verified_state_compilation":
            candidates = [
                row
                for row in graph.evidence.values()
                if row.domain == destination_domain
                and "verified_state_compilation" in row.pattern_ids
            ]
            if candidates:
                chosen = sorted(candidates, key=lambda row: row.evidence_id)[0]
                return (
                    "VERIFIED",
                    "destination has independent cold/warm/restart/ablation authority for the same developmental pattern",
                    chosen.evidence_id,
                )
            return (
                "UNKNOWN_AUTHORITY",
                "destination lacks an independent cold/warm/restart/ablation qualification for this meta-pattern",
                None,
            )

        if claim == "exact_refutation_cache":
            candidates = [
                row
                for row in graph.evidence.values()
                if row.domain == destination_domain
                and "exact_refutation_cache" in row.pattern_ids
            ]
            if candidates:
                chosen = sorted(candidates, key=lambda row: row.evidence_id)[0]
                return "VERIFIED", "destination independently qualifies exact refutation reuse", chosen.evidence_id
            return (
                "UNKNOWN_AUTHORITY",
                "destination has no exact repeated-refutation restart qualification",
                None,
            )

        if claim == "gpu_hardware_speedup":
            if destination_domain != "gpu-hardware":
                return "TYPE_MISMATCH", "hardware latency claim requires gpu-hardware authority", None
            boundary = graph.evidence.get("gpu-hardware:v1:no-authority")
            return (
                "UNKNOWN_AUTHORITY",
                "finite IR pass cannot authorize CUDA/Triton hardware speedup; runner had no GPU",
                boundary.evidence_id if boundary else None,
            )

        return "UNKNOWN_AUTHORITY", f"no destination verifier registered for claim {claim}", None

    return verify


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True)
    args = p.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    graph = RealFlashGraph(("sair", "arc", "lean-kernel", "gpu-ir", "gpu-hardware"))

    sources: dict[str, Any] = {}
    for loader, name in (
        (load_sair, "sair"),
        (load_arc, "arc"),
        (load_lean_kernel, "lean-kernel"),
        (load_gpu_ir, "gpu"),
    ):
        evidence_rows, source_meta = loader()
        for row in evidence_rows:
            graph.add_evidence(row)
        sources[name] = source_meta

    # Real unresolved protocol questions. A compiled meta-pattern is allowed to
    # settle only domains that independently support it.
    graph.add_residual(ProtocolResidual(
        "res:sair:should-reuse-verified-state",
        "sair",
        "verified_state_compilation",
        100,
    ))
    graph.add_residual(ProtocolResidual(
        "res:arc:should-reuse-verified-state",
        "arc",
        "verified_state_compilation",
        80,
    ))
    graph.add_residual(ProtocolResidual(
        "res:gpu-ir:should-reuse-verified-state",
        "gpu-ir",
        "verified_state_compilation",
        120,
    ))
    graph.add_residual(ProtocolResidual(
        "res:lean-kernel:restartable-negative-reuse",
        "lean-kernel",
        "verified_state_compilation",
        200,
    ))
    graph.add_residual(ProtocolResidual(
        "res:gpu-hardware:promote-ir-capability",
        "gpu-hardware",
        "verified_state_compilation",
        300,
    ))

    verify = destination_verifier_factory(graph)

    # Meta-level transfer is allowed only after independent destination authority.
    meta_arc = graph.propose_transfer(
        source_evidence_id="sair:v6:compiled-verified-state",
        destination_domain="arc",
        claim="verified_state_compilation",
        exact_scope={"level": "developmental-protocol"},
        verifier=verify,
    )
    meta_gpu = graph.propose_transfer(
        source_evidence_id="sair:v6:compiled-verified-state",
        destination_domain="gpu-ir",
        claim="verified_state_compilation",
        exact_scope={"level": "developmental-protocol"},
        verifier=verify,
    )
    meta_kernel = graph.propose_transfer(
        source_evidence_id="sair:v6:compiled-verified-state",
        destination_domain="lean-kernel",
        claim="verified_state_compilation",
        exact_scope={"level": "developmental-protocol"},
        verifier=verify,
    )
    meta_hardware = graph.propose_transfer(
        source_evidence_id="sair:v6:compiled-verified-state",
        destination_domain="gpu-hardware",
        claim="gpu_hardware_speedup",
        exact_scope={"metric": "wall-time-latency"},
        verifier=verify,
    )

    # Direct content-transfer attempts are rejected by typed contract mismatch.
    direct_content = []
    for source_id, destination in (
        ("sair:v5:three-countermodels", "arc"),
        ("sair:v5:three-countermodels", "lean-kernel"),
        ("arc:v3:action6-fatal-transfer-refutation", "sair"),
        ("lean-kernel:negative-consequence-bank", "gpu-ir"),
    ):
        direct_content.append(
            graph.propose_transfer(
                source_evidence_id=source_id,
                destination_domain=destination,
                claim="direct_semantic_content",
                exact_scope={"mode": "literal-content-transfer"},
                verifier=verify,
            )
        )

    # Repeating the same rejected proposals must be free: exact failures become capital.
    repeated_blocks = []
    for source_id, destination in (
        ("sair:v5:three-countermodels", "arc"),
        ("sair:v5:three-countermodels", "lean-kernel"),
        ("arc:v3:action6-fatal-transfer-refutation", "sair"),
        ("lean-kernel:negative-consequence-bank", "gpu-ir"),
    ):
        repeated_blocks.append(
            graph.propose_transfer(
                source_evidence_id=source_id,
                destination_domain=destination,
                claim="direct_semantic_content",
                exact_scope={"mode": "literal-content-transfer"},
                verifier=verify,
            )
        )

    # Existing ARC authority independently verifies exact-refutation caching. Lean does not.
    arc_refutation_to_kernel = graph.propose_transfer(
        source_evidence_id="arc:v3:restarted-exact-refutation",
        destination_domain="lean-kernel",
        claim="exact_refutation_cache",
        exact_scope={"level": "developmental-protocol"},
        verifier=verify,
    )

    compiled = graph.compile_meta_pattern("verified_state_compilation", min_domains=3)
    if compiled is None:
        raise AssertionError("three-domain verified-state-compilation pattern failed to compile")

    snapshot = graph.snapshot()

    settled = {
        rid for rid, row in graph.residuals.items() if row.status == "SETTLED"
    }
    open_residuals = {
        rid for rid, row in graph.residuals.items() if row.status == "OPEN"
    }
    expected_settled = {
        "res:sair:should-reuse-verified-state",
        "res:arc:should-reuse-verified-state",
        "res:gpu-ir:should-reuse-verified-state",
    }
    expected_open = {
        "res:lean-kernel:restartable-negative-reuse",
        "res:gpu-hardware:promote-ir-capability",
    }

    gates = {
        "sair_to_arc_meta_verified": meta_arc.status == "VERIFIED",
        "sair_to_gpu_ir_meta_verified": meta_gpu.status == "VERIFIED",
        "lean_kernel_meta_not_overclaimed": meta_kernel.status == "UNKNOWN_AUTHORITY",
        "gpu_hardware_not_overclaimed": meta_hardware.status == "UNKNOWN_AUTHORITY",
        "direct_content_all_scoped": all(row.status == "TYPE_MISMATCH" for row in direct_content),
        "repeated_bad_transfers_zero_verifier_calls": all(
            row.status == "BLOCKED_BY_EXACT_REFUTATION" and row.verifier_calls == 0
            for row in repeated_blocks
        ),
        "arc_refutation_cache_not_assumed_in_lean": arc_refutation_to_kernel.status == "UNKNOWN_AUTHORITY",
        "meta_capability_supported_by_three_domains": set(compiled.supporting_domains)
        == {"sair", "arc", "gpu-ir"},
        "only_authorized_protocol_residuals_settled": settled == expected_settled,
        "missing_authority_residuals_stay_open": open_residuals == expected_open,
        "gpu_ir_pass_hardware_boundary_preserved": graph.evidence[
            "gpu-hardware:v1:no-authority"
        ].consequence_signature == ("GPU_HARDWARE_AUTHORITY_UNAVAILABLE",),
    }

    result = {
        "schema": "qckn-real-multidomain-flash-v1",
        "verdict": "PASS" if all(gates.values()) else "FAIL",
        "sources": sources,
        "gates": gates,
        "cross_domain_result": {
            "genuine_meta_flash": {
                "pattern": "verified_state_compilation",
                "supporting_domains": list(compiled.supporting_domains),
                "supporting_evidence_ids": list(compiled.supporting_evidence_ids),
                "settled_protocol_residuals": sorted(settled),
                "estimated_protocol_search_cancelled": graph.total_residual_cost_cancelled,
            },
            "scoped_content": {
                "direct_transfer_attempts": len(direct_content),
                "type_mismatches": sum(row.status == "TYPE_MISMATCH" for row in direct_content),
                "cached_repeat_blocks": graph.total_cached_transfer_blocks,
            },
            "still_unresolved": sorted(open_residuals),
            "next_priority": [
                {
                    "residual_id": row.residual_id,
                    "domain": row.domain,
                    "estimated_cost": row.estimated_cost,
                    "reason": (
                        "requires destination-specific authority before Flash may mutate shared state"
                    ),
                }
                for row in sorted(
                    (r for r in graph.residuals.values() if r.status == "OPEN"),
                    key=lambda r: (-r.estimated_cost, r.residual_id),
                )
            ],
        },
        "snapshot": snapshot,
        "claim_boundary": (
            "Real public evidence from SAIR/OpenRouter, ARC3, Lean-kernel diagnostics, and a finite "
            "GPU-kernel IR gate is attached to one authority-gated consequence graph. The graph "
            "confirms a cross-domain developmental pattern only where each destination has independent "
            "cold/warm/restart/ablation evidence. Mathematical/game/kernel content remains scoped; "
            "missing Lean restart authority and missing GPU hardware authority remain OPEN rather than "
            "being inferred from analogy. No arbitrary semantic cross-domain transfer is claimed."
        ),
    }

    (out / "real-multidomain-flash-v1.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    (out / "source-manifest.json").write_text(
        json.dumps(sources, indent=2, sort_keys=True) + "\n"
    )

    print(json.dumps({
        "verdict": result["verdict"],
        "gates": gates,
        "cross_domain_result": result["cross_domain_result"],
        "claim_boundary": result["claim_boundary"],
    }, indent=2, sort_keys=True))
    print("PASS_REAL_MULTIDOMAIN_META_FLASH" if gates["meta_capability_supported_by_three_domains"] else "FAIL_REAL_MULTIDOMAIN_META_FLASH")
    print("PASS_REAL_CONTENT_SCOPE_GUARDS" if gates["direct_content_all_scoped"] else "FAIL_REAL_CONTENT_SCOPE_GUARDS")
    print("PASS_REAL_FAILURE_CAPITAL_REUSE" if gates["repeated_bad_transfers_zero_verifier_calls"] else "FAIL_REAL_FAILURE_CAPITAL_REUSE")
    print("PASS_MISSING_AUTHORITY_REMAINS_OPEN" if gates["missing_authority_residuals_stay_open"] else "FAIL_MISSING_AUTHORITY_REMAINS_OPEN")
    print("PASS_QCKN_REAL_MULTIDOMAIN_FLASH_V1" if result["verdict"] == "PASS" else "FAIL_QCKN_REAL_MULTIDOMAIN_FLASH_V1")
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
