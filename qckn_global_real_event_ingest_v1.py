from __future__ import annotations

import json

from realitygraph.flash_bus import DomainContract, EvidenceEvent, GlobalFlashBus, TypedCost


def main() -> None:
    bus = GlobalFlashBus(
        domain_contracts=(
            DomainContract("lean", "arena-510fb", "arena-semantic-parity"),
            DomainContract("arc", "arc3-public-v2", "arc3-destination-check"),
            DomainContract("collatz", "collatz-macro-v1", "exact-forward-replay"),
        ),
        bridge_contract=DomainContract(
            "bridge", "flash-bridge-v1", "independent-bridge-verifier"
        ),
    )

    events = (
        EvidenceEvent(
            event_id="lean:direct-var-v1",
            domain="lean",
            consequence_kind="certified-performance-capability",
            consequence_key="eval:direct-var",
            authority_snapshot="arena-510fb",
            verifier_id="arena-semantic-parity",
            provenance=(
                "semantic-run:35380841937;"
                "performance-run:35380563756;"
                "active-sha:74dc5ddb4584e1254f5687615e5b02795b8dc6f3"
            ),
            avoided_cost=TypedCost("lean.mathlib_wall_seconds", 1.42),
        ),
        EvidenceEvent(
            event_id="arc:online-refutation-v2",
            domain="arc",
            consequence_kind="transfer-refutation",
            consequence_key="ft09->vc33:complex_action6:fatal-family",
            authority_snapshot="arc3-public-v2",
            verifier_id="arc3-destination-check",
            provenance=(
                "run:35404864326;artifact:10571982632;"
                "digest:sha256:a0cd3c2088931f1411684156a3d83f55c0533e85e8a9d38f3bf301bc3cadd058"
            ),
            avoided_cost=TypedCost("arc.destination_verifier_calls", 7),
        ),
        EvidenceEvent(
            event_id="collatz:flash-control-v1",
            domain="collatz",
            consequence_kind="control-obstruction",
            consequence_key="propagation-no-advantage-over-upfront-guard",
            authority_snapshot="collatz-macro-v1",
            verifier_id="exact-forward-replay",
            provenance="run:35403074591;sha:0bd6cc71a5fb4268109d5b404ecbf21c7aaaf4c1",
        ),
    )

    deltas = [bus.admit_event(event) for event in events]
    evidence = {
        "schema": "qckn-global-event-bus-real-ingest-v1",
        "events": [event.event_id for event in events],
        "affected_domains": {
            delta.event_id: list(delta.affected_domains) for delta in deltas
        },
        "cross_domain_edges": [
            {
                "source_event_id": edge.source_event_id,
                "source_domain": edge.source_domain,
                "destination_domain": edge.destination_domain,
                "destination_kind": edge.destination_kind,
                "destination_key": edge.destination_key,
                "bridge_id": edge.bridge_id,
            }
            for edge in bus.cross_domain_edges()
        ],
        "typed_avoided_costs": bus.avoided_costs_by_unit(),
        "claim_boundary": (
            "shared ingestion of three verified project events with local authority "
            "and typed costs; no cross-domain semantic transfer is claimed or permitted "
            "without an independently verified exact bridge"
        ),
    }

    if evidence["cross_domain_edges"]:
        raise AssertionError("unlicensed cross-domain edge entered the shared graph")
    if set(evidence["typed_avoided_costs"]) != {
        "arc.destination_verifier_calls",
        "lean.mathlib_wall_seconds",
    }:
        raise AssertionError("typed cost units were lost or collapsed")

    print(json.dumps(evidence, sort_keys=True, indent=2))
    print("PASS_GLOBAL_REAL_EVENT_INGEST")
    print("PASS_ZERO_UNLICENSED_CROSS_DOMAIN_EDGES")
    print("PASS_TYPED_COST_SEPARATION")


if __name__ == "__main__":
    main()
