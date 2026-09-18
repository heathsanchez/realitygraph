import unittest

from realitygraph.flash_bus import (
    BridgeCertificate,
    DomainContract,
    EvidenceEvent,
    GlobalFlashBus,
    TypedCost,
)


class GlobalFlashBusTests(unittest.TestCase):
    def setUp(self):
        self.bus = GlobalFlashBus(
            domain_contracts=(
                DomainContract("lean", "arena-510fb", "arena-semantic-parity"),
                DomainContract("arc", "arc3-public-v2", "arc3-destination-check"),
                DomainContract("collatz", "collatz-macro-v1", "exact-forward-replay"),
            ),
            bridge_contract=DomainContract(
                "bridge", "flash-bridge-v1", "independent-bridge-verifier"
            ),
        )

    def test_event_is_local_without_verified_bridge(self):
        event = EvidenceEvent(
            event_id="lean-r2",
            domain="lean",
            consequence_kind="eval-residual",
            consequence_key="app_simple_apply",
            authority_snapshot="arena-510fb",
            verifier_id="arena-semantic-parity",
            provenance="run:35401942103/artifact:10570927402",
            avoided_cost=TypedCost("lean.retired_instructions", 100),
        )
        delta = self.bus.admit_event(event)
        self.assertEqual(delta.affected_domains, ("lean",))
        self.assertEqual(delta.cross_domain_edges, ())

    def test_foreign_authority_cannot_enter_shared_graph(self):
        event = EvidenceEvent(
            event_id="bad",
            domain="lean",
            consequence_kind="eval-residual",
            consequence_key="x",
            authority_snapshot="not-arena",
            verifier_id="arena-semantic-parity",
            provenance="bad",
        )
        with self.assertRaisesRegex(ValueError, "domain authority/verifier mismatch"):
            self.bus.admit_event(event)

    def test_cross_domain_edge_requires_exact_bridge_certificate(self):
        source = EvidenceEvent(
            event_id="arc-refutation",
            domain="arc",
            consequence_kind="transfer-refutation",
            consequence_key="ft09->vc33:complex_action6:fatal-family",
            authority_snapshot="arc3-public-v2",
            verifier_id="arc3-destination-check",
            provenance="run:35404142387/artifact:10571308957",
            avoided_cost=TypedCost("arc.destination_verifier_calls", 7),
        )
        self.bus.admit_event(source)
        self.assertEqual(self.bus.cross_domain_edges(), ())

        bridge = BridgeCertificate(
            bridge_id="arc-to-collatz-refutation-shape-v1",
            source_domain="arc",
            source_kind="transfer-refutation",
            source_key="ft09->vc33:complex_action6:fatal-family",
            destination_domain="collatz",
            destination_kind="proposal-obstruction",
            destination_key="exact-transfer-refutation",
            bridge_authority_snapshot="flash-bridge-v1",
            bridge_verifier_id="independent-bridge-verifier",
            certificate_id="bridge-cert-1",
        )
        self.bus.admit_bridge(bridge)
        edges = self.bus.cross_domain_edges()
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0].source_event_id, "arc-refutation")
        self.assertEqual(edges[0].destination_domain, "collatz")

    def test_bridge_scope_mismatch_does_not_transfer(self):
        self.bus.admit_bridge(
            BridgeCertificate(
                bridge_id="wrong-key",
                source_domain="arc",
                source_kind="transfer-refutation",
                source_key="different",
                destination_domain="collatz",
                destination_kind="proposal-obstruction",
                destination_key="exact-transfer-refutation",
                bridge_authority_snapshot="flash-bridge-v1",
                bridge_verifier_id="independent-bridge-verifier",
                certificate_id="bridge-cert-2",
            )
        )
        self.bus.admit_event(
            EvidenceEvent(
                event_id="arc-refutation",
                domain="arc",
                consequence_kind="transfer-refutation",
                consequence_key="ft09->vc33:complex_action6:fatal-family",
                authority_snapshot="arc3-public-v2",
                verifier_id="arc3-destination-check",
                provenance="run:35404142387/artifact:10571308957",
            )
        )
        self.assertEqual(self.bus.cross_domain_edges(), ())

    def test_costs_remain_typed_and_cannot_be_summed_without_conversion(self):
        self.bus.admit_event(
            EvidenceEvent(
                event_id="lean",
                domain="lean",
                consequence_kind="speedup",
                consequence_key="direct-var",
                authority_snapshot="arena-510fb",
                verifier_id="arena-semantic-parity",
                provenance="run:35380841937",
                avoided_cost=TypedCost("lean.mathlib_wall_seconds", 1.42),
            )
        )
        self.bus.admit_event(
            EvidenceEvent(
                event_id="collatz",
                domain="collatz",
                consequence_kind="search-elimination",
                consequence_key="reviewed-dominance",
                authority_snapshot="collatz-macro-v1",
                verifier_id="exact-forward-replay",
                provenance="run:35403074591",
                avoided_cost=TypedCost("collatz.T_calls", 1292484),
            )
        )
        totals = self.bus.avoided_costs_by_unit()
        self.assertEqual(totals["lean.mathlib_wall_seconds"], 1.42)
        self.assertEqual(totals["collatz.T_calls"], 1292484)
        with self.assertRaisesRegex(ValueError, "typed costs require an explicit conversion contract"):
            self.bus.scalar_avoided_cost()


if __name__ == "__main__":
    unittest.main()
