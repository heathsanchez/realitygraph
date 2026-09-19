import unittest

from realitygraph.real_flash import AuthorityEvidence, ProtocolResidual, RealFlashGraph


def ev(eid, domain, contract, patterns=()):
    return AuthorityEvidence(
        evidence_id=eid,
        domain=domain,
        kind="fixture",
        contract=contract,
        scope=(),
        consequence_signature=(eid,),
        source_ref="fixture",
        source_sha256=eid,
        pattern_ids=patterns,
    )


class RealFlashGraphTests(unittest.TestCase):
    def test_exact_refutation_blocks_repeat_without_verifier(self):
        graph = RealFlashGraph(("a", "b"))
        graph.add_evidence(ev("a:content", "a", "a:content"))
        calls = {"n": 0}

        def verifier(source, dest, claim, scope):
            calls["n"] += 1
            return "TYPE_MISMATCH", "no adapter", None

        first = graph.propose_transfer(
            source_evidence_id="a:content",
            destination_domain="b",
            claim="direct_semantic_content",
            exact_scope={"x": "1"},
            verifier=verifier,
        )
        second = graph.propose_transfer(
            source_evidence_id="a:content",
            destination_domain="b",
            claim="direct_semantic_content",
            exact_scope={"x": "1"},
            verifier=verifier,
        )
        self.assertEqual(first.status, "TYPE_MISMATCH")
        self.assertEqual(second.status, "BLOCKED_BY_EXACT_REFUTATION")
        self.assertEqual(second.verifier_calls, 0)
        self.assertEqual(calls["n"], 1)

    def test_meta_capability_settles_only_supported_domains(self):
        graph = RealFlashGraph(("a", "b", "c"))
        graph.add_evidence(ev("a:meta", "a", "meta", ("p",)))
        graph.add_evidence(ev("b:meta", "b", "meta", ("p",)))
        graph.add_residual(ProtocolResidual("ra", "a", "p", 5))
        graph.add_residual(ProtocolResidual("rb", "b", "p", 7))
        graph.add_residual(ProtocolResidual("rc", "c", "p", 11))
        cap = graph.compile_meta_pattern("p", min_domains=2)
        self.assertIsNotNone(cap)
        self.assertEqual(graph.residuals["ra"].status, "SETTLED")
        self.assertEqual(graph.residuals["rb"].status, "SETTLED")
        self.assertEqual(graph.residuals["rc"].status, "OPEN")
        self.assertEqual(graph.total_residual_cost_cancelled, 12)



    def test_local_authority_settles_only_same_domain_exact_pattern(self):
        graph = RealFlashGraph(("gpu-ir", "gpu-hardware"))
        graph.add_evidence(
            ev(
                "hardware:measured",
                "gpu-hardware",
                "gpu-hardware:latency",
                ("verified_hardware_promotion",),
            )
        )
        graph.add_residual(
            ProtocolResidual(
                "hardware-gap",
                "gpu-hardware",
                "verified_hardware_promotion",
                13,
            )
        )
        settled = graph.settle_residual_with_evidence(
            "hardware-gap",
            evidence_id="hardware:measured",
        )
        self.assertEqual(settled.status, "SETTLED")
        self.assertEqual(settled.settled_by, "hardware:measured")
        self.assertEqual(graph.total_residual_cost_cancelled, 13)

        graph.add_residual(
            ProtocolResidual(
                "wrong-domain",
                "gpu-ir",
                "verified_hardware_promotion",
                17,
            )
        )
        with self.assertRaisesRegex(
            ValueError, "same-domain authority"
        ):
            graph.settle_residual_with_evidence(
                "wrong-domain",
                evidence_id="hardware:measured",
            )


if __name__ == "__main__":
    unittest.main()
