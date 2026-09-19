from __future__ import annotations

import argparse
import json
from pathlib import Path

import qckn_real_multidomain_flash_v1 as v1
import qckn_real_multidomain_flash_v2 as v2
from realitygraph.flash_bus import (
    BridgeCertificate,
    DomainContract,
    EvidenceEvent,
    GlobalFlashBus,
    TypedCost,
)
from realitygraph.real_flash import (
    AuthorityEvidence,
    ProtocolResidual,
    RealFlashGraph,
)


HARDWARE_REPO = "heathsanchez/test"
HARDWARE_DOC_COMMIT = "47f27134d058d238d6fe5fb561fbfa06163bf01e"
HARDWARE_DOC_PATH = "docs/evidence/gpu-developmental-hardware-v1.md"
HARDWARE_RUN = 35412218742
HARDWARE_ARTIFACT = 10574349230
HARDWARE_ARTIFACT_DIGEST = (
    "sha256:b386f11d3af43d20722bb10d5cce37726a9909df79f0b4d042655cf968801873"
)
HARDWARE_HEAD_SHA = "e7a2dfd472fc33aeeefa6d675a8b5416050aeee2"


def load_hardware_authority() -> tuple[AuthorityEvidence, dict]:
    doc_bytes, doc_url = v1._raw(
        HARDWARE_REPO,
        HARDWARE_DOC_COMMIT,
        HARDWARE_DOC_PATH,
    )
    text = doc_bytes.decode("utf-8")
    run = v1._api(
        f"repos/{HARDWARE_REPO}/actions/runs/{HARDWARE_RUN}"
    )
    artifact = v1._api(
        f"repos/{HARDWARE_REPO}/actions/artifacts/{HARDWARE_ARTIFACT}"
    )

    if run.get("conclusion") != "success":
        raise AssertionError("pinned GPU hardware authority run is not green")
    if run.get("head_sha") != HARDWARE_HEAD_SHA:
        raise AssertionError("GPU hardware authority head changed")
    if artifact.get("digest") != HARDWARE_ARTIFACT_DIGEST:
        raise AssertionError("GPU hardware artifact digest changed")

    required = (
        "NVIDIA GeForce RTX 4090",
        "Both transformed outputs were bit-exact equal",
        "two-pass: **0.038112 ms**",
        "fused: **0.025568 ms**",
        "speedup: **1.4906×**",
        "affine + identity: **0.038768 ms**",
        "identity removed: **0.024576 ms**",
        "speedup: **1.5775×**",
        "PASS_GPU_HARDWARE_AUTHORITY_V1",
    )
    if not all(row in text for row in required):
        raise AssertionError("GPU hardware published evidence changed")

    evidence = AuthorityEvidence(
        evidence_id="gpu-hardware:v1:rtx4090-triton-promotion",
        domain="gpu-hardware",
        kind="measured_performance_authority",
        contract="gpu-hardware:rtx4090-triton:v1",
        scope=v1._scope(
            gpu="NVIDIA GeForce RTX 4090",
            compute_capability="8.9",
            dtype="int32",
            n_elements="4194304",
            transformations="fuse_adjacent_affine,remove_identity",
        ),
        consequence_signature=(
            "bit_exact_fused_affine",
            "bit_exact_identity_removal",
            "fuse_adjacent_affine_speedup_gt_1.05",
            "remove_identity_speedup_gt_1.05",
        ),
        source_ref=doc_url,
        source_sha256=v1._sha256(doc_bytes),
        metrics=v1._metrics(
            fuse_adjacent_affine_speedup=1.4906133040570886,
            remove_identity_speedup=1.5774738633969323,
            two_pass_affine_ms=0.03811199963092804,
            fused_affine_ms=0.025567999109625816,
            affine_plus_identity_ms=0.03876799903810024,
            affine_without_identity_ms=0.02457600086927414,
            repetitions=60,
            warmup=12,
        ),
        pattern_ids=("verified_hardware_promotion",),
    )
    return evidence, {
        "run_id": HARDWARE_RUN,
        "artifact_id": HARDWARE_ARTIFACT,
        "artifact_digest": artifact.get("digest"),
        "head_sha": run.get("head_sha"),
        "doc_commit": HARDWARE_DOC_COMMIT,
        "doc_sha256": v1._sha256(doc_bytes),
        "gpu": "NVIDIA GeForce RTX 4090",
        "fuse_adjacent_affine_speedup": 1.4906133040570886,
        "remove_identity_speedup": 1.5774738633969323,
    }


def make_bus() -> GlobalFlashBus:
    return GlobalFlashBus(
        domain_contracts=(
            DomainContract("sair", "sair-v6-public", "mathgraph-finite-checker"),
            DomainContract("arc", "arc-v3-public", "arc-destination-replay"),
            DomainContract(
                "lean-kernel",
                "lean-negative-v1",
                "diagnostic-routing-replay",
            ),
            DomainContract("gpu-ir", "gpu-ir-v1", "gpu-ir-exhaustive"),
            DomainContract(
                "gpu-hardware",
                "gpu-hardware-v1",
                "rtx4090-triton-authority",
            ),
            DomainContract(
                "developmental",
                "qckn-meta-v3",
                "four-domain-independent-support",
            ),
        ),
        bridge_contract=DomainContract(
            "bridge",
            "qckn-real-bridge-v3",
            "authority-gated-meta-and-hardware-bridge",
        ),
    )


def bus_events() -> tuple[EvidenceEvent, ...]:
    return (
        EvidenceEvent(
            event_id="sair:v6:verified-state-compilation",
            domain="sair",
            consequence_kind="verified-state-compilation",
            consequence_key="restartable-verified-state",
            authority_snapshot="sair-v6-public",
            verifier_id="mathgraph-finite-checker",
            provenance="run:35402936630",
            avoided_cost=TypedCost("sair.openrouter_model_calls", 231),
        ),
        EvidenceEvent(
            event_id="arc:v3:verified-state-compilation",
            domain="arc",
            consequence_kind="verified-state-compilation",
            consequence_key="restartable-verified-state",
            authority_snapshot="arc-v3-public",
            verifier_id="arc-destination-replay",
            provenance="run:35405566334/artifact:10571953522",
            avoided_cost=TypedCost("arc.destination_verifier_calls", 8),
        ),
        EvidenceEvent(
            event_id="lean:v1:verified-state-compilation",
            domain="lean-kernel",
            consequence_kind="verified-state-compilation",
            consequence_key="restartable-verified-state",
            authority_snapshot="lean-negative-v1",
            verifier_id="diagnostic-routing-replay",
            provenance="run:35406929514/artifact:10572986183",
            avoided_cost=TypedCost("lean.diagnostic_verifier_calls", 8),
        ),
        EvidenceEvent(
            event_id="gpu-ir:v1:verified-state-compilation",
            domain="gpu-ir",
            consequence_kind="verified-state-compilation",
            consequence_key="restartable-verified-state",
            authority_snapshot="gpu-ir-v1",
            verifier_id="gpu-ir-exhaustive",
            provenance="run:35405925307/artifact:10571694324",
            avoided_cost=TypedCost("gpu_ir.developmental_search_steps", 96),
        ),
        EvidenceEvent(
            event_id="gpu-ir:v1:optimization-content",
            domain="gpu-ir",
            consequence_kind="domain-content",
            consequence_key="remove-identity-and-fuse-affine",
            authority_snapshot="gpu-ir-v1",
            verifier_id="gpu-ir-exhaustive",
            provenance="run:35405925307",
        ),
        EvidenceEvent(
            event_id="gpu-hardware:v1:measured-promotion",
            domain="gpu-hardware",
            consequence_kind="measured-performance-authority",
            consequence_key="rtx4090-triton:fuse-affine+remove-identity",
            authority_snapshot="gpu-hardware-v1",
            verifier_id="rtx4090-triton-authority",
            provenance="run:35412218742/artifact:10574349230",
        ),
        # Unbridged literal domain content controls.
        EvidenceEvent(
            event_id="sair:v5:magma-content",
            domain="sair",
            consequence_kind="domain-content",
            consequence_key="three-finite-magma-countermodels",
            authority_snapshot="sair-v6-public",
            verifier_id="mathgraph-finite-checker",
            provenance="mathgraph:frozen-v5-bank",
        ),
        EvidenceEvent(
            event_id="arc:v3:action6-content",
            domain="arc",
            consequence_kind="domain-content",
            consequence_key="ft09-vc33-action6-refutation",
            authority_snapshot="arc-v3-public",
            verifier_id="arc-destination-replay",
            provenance="run:35405566334",
        ),
        EvidenceEvent(
            event_id="lean:v1:diagnostic-content",
            domain="lean-kernel",
            consequence_kind="domain-content",
            consequence_key="eight-falsified-diagnostic-routes",
            authority_snapshot="lean-negative-v1",
            verifier_id="diagnostic-routing-replay",
            provenance="run:35406929514",
        ),
    )


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
        (v1.load_gpu_ir, "gpu-ir"),
    ):
        evidence_rows, source_meta = loader()
        for row in evidence_rows:
            graph.add_evidence(row)
        sources[name] = source_meta

    lean_restart, lean_meta = v2.load_lean_restart_authority()
    graph.add_evidence(lean_restart)
    sources["lean-kernel-restart"] = lean_meta

    hardware, hardware_meta = load_hardware_authority()
    graph.add_evidence(hardware)
    sources["gpu-hardware"] = hardware_meta

    for residual in (
        ProtocolResidual(
            "res:sair:reuse-verified-state",
            "sair",
            "verified_state_compilation",
            100,
        ),
        ProtocolResidual(
            "res:arc:reuse-verified-state",
            "arc",
            "verified_state_compilation",
            80,
        ),
        ProtocolResidual(
            "res:lean-kernel:reuse-negative-state",
            "lean-kernel",
            "verified_state_compilation",
            200,
        ),
        ProtocolResidual(
            "res:gpu-ir:reuse-verified-state",
            "gpu-ir",
            "verified_state_compilation",
            120,
        ),
        ProtocolResidual(
            "res:gpu-hardware:promote-ir-capability",
            "gpu-hardware",
            "verified_hardware_promotion",
            300,
        ),
    ):
        graph.add_residual(residual)

    compiled = graph.compile_meta_pattern(
        "verified_state_compilation",
        min_domains=4,
    )
    if compiled is None:
        raise AssertionError("four-domain developmental meta-capability missing")

    hardware_residual = graph.settle_residual_with_evidence(
        "res:gpu-hardware:promote-ir-capability",
        evidence_id="gpu-hardware:v1:rtx4090-triton-promotion",
    )
    if hardware_residual.status != "SETTLED":
        raise AssertionError("hardware residual failed destination-local closure")

    # Preserve literal-content controls from earlier generations.
    verify = v1.destination_verifier_factory(graph)
    direct_controls = []
    for source_id, destination in (
        ("sair:v5:three-countermodels", "arc"),
        ("sair:v5:three-countermodels", "lean-kernel"),
        ("arc:v3:action6-fatal-transfer-refutation", "sair"),
        ("lean-kernel:v1:restartable-negative-reuse", "gpu-ir"),
    ):
        direct_controls.append(
            graph.propose_transfer(
                source_evidence_id=source_id,
                destination_domain=destination,
                claim="direct_semantic_content",
                exact_scope={"mode": "literal-content-transfer"},
                verifier=verify,
            )
        )

    bus = make_bus()
    events = bus_events()
    for event in events:
        bus.admit_event(event)
    if bus.cross_domain_edges():
        raise AssertionError("unlicensed cross-domain edges exist before bridges")

    graph_digest = graph.snapshot()["digest"]
    meta_certificate = "four-domain-meta:" + graph_digest[:24]
    for domain in ("sair", "arc", "lean-kernel", "gpu-ir"):
        bus.admit_bridge(
            BridgeCertificate(
                bridge_id=(
                    f"{domain}->developmental:"
                    "verified-state-compilation:v3"
                ),
                source_domain=domain,
                source_kind="verified-state-compilation",
                source_key="restartable-verified-state",
                destination_domain="developmental",
                destination_kind="meta-capability",
                destination_key="verified_state_compilation",
                bridge_authority_snapshot="qckn-real-bridge-v3",
                bridge_verifier_id=(
                    "authority-gated-meta-and-hardware-bridge"
                ),
                certificate_id=meta_certificate,
            )
        )

    hardware_certificate = (
        "gpu-hardware:"
        + HARDWARE_ARTIFACT_DIGEST.replace("sha256:", "")[:24]
    )
    bus.admit_bridge(
        BridgeCertificate(
            bridge_id="gpu-ir->gpu-hardware:measured-promotion:v1",
            source_domain="gpu-ir",
            source_kind="domain-content",
            source_key="remove-identity-and-fuse-affine",
            destination_domain="gpu-hardware",
            destination_kind="measured-performance-capability",
            destination_key="rtx4090-triton:fuse-affine+remove-identity",
            bridge_authority_snapshot="qckn-real-bridge-v3",
            bridge_verifier_id=(
                "authority-gated-meta-and-hardware-bridge"
            ),
            certificate_id=hardware_certificate,
        )
    )

    edges = bus.cross_domain_edges()
    meta_edges = [
        edge for edge in edges if edge.destination_domain == "developmental"
    ]
    hardware_edges = [
        edge for edge in edges if edge.destination_domain == "gpu-hardware"
    ]

    literal_content_ids = {
        "sair:v5:magma-content",
        "arc:v3:action6-content",
        "lean:v1:diagnostic-content",
    }
    leaked_literal_edges = [
        edge for edge in edges if edge.source_event_id in literal_content_ids
    ]

    typed_costs = bus.avoided_costs_by_unit()
    scalarization_rejected = False
    try:
        bus.scalar_avoided_cost()
    except ValueError:
        scalarization_rejected = True

    open_residuals = {
        rid
        for rid, row in graph.residuals.items()
        if row.status == "OPEN"
    }
    settled_residuals = {
        rid
        for rid, row in graph.residuals.items()
        if row.status == "SETTLED"
    }

    gates = {
        "four_domain_meta_capability_preserved": set(
            compiled.supporting_domains
        ) == {"sair", "arc", "lean-kernel", "gpu-ir"},
        "hardware_authority_run_green": (
            hardware_meta["artifact_digest"] == HARDWARE_ARTIFACT_DIGEST
            and hardware_meta["head_sha"] == HARDWARE_HEAD_SHA
        ),
        "hardware_exact_correctness_and_speed_gate": (
            hardware.metric_map["fuse_adjacent_affine_speedup"] > 1.05
            and hardware.metric_map["remove_identity_speedup"] > 1.05
        ),
        "hardware_residual_settled_locally": (
            hardware_residual.settled_by
            == "gpu-hardware:v1:rtx4090-triton-promotion"
        ),
        "no_declared_authority_residuals_open": not open_residuals,
        "all_five_declared_residuals_settled": len(settled_residuals) == 5,
        "exactly_four_developmental_meta_edges": len(meta_edges) == 4,
        "exactly_one_hardware_promotion_edge": (
            len(hardware_edges) == 1
            and hardware_edges[0].source_domain == "gpu-ir"
            and hardware_edges[0].certificate_id == hardware_certificate
        ),
        "unrelated_literal_content_remains_unbridged": (
            len(leaked_literal_edges) == 0
        ),
        "direct_content_controls_still_type_mismatch": all(
            row.status == "TYPE_MISMATCH" for row in direct_controls
        ),
        "typed_cost_units_preserved": set(typed_costs) == {
            "sair.openrouter_model_calls",
            "arc.destination_verifier_calls",
            "lean.diagnostic_verifier_calls",
            "gpu_ir.developmental_search_steps",
        },
        "heterogeneous_costs_not_scalarized": scalarization_rejected,
    }

    result = {
        "schema": "qckn-real-multidomain-flash-v3",
        "verdict": "PASS" if all(gates.values()) else "FAIL",
        "sources": sources,
        "meta_capability": {
            "pattern": compiled.pattern_id,
            "supporting_domains": list(compiled.supporting_domains),
            "supporting_evidence_ids": list(
                compiled.supporting_evidence_ids
            ),
        },
        "hardware_authority": {
            "evidence_id": hardware.evidence_id,
            "gpu": hardware.scope_map["gpu"],
            "artifact_digest": HARDWARE_ARTIFACT_DIGEST,
            "metrics": hardware.metric_map,
            "certificate_id": hardware_certificate,
        },
        "residuals": {
            rid: {
                "domain": row.domain,
                "required_pattern": row.required_pattern,
                "status": row.status,
                "settled_by": row.settled_by,
            }
            for rid, row in sorted(graph.residuals.items())
        },
        "event_bus": {
            "edge_count": len(edges),
            "meta_edge_count": len(meta_edges),
            "hardware_edge_count": len(hardware_edges),
            "edges": [
                {
                    "source_event_id": edge.source_event_id,
                    "source_domain": edge.source_domain,
                    "destination_domain": edge.destination_domain,
                    "destination_kind": edge.destination_kind,
                    "destination_key": edge.destination_key,
                    "bridge_id": edge.bridge_id,
                    "certificate_id": edge.certificate_id,
                }
                for edge in edges
            ],
            "typed_avoided_costs": typed_costs,
            "scalarization_rejected": scalarization_rejected,
            "unrelated_literal_content_edges": len(leaked_literal_edges),
        },
        "gates": gates,
        "graph_snapshot": graph.snapshot(),
        "claim_boundary": (
            "V3 closes the sole declared hardware authority residual in the "
            "initial five-domain qualification using measured RTX 4090/Triton "
            "evidence for exactly two previously verified GPU-IR transformations. "
            "The four-domain developmental meta-capability remains independently "
            "supported only by SAIR, ARC, Lean diagnostic routing and finite GPU-IR; "
            "the hardware measurement is a destination promotion, not a fifth "
            "independent developmental-learning domain. Exactly one content-level "
            "cross-domain edge is licensed: GPU-IR transformation content into its "
            "measured GPU-hardware consequence. Other domain content remains scoped. "
            "No universal GPU, universal cross-domain, or open-ended research closure "
            "claim follows."
        ),
    }

    (out / "real-multidomain-flash-v3.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    (out / "source-manifest-v3.json").write_text(
        json.dumps(sources, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps({
        "verdict": result["verdict"],
        "hardware_authority": result["hardware_authority"],
        "residuals": result["residuals"],
        "event_bus": result["event_bus"],
        "gates": result["gates"],
        "claim_boundary": result["claim_boundary"],
    }, indent=2, sort_keys=True))

    print(
        "PASS_GPU_HARDWARE_RESIDUAL_CLOSED"
        if gates["no_declared_authority_residuals_open"]
        else "FAIL_GPU_HARDWARE_RESIDUAL_CLOSED"
    )
    print(
        "PASS_EXACT_GPU_IR_TO_HARDWARE_BRIDGE"
        if gates["exactly_one_hardware_promotion_edge"]
        else "FAIL_EXACT_GPU_IR_TO_HARDWARE_BRIDGE"
    )
    print(
        "PASS_QCKN_REAL_MULTIDOMAIN_FLASH_V3"
        if result["verdict"] == "PASS"
        else "FAIL_QCKN_REAL_MULTIDOMAIN_FLASH_V3"
    )
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
