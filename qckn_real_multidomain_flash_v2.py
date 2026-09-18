from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

import qckn_real_multidomain_flash_v1 as v1
from realitygraph.real_flash import (
    AuthorityEvidence,
    ProtocolResidual,
    RealFlashGraph,
)

LEAN_RESTART_RUN = 35406929514
LEAN_RESTART_ARTIFACT = 10572986183
LEAN_RESTART_ARTIFACT_DIGEST = (
    "sha256:2e3e51f43a9090dfe70f2e9240b8449fd7861512e8e98d2dbb38085a0b168bca"
)
LEAN_RESTART_HEAD = "74fb78667a425f1fcee604a9b39c843632e2c682"
LEAN_RESTART_SUMMARY_COMMIT = "402cdaf86f4d3c5122c39ced07e8366852bc5977"
LEAN_RESTART_SUMMARY_PATH = "genesis/evidence/restartable-negative-reuse-v1-summary.json"


def _artifact_bytes(repo: str, artifact_id: int) -> bytes:
    """Download an Actions artifact without leaking GitHub auth to blob storage.

    GitHub's artifact endpoint redirects to a signed storage URL. urllib's
    default redirect handling can forward Authorization to the redirected host,
    which the signed blob endpoint rejects. Resolve the redirect explicitly,
    authenticate only the GitHub API request, then fetch the signed URL without
    GitHub credentials.
    """
    url = f"https://api.github.com/repos/{repo}/actions/artifacts/{artifact_id}/zip"
    headers = {"User-Agent": v1.USER_AGENT}
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
        headers["X-GitHub-Api-Version"] = "2022-11-28"

    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, hdrs, newurl):
            return None

    opener = urllib.request.build_opener(_NoRedirect)
    request = urllib.request.Request(url, headers=headers)
    try:
        response = opener.open(request, timeout=30)
    except urllib.error.HTTPError as exc:
        if exc.code not in (301, 302, 303, 307, 308):
            raise
        location = exc.headers.get("Location")
        if not location:
            raise AssertionError("artifact redirect missing Location header")
    else:
        with response:
            return response.read()

    redirected = urllib.request.Request(
        location,
        headers={"User-Agent": v1.USER_AGENT},
    )
    with urllib.request.urlopen(redirected, timeout=60) as response:
        return response.read()


def _json_members(raw: bytes) -> list[tuple[str, dict]]:
    rows: list[tuple[str, dict]] = []
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        for name in archive.namelist():
            if not name.endswith(".json"):
                continue
            try:
                value = json.loads(archive.read(name))
            except Exception:
                continue
            if isinstance(value, dict):
                rows.append((name, value))
    return rows


def load_lean_restart_authority() -> tuple[AuthorityEvidence, dict]:
    summary_bytes, summary_url = v1._raw(
        v1.LEAN_REPO,
        LEAN_RESTART_SUMMARY_COMMIT,
        LEAN_RESTART_SUMMARY_PATH,
    )
    summary = json.loads(summary_bytes)
    run = v1._api(
        f"repos/{v1.LEAN_REPO}/actions/runs/{LEAN_RESTART_RUN}"
    )

    if run.get("conclusion") != "success":
        raise AssertionError("Lean restart authority run is not green")
    if run.get("head_sha") != LEAN_RESTART_HEAD:
        raise AssertionError("Lean restart authority head changed")
    if summary.get("schema") != "lean-restartable-negative-reuse-v1-summary":
        raise AssertionError("Lean restart summary schema changed")
    if summary.get("qualification") != "PASS_DIAGNOSTIC_REUSE_NONREGRESSION":
        raise AssertionError("Lean restart summary is not qualified")
    if summary.get("qualified_run_id") != LEAN_RESTART_RUN:
        raise AssertionError("Lean restart summary run mismatch")
    if summary.get("qualified_head_sha") != LEAN_RESTART_HEAD:
        raise AssertionError("Lean restart summary head mismatch")
    artifact = summary.get("artifact", {})
    if artifact.get("id") != LEAN_RESTART_ARTIFACT:
        raise AssertionError("Lean restart artifact ID changed")
    if artifact.get("digest") != LEAN_RESTART_ARTIFACT_DIGEST:
        raise AssertionError("Lean restart artifact digest changed")

    routing = summary.get("routing", {})
    required_routing = {
        "candidate_count": 11,
        "cold_verifier_calls": 11,
        "warm_verifier_calls": 3,
        "restart_verifier_calls": 3,
        "sham_verifier_calls": 11,
        "ablation_verifier_calls": 11,
        "changed_signature_verifier_calls": 11,
        "exact_negative_routes_skipped": 8,
        "saved_verifier_calls": 8,
    }
    for key, expected in required_routing.items():
        if routing.get(key) != expected:
            raise AssertionError(f"Lean restart routing metric changed: {key}")

    corpus = summary.get("matched_current_public_corpus", {})
    expected_totals = {
        "correct": 182,
        "unknown": 7,
        "wrong": 0,
        "errors": 0,
    }
    if corpus.get("candidate") != expected_totals:
        raise AssertionError("Lean candidate corpus totals changed")
    if corpus.get("parent") != expected_totals:
        raise AssertionError("Lean parent corpus totals changed")
    if corpus.get("exact_case_status_reason_parity") is not True:
        raise AssertionError("Lean candidate/parent corpus parity is absent")
    strict = summary.get("strict_arena_closure", {})
    if strict.get("qualified") is not False or strict.get("remaining_unknown") != 7:
        raise AssertionError("Lean strict Arena residual boundary changed")
    if summary.get("trusted_boundary") != (
        "diagnostic-routing-only; never changes ACCEPT/REJECT semantics"
    ):
        raise AssertionError("Lean trusted boundary changed")

    source_runs = tuple(summary.get("source_runs", ()))
    if len(source_runs) != 8:
        raise AssertionError("Lean source falsifier count changed")
    for source_run in source_runs:
        source = v1._api(
            f"repos/{v1.LEAN_REPO}/actions/runs/{int(source_run)}"
        )
        if source.get("conclusion") != "success":
            raise AssertionError(
                f"Lean source falsifier run is no longer green: {source_run}"
            )

    evidence = AuthorityEvidence(
        evidence_id="lean-kernel:v1:restartable-negative-reuse",
        domain="lean-kernel",
        kind="verified_negative_routing_capability",
        contract="developmental:verified-state-compilation:v1",
        scope=v1._scope(
            mode="diagnostic-routing-only",
            residual_guard=str(summary["compiled_bank_digest"]),
            corpus="current-public-arena-parent-matched",
        ),
        consequence_signature=(
            "eight_source_falsifiers_verified",
            "compiled_negative_bank",
            "warm_reuse",
            "restart_exact",
            "sham_restores_cold",
            "changed_signature_restores_cold",
            "ablation_restores_cold",
            "parent_corpus_behavior_preserved",
        ),
        source_ref=summary_url,
        source_sha256=v1._sha256(summary_bytes),
        metrics=v1._metrics(
            cold_verifier_calls=11,
            warm_verifier_calls=3,
            restart_verifier_calls=3,
            sham_verifier_calls=11,
            ablation_verifier_calls=11,
            changed_signature_verifier_calls=11,
            saved_verifier_calls=8,
            reduction_fraction=routing[
                "verifier_call_reduction_fraction"
            ],
            corpus_correct=182,
            corpus_unknown=7,
            corpus_wrong=0,
            corpus_errors=0,
        ),
        pattern_ids=(
            "verified_state_compilation",
            "restartable_capability_reuse",
            "negative_evidence_as_search_capital",
            "exact_refutation_cache",
        ),
    )
    meta = {
        "run_id": LEAN_RESTART_RUN,
        "artifact_id": LEAN_RESTART_ARTIFACT,
        "artifact_digest": artifact.get("digest"),
        "head_sha": run.get("head_sha"),
        "summary_commit": LEAN_RESTART_SUMMARY_COMMIT,
        "summary_sha256": v1._sha256(summary_bytes),
        "compiled_bank_digest": summary["compiled_bank_digest"],
        "saved_verifier_calls": routing["saved_verifier_calls"],
        "corpus_totals": corpus["candidate"],
        "source_runs_rechecked": list(source_runs),
    }
    return evidence, meta

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    graph = RealFlashGraph(
        ("sair", "arc", "lean-kernel", "gpu-ir", "gpu-hardware")
    )
    sources: dict[str, object] = {}

    for loader, name in (
        (v1.load_sair, "sair"),
        (v1.load_arc, "arc"),
        (v1.load_lean_kernel, "lean-kernel-base"),
        (v1.load_gpu_ir, "gpu"),
    ):
        evidence_rows, source_meta = loader()
        for row in evidence_rows:
            graph.add_evidence(row)
        sources[name] = source_meta

    lean_restart, lean_meta = load_lean_restart_authority()
    graph.add_evidence(lean_restart)
    sources["lean-kernel-restart"] = lean_meta

    for residual in (
        ProtocolResidual(
            "res:sair:should-reuse-verified-state",
            "sair",
            "verified_state_compilation",
            100,
        ),
        ProtocolResidual(
            "res:arc:should-reuse-verified-state",
            "arc",
            "verified_state_compilation",
            80,
        ),
        ProtocolResidual(
            "res:gpu-ir:should-reuse-verified-state",
            "gpu-ir",
            "verified_state_compilation",
            120,
        ),
        ProtocolResidual(
            "res:lean-kernel:restartable-negative-reuse",
            "lean-kernel",
            "verified_state_compilation",
            200,
        ),
        ProtocolResidual(
            "res:gpu-hardware:promote-ir-capability",
            "gpu-hardware",
            "verified_state_compilation",
            300,
        ),
    ):
        graph.add_residual(residual)

    verify = v1.destination_verifier_factory(graph)

    meta_destinations = {}
    for destination in ("arc", "gpu-ir", "lean-kernel"):
        meta_destinations[destination] = graph.propose_transfer(
            source_evidence_id="sair:v6:compiled-verified-state",
            destination_domain=destination,
            claim="verified_state_compilation",
            exact_scope={"level": "developmental-protocol"},
            verifier=verify,
        )

    hardware = graph.propose_transfer(
        source_evidence_id="sair:v6:compiled-verified-state",
        destination_domain="gpu-hardware",
        claim="gpu_hardware_speedup",
        exact_scope={"metric": "wall-time-latency"},
        verifier=verify,
    )

    direct_content = []
    direct_pairs = (
        ("sair:v5:three-countermodels", "arc"),
        ("sair:v5:three-countermodels", "lean-kernel"),
        ("arc:v3:action6-fatal-transfer-refutation", "sair"),
        ("lean-kernel:negative-consequence-bank", "gpu-ir"),
    )
    for source_id, destination in direct_pairs:
        direct_content.append(
            graph.propose_transfer(
                source_evidence_id=source_id,
                destination_domain=destination,
                claim="direct_semantic_content",
                exact_scope={"mode": "literal-content-transfer"},
                verifier=verify,
            )
        )

    repeated_blocks = []
    for source_id, destination in direct_pairs:
        repeated_blocks.append(
            graph.propose_transfer(
                source_evidence_id=source_id,
                destination_domain=destination,
                claim="direct_semantic_content",
                exact_scope={"mode": "literal-content-transfer"},
                verifier=verify,
            )
        )

    arc_to_lean_refutation = graph.propose_transfer(
        source_evidence_id="arc:v3:restarted-exact-refutation",
        destination_domain="lean-kernel",
        claim="exact_refutation_cache",
        exact_scope={"level": "developmental-protocol"},
        verifier=verify,
    )

    compiled = graph.compile_meta_pattern(
        "verified_state_compilation",
        min_domains=4,
    )
    if compiled is None:
        raise AssertionError("four-domain verified-state meta pattern failed")

    settled = {
        rid
        for rid, row in graph.residuals.items()
        if row.status == "SETTLED"
    }
    open_residuals = {
        rid
        for rid, row in graph.residuals.items()
        if row.status == "OPEN"
    }
    expected_settled = {
        "res:sair:should-reuse-verified-state",
        "res:arc:should-reuse-verified-state",
        "res:gpu-ir:should-reuse-verified-state",
        "res:lean-kernel:restartable-negative-reuse",
    }
    expected_open = {"res:gpu-hardware:promote-ir-capability"}

    gates = {
        "lean_restart_artifact_verified": (
            lean_meta["artifact_digest"] == LEAN_RESTART_ARTIFACT_DIGEST
            and lean_meta["head_sha"] == LEAN_RESTART_HEAD
            and lean_meta["saved_verifier_calls"] == 8
        ),
        "lean_meta_transfer_verified": (
            meta_destinations["lean-kernel"].status == "VERIFIED"
        ),
        "sair_to_arc_meta_verified": (
            meta_destinations["arc"].status == "VERIFIED"
        ),
        "sair_to_gpu_ir_meta_verified": (
            meta_destinations["gpu-ir"].status == "VERIFIED"
        ),
        "arc_refutation_cache_now_verified_in_lean": (
            arc_to_lean_refutation.status == "VERIFIED"
        ),
        "gpu_hardware_still_open": hardware.status == "UNKNOWN_AUTHORITY",
        "direct_content_still_scoped": all(
            row.status == "TYPE_MISMATCH" for row in direct_content
        ),
        "repeated_bad_transfers_zero_calls": all(
            row.status == "BLOCKED_BY_EXACT_REFUTATION"
            and row.verifier_calls == 0
            for row in repeated_blocks
        ),
        "meta_pattern_has_four_independent_domains": (
            set(compiled.supporting_domains)
            == {"sair", "arc", "gpu-ir", "lean-kernel"}
        ),
        "authorized_residuals_settled": settled == expected_settled,
        "gpu_hardware_is_only_open_authority_residual": (
            open_residuals == expected_open
        ),
        "protocol_search_cancelled_rises_to_500": (
            graph.total_residual_cost_cancelled == 500
        ),
    }

    snapshot = graph.snapshot()
    result = {
        "schema": "qckn-real-multidomain-flash-v2",
        "verdict": "PASS" if all(gates.values()) else "FAIL",
        "gates": gates,
        "sources": sources,
        "cross_domain_result": {
            "genuine_meta_flash": {
                "pattern": "verified_state_compilation",
                "supporting_domains": list(compiled.supporting_domains),
                "supporting_evidence_ids": list(
                    compiled.supporting_evidence_ids
                ),
                "settled_protocol_residuals": sorted(settled),
                "estimated_protocol_search_cancelled": (
                    graph.total_residual_cost_cancelled
                ),
            },
            "lean_authority": {
                "run_id": LEAN_RESTART_RUN,
                "artifact_id": LEAN_RESTART_ARTIFACT,
                "saved_verifier_calls": 8,
                "cold_calls": 11,
                "warm_restart_calls": 3,
                "matched_current_corpus": {
                    "correct": 182,
                    "unknown": 7,
                    "wrong": 0,
                    "errors": 0,
                },
                "strict_arena_unknown_residual_remains": 7,
            },
            "scoped_content": {
                "direct_transfer_attempts": len(direct_content),
                "type_mismatches": sum(
                    row.status == "TYPE_MISMATCH" for row in direct_content
                ),
                "cached_repeat_blocks": graph.total_cached_transfer_blocks,
            },
            "still_unresolved": sorted(open_residuals),
            "next_priority": [
                {
                    "residual_id": "res:gpu-hardware:promote-ir-capability",
                    "domain": "gpu-hardware",
                    "estimated_cost": 300,
                    "reason": (
                        "finite GPU-IR capability is qualified, but CUDA/Triton "
                        "hardware authority is still absent"
                    ),
                }
            ],
        },
        "snapshot": snapshot,
        "claim_boundary": (
            "Real public evidence now independently supports the developmental "
            "verified-state-compilation pattern in SAIR, ARC, GPU-IR, and Lean "
            "diagnostic routing. Lean's seven current public Arena UNKNOWNs "
            "remain an explicit separate residual; this V2 promotion does not "
            "claim strict Arena closure or direct semantic transfer between "
            "domains. GPU hardware remains unqualified."
        ),
    }

    (out / "real-multidomain-flash-v2.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    (out / "source-manifest-v2.json").write_text(
        json.dumps(sources, indent=2, sort_keys=True) + "\n"
    )

    print(
        json.dumps(
            {
                "verdict": result["verdict"],
                "gates": gates,
                "cross_domain_result": result["cross_domain_result"],
                "claim_boundary": result["claim_boundary"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    print(
        "PASS_QCKN_REAL_MULTIDOMAIN_FLASH_V2"
        if result["verdict"] == "PASS"
        else "FAIL_QCKN_REAL_MULTIDOMAIN_FLASH_V2"
    )
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
