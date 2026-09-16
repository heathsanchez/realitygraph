from __future__ import annotations

import unittest

from realitygraph.developmental_types import CompletenessCertificate, NoResolutionCertificate
from realitygraph.grammar import FiniteConstructor, Grammar, GrammarDelta
from realitygraph.grammar_growth import grow_grammar, apply_delta, ablate_delta
from realitygraph.residual_certificate import make_expressivity_residual


class GrammarGrowthTests(unittest.TestCase):
    def setUp(self):
        self.zero = FiniteConstructor(
            "zero", "pair", "bit", (("00", "0"), ("01", "0"), ("10", "0"), ("11", "0")), 0
        )
        self.x = FiniteConstructor(
            "x", "pair", "bit", (("00", "0"), ("01", "0"), ("10", "1"), ("11", "1")), 0
        )
        self.grammar = Grammar((self.zero, self.x))
        signatures = tuple(c.semantic_signature for c in self.grammar.constructors)
        complete = CompletenessCertificate(
            language_id=self.grammar.digest,
            substrate_scope="old-pair-observers",
            state_digest="state-g0",
            authority_snapshot="authority-frozen",
            enumerated_signatures=signatures,
            verifier_id="truth-table-exhaustive",
            replay_evidence=("old-language-exhausted",),
        )
        no_sep = NoResolutionCertificate(
            language_id=self.grammar.digest,
            state_digest="state-g0",
            authority_snapshot="authority-frozen",
            unresolved=("parity-table",),
            checked_signatures=signatures,
            verifier_id="truth-table-exhaustive",
            replay_evidence=("parity-absent",),
        )
        self.residual = make_expressivity_residual(
            obligation_id="learn-parity-observer",
            state_digest="state-g0",
            authority_snapshot="authority-frozen",
            language_id=self.grammar.digest,
            substrate_id="nand-atoms-v1",
            protected_consequences=("old-observer-semantics",),
            observational_equivalence=("old-language-parity-collapse",),
            unresolved=("parity-table",),
            completeness=complete,
            no_resolution=no_sep,
            necessary_constraints=("signature=0110",),
            candidate_version_space_digest="nand-search-space",
            replay_evidence=("frozen-fixture",),
        )

    def candidate(self, ident, signature, complexity, dependencies=()):
        keys = ("00", "01", "10", "11")
        return FiniteConstructor(
            ident,
            "pair",
            "bit",
            tuple(zip(keys, signature)),
            complexity,
            dependencies=dependencies,
            primitive_expansion=(ident,),
        )

    def test_extensional_duplicate_is_rejected_and_minimal_adequate_candidate_wins(self):
        duplicate_x = self.candidate("x-copy", "0011", 1)
        expensive = self.candidate("parity-expensive", "0110", 4)
        minimal = self.candidate("parity-minimal", "0110", 3)

        result = grow_grammar(
            self.residual,
            self.grammar,
            (expensive, duplicate_x, minimal),
            authority_snapshot="authority-frozen",
            adequate=lambda c, r: c.semantic_signature == "0110",
            preserves=lambda c: True,
            verify=lambda c: c.semantic_signature == "0110",
            verifier_id="truth-table-exhaustive",
            provenance_ids=("test-lineage",),
        )

        self.assertTrue(result.accepted)
        self.assertEqual(result.candidate.constructor_id, "parity-minimal")
        self.assertIn("extensional-duplicate", [v.reason for v in result.verdicts])
        child = apply_delta(self.grammar, result.delta)
        self.assertIn("parity-minimal", child.constructor_map)
        self.assertEqual(child.digest, result.delta.child_language_id)

    def test_delta_round_trip_and_ablation_restore_exact_parent(self):
        minimal = self.candidate("parity-minimal", "0110", 3)
        result = grow_grammar(
            self.residual,
            self.grammar,
            (minimal,),
            authority_snapshot="authority-frozen",
            adequate=lambda c, r: True,
            preserves=lambda c: True,
            verify=lambda c: True,
            verifier_id="truth-table-exhaustive",
            provenance_ids=("p",),
        )
        text = result.delta.text()
        restarted = GrammarDelta.from_text(text)
        self.assertEqual(restarted.text(), text)
        self.assertEqual(restarted, result.delta)
        child = apply_delta(self.grammar, restarted)
        parent = ablate_delta(child, restarted)
        self.assertEqual(parent.digest, self.grammar.digest)
        self.assertEqual(parent.text(), self.grammar.text())

    def test_stale_residual_or_wrong_authority_cannot_grow(self):
        candidate = self.candidate("parity-minimal", "0110", 3)
        changed_parent = Grammar((self.zero, self.x, self.candidate("one", "1111", 0)))
        with self.assertRaises(ValueError):
            grow_grammar(
                self.residual,
                changed_parent,
                (candidate,),
                authority_snapshot="authority-frozen",
                adequate=lambda c, r: True,
                preserves=lambda c: True,
                verify=lambda c: True,
                verifier_id="v",
                provenance_ids=(),
            )
        with self.assertRaises(ValueError):
            grow_grammar(
                self.residual,
                self.grammar,
                (candidate,),
                authority_snapshot="authority-other",
                adequate=lambda c, r: True,
                preserves=lambda c: True,
                verify=lambda c: True,
                verifier_id="v",
                provenance_ids=(),
            )

    def test_missing_constructor_dependency_is_not_admitted(self):
        candidate = self.candidate("dependent", "0110", 2, dependencies=("missing",))
        result = grow_grammar(
            self.residual,
            self.grammar,
            (candidate,),
            authority_snapshot="authority-frozen",
            adequate=lambda c, r: True,
            preserves=lambda c: True,
            verify=lambda c: True,
            verifier_id="v",
            provenance_ids=(),
        )
        self.assertFalse(result.accepted)
        self.assertIsNone(result.delta)
        self.assertEqual(result.verdicts[-1].reason, "missing-dependency")


if __name__ == "__main__":
    unittest.main()
