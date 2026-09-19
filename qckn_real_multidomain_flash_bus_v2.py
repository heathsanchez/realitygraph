from __future__ import annotations

import argparse
import json
from pathlib import Path

from realitygraph.flash_bus import (
    BridgeCertificate,
    DomainContract,
    EvidenceEvent,
    GlobalFlashBus,
    TypedCost,
)


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
                "hardware-latency-authority",
            ),
            DomainContract(
                "developmental",
                "qckn-meta-v2",
                "four-domain-independent-support",
            ),
        ),
        bridge_contract=DomainContract(
            "bridge",
            "qckn-real-bridge-v2",
            "authority-gated-meta-bridge",
        ),
    )


def real_events() -> tuple[EvidenceEvent, ...]:
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
            event_id="gpu-hardware:v1:authority-gap",
            domain="gpu-hardware",
            consequence_kind="authority-gap",
            consequence_key="gpu-hardware-latency-unavailable",
            authority_snapshot="gpu-hardware-v1",
            verifier_id="hardware-latency-authority",
            provenance="run:35405925307/status:GPU_HARDWARE_AUTHORITY_UNAVAILABLE",
        ),
        # Real content events deliberately have no bridge certificate.
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
        EvidenceEvent(
            event_id="gpu-ir:v1:optimization-content",
            domain="gpu-ir",
            consequence_kind="domain-content",
            consequence_key="remove-identity-and-fuse-affine",
            authority_snapshot="gpu-ir-v1",
            verifier_id="gpu-ir-exhaustive",
            provenance="run:35405925307",
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v2-result", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    result_path = Path(args.v2_result)
    v2 = json.loads(result_path.read_text())
    if v2.get("verdict") != "PASS":
        raise AssertionError("real multidomain V2 must pass before bus compilation")
    support = set(
        v2["cross_domain_result"]["genuine_meta_flash"]["supporting_domains"]
    )
    if support != {"sair", "arc", "lean-kernel", "gpu-ir"}:
        raise AssertionError("four-domain support set changed")
    if v2["cross_domain_result"]["still_unresolved"] != [
        "res:gpu-hardware:promote-ir-capability"
    ]:
        raise AssertionError("GPU hardware is not the sole residual")

    bus = make_bus()
    events = real_events()
    for event in events:
        bus.admit_event(event)

    if bus.cross_domain_edges():
        raise AssertionError("unlicensed cross-domain edge exists before bridges")

    graph_digest = str(v2["snapshot"]["digest"])
    certificate_id = "four-domain-meta:" + graph_digest[:24]

    created = []
    for domain in ("sair", "arc", "lean-kernel", "gpu-ir"):
        created.extend(
            bus.admit_bridge(
                BridgeCertificate(
                    bridge_id=(
                        f"{domain}->developmental:"
                        "verified-state-compilation:v2"
                    ),
                    source_domain=domain,
                    source_kind="verified-state-compilation",
                    source_key="restartable-verified-state",
                    destination_domain="developmental",
                    destination_kind="meta-capability",
                    destination_key="verified_state_compilation",
                    bridge_authority_snapshot="qckn-real-bridge-v2",
                    bridge_verifier_id="authority-gated-meta-bridge",
                    certificate_id=certificate_id,
                )
            )
        )

    edges = bus.cross_domain_edges()
    if len(edges) != 4:
        raise AssertionError(f"expected four meta edges, got {len(edges)}")
    if {edge.source_domain for edge in edges} != support:
        raise AssertionError("event-bus source domains do not match authority support")
    if {edge.destination_domain for edge in edges} != {"developmental"}:
        raise AssertionError("meta edges escaped the developmental destination")
    if any(edge.source_domain == "gpu-hardware" for edge in edges):
        raise AssertionError("GPU hardware received an unlicensed bridge")

    content_event_ids = {
        event.event_id
        for event in events
        if event.consequence_kind == "domain-content"
    }
    if any(edge.source_event_id in content_event_ids for edge in edges):
        raise AssertionError("literal domain content leaked through the meta bridge")

    typed_costs = bus.avoided_costs_by_unit()
    expected_units = {
        "sair.openrouter_model_calls",
        "arc.destination_verifier_calls",
        "lean.diagnostic_verifier_calls",
        "gpu_ir.developmental_search_steps",
    }
    if set(typed_costs) != expected_units:
        raise AssertionError("typed cost units changed")

    scalarization_rejected = False
    try:
        bus.scalar_avoided_cost()
    except ValueError:
        scalarization_rejected = True
    if not scalarization_rejected:
        raise AssertionError("heterogeneous costs were silently scalarized")

    evidence = {
        "schema": "qckn-real-multidomain-flash-bus-v2",
        "verdict": "PASS",
        "source_v2_result": str(result_path),
        "source_graph_digest": graph_digest,
        "certificate_id": certificate_id,
        "events": [event.event_id for event in events],
        "active_cross_domain_edges": [
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
        "content_event_ids": sorted(content_event_ids),
        "content_cross_domain_edges": 0,
        "gpu_hardware_cross_domain_edges": 0,
        "claim_boundary": (
            "Four exact bridge certificates materialize only the independently "
            "confirmed verified-state-compilation meta-pattern into the shared "
            "developmental domain. Literal SAIR, ARC, Lean-kernel and GPU-IR "
            "content events remain unbridged. Heterogeneous avoided-cost units "
            "remain typed and cannot be summed without a separate conversion "
            "authority. GPU hardware remains outside the bridge set."
        ),
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "real-multidomain-flash-bus-v2.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(evidence, indent=2, sort_keys=True))
    print("PASS_FOUR_DOMAIN_REAL_FLASH_EVENT_BUS")
    print("PASS_ZERO_LITERAL_CONTENT_BRIDGES")
    print("PASS_TYPED_COST_SEPARATION")
    print("PASS_GPU_HARDWARE_REMAINS_UNBRIDGED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
