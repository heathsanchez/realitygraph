from __future__ import annotations

import unittest

from realitygraph.capability import FiniteCapability
from realitygraph.flash import (
    FlashClosure,
    FlashCompositionRule,
    FlashContract,
    FlashObstruction,
    LiveObligation,
)


AUTHORITY = "test-authority"
VERIFIER = "test-verifier"
CONTRACT = FlashContract(AUTHORITY, VERIFIER)


def cap(
    capability_id: str,
    input_type: str,
    output_type: str,
    rows: tuple[tuple[str, str], ...],
) -> FiniteCapability:
    return FiniteCapability(
        capability_id=capability_id,
        input_type=input_type,
        output_type=output_type,
        semantics=rows,
        guard_inputs=tuple(key for key, _ in rows),
        certificate_id=f"cert:{capability_id}",
        dependencies=(),
        authority_snapshot=AUTHORITY,
        verifier_id=VERIFIER,
        provenance_ids=("unit-test",),
        cost=1,
    )


class FlashClosureContracts(unittest.TestCase):
    def test_verified_capability_discharges_transported_obligations(self):
        obligation_a = LiveObligation(
            "a",
            "surface-a",
            "bit",
            "label",
            (("x", "NO"), ("y", "YES")),
            (("x", "0"), ("y", "1")),
            CONTRACT,
        )
        obligation_b = LiveObligation(
            "b",
            "surface-b",
            "bit",
            "label",
            (("p", "NO"), ("q", "YES")),
            (("p", "0"), ("q", "1")),
            CONTRACT,
        )
        engine = FlashClosure((obligation_a, obligation_b))
        decoder = cap(
            "decoder",
            "bit",
            "label",
            (("0", "NO"), ("1", "YES")),
        )
        delta = engine.admit_capability(
            decoder,
            oracle=decoder.semantics,
        )
        self.assertEqual(
            engine.discharged_obligation_ids(),
            ("a", "b"),
        )
        self.assertEqual(delta.flash_radius, 2)
        self.assertTrue(all(
            engine.obligations[key].worker_cancelled
            for key in ("a", "b")
        ))

    def test_sham_capability_cannot_mutate_shared_state(self):
        obligation = LiveObligation(
            "a",
            "bit",
            "bit",
            "label",
            (("0", "NO"), ("1", "YES")),
            (("0", "0"), ("1", "1")),
            CONTRACT,
        )
        engine = FlashClosure((obligation,))
        wrong = cap(
            "wrong",
            "bit",
            "label",
            (("0", "NO"), ("1", "NO")),
        )
        before = engine.metrics()
        with self.assertRaises(ValueError):
            engine.admit_capability(
                wrong,
                oracle=(("0", "NO"), ("1", "YES")),
            )
        after = engine.metrics()
        self.assertEqual(before["ledger_event_count"], after["ledger_event_count"])
        self.assertEqual(before["open_obligations"], after["open_obligations"])

    def test_obstruction_prunes_only_matching_contract(self):
        rows = (("0", "NO"), ("1", "NO"))
        fingerprint = FlashClosure.candidate_fingerprint(
            rows,
            input_type="bit",
            output_type="label",
            contract=CONTRACT,
        )
        same = LiveObligation(
            "same",
            "bit",
            "bit",
            "label",
            (("0", "NO"), ("1", "YES")),
            (("0", "0"), ("1", "1")),
            CONTRACT,
            (fingerprint,),
        )
        other_contract = FlashContract("other-authority", VERIFIER)
        other_fingerprint = FlashClosure.candidate_fingerprint(
            rows,
            input_type="bit",
            output_type="label",
            contract=other_contract,
        )
        other = LiveObligation(
            "other",
            "bit",
            "bit",
            "label",
            (("0", "NO"), ("1", "YES")),
            (("0", "0"), ("1", "1")),
            other_contract,
            (other_fingerprint,),
        )
        engine = FlashClosure((same, other))
        obstruction = FlashObstruction(
            "o1",
            "bit",
            "label",
            CONTRACT,
            fingerprint,
            "1",
            "YES",
            "NO",
        )
        delta = engine.admit_obstruction(obstruction)
        self.assertEqual(
            engine.obligations["same"].pruned_fingerprints,
            {fingerprint},
        )
        self.assertEqual(
            engine.obligations["other"].pruned_fingerprints,
            set(),
        )
        self.assertEqual(delta.pruned_candidate_occurrences, 1)

    def test_composition_closes_in_same_flash(self):
        source = LiveObligation(
            "target",
            "pair",
            "pair",
            "label",
            (
                ("00", "EVEN"),
                ("01", "ODD"),
                ("10", "ODD"),
                ("11", "EVEN"),
            ),
            (
                ("00", "00"),
                ("01", "01"),
                ("10", "10"),
                ("11", "11"),
            ),
            CONTRACT,
        )
        rule = FlashCompositionRule(
            "compose",
            "parity",
            "decoder",
            "pair-label",
            (
                ("00", "EVEN"),
                ("01", "ODD"),
                ("10", "ODD"),
                ("11", "EVEN"),
            ),
            "cert:pair-label",
        )
        engine = FlashClosure((source,), composition_rules=(rule,))
        parity = cap(
            "parity",
            "pair",
            "bit",
            (("00", "0"), ("01", "1"), ("10", "1"), ("11", "0")),
        )
        decoder = cap(
            "decoder",
            "bit",
            "label",
            (("0", "EVEN"), ("1", "ODD")),
        )
        engine.admit_capability(parity, oracle=parity.semantics)
        delta = engine.admit_capability(decoder, oracle=decoder.semantics)
        self.assertIn("pair-label", delta.generated_capabilities)
        self.assertEqual(engine.discharged_obligation_ids(), ("target",))
        self.assertEqual(engine.obligations["target"].solved_by, "pair-label")

    def test_revocation_reopens_only_causal_dependents(self):
        label_target = LiveObligation(
            "label",
            "pair",
            "pair",
            "label",
            (
                ("00", "EVEN"),
                ("01", "ODD"),
                ("10", "ODD"),
                ("11", "EVEN"),
            ),
            (
                ("00", "00"),
                ("01", "01"),
                ("10", "10"),
                ("11", "11"),
            ),
            CONTRACT,
        )
        decoder_target = LiveObligation(
            "decoder-target",
            "bit",
            "bit",
            "label",
            (("0", "EVEN"), ("1", "ODD")),
            (("0", "0"), ("1", "1")),
            CONTRACT,
        )
        rule = FlashCompositionRule(
            "compose",
            "parity",
            "decoder",
            "pair-label",
            label_target.oracle,
            "cert:pair-label",
        )
        engine = FlashClosure(
            (label_target, decoder_target),
            composition_rules=(rule,),
        )
        parity = cap(
            "parity",
            "pair",
            "bit",
            (("00", "0"), ("01", "1"), ("10", "1"), ("11", "0")),
        )
        decoder = cap(
            "decoder",
            "bit",
            "label",
            (("0", "EVEN"), ("1", "ODD")),
        )
        engine.admit_capability(parity, oracle=parity.semantics)
        engine.admit_capability(decoder, oracle=decoder.semantics)
        delta = engine.revoke_capability(
            "parity",
            reason="unit-test revocation",
        )
        self.assertIn("label", delta.reopened)
        self.assertNotIn("decoder-target", delta.reopened)
        self.assertEqual(
            engine.obligations["decoder-target"].status,
            "DISCHARGED",
        )
        self.assertEqual(engine.obligations["label"].status, "OPEN")


if __name__ == "__main__":
    unittest.main(verbosity=2)
