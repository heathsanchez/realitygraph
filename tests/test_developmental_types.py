from __future__ import annotations

import unittest

from realitygraph.developmental_types import (
    CompletenessCertificate,
    DevelopmentalResult,
    NoResolutionCertificate,
    ResultKind,
)
from realitygraph.residual_certificate import (
    ResidualCertificate,
    make_expressivity_residual,
)


class DevelopmentalTypeTests(unittest.TestCase):
    def setUp(self):
        self.complete = CompletenessCertificate(
            language_id="lang-old",
            substrate_scope="unary-x",
            state_digest="state-1",
            authority_snapshot="authority-1",
            enumerated_signatures=("0000", "1111", "0011", "1100"),
            verifier_id="finite-exhaustive-v1",
            replay_evidence=("enum:4/4",),
        )
        self.no_sep = NoResolutionCertificate(
            language_id="lang-old",
            state_digest="state-1",
            authority_snapshot="authority-1",
            unresolved=("00|01",),
            checked_signatures=("0000", "1111", "0011", "1100"),
            verifier_id="finite-exhaustive-v1",
            replay_evidence=("nosep:4/4",),
        )

    def test_expressivity_requires_both_independent_certificates(self):
        with self.assertRaises(ValueError):
            make_expressivity_residual(
                obligation_id="o1",
                state_digest="state-1",
                authority_snapshot="authority-1",
                language_id="lang-old",
                substrate_id="nand-v1",
                protected_consequences=("old-parity",),
                observational_equivalence=("00~01",),
                unresolved=("00|01",),
                completeness=None,
                no_resolution=self.no_sep,
                necessary_constraints=("separate:00|01",),
                candidate_version_space_digest="versions-1",
                replay_evidence=("fixture",),
            )
        with self.assertRaises(ValueError):
            make_expressivity_residual(
                obligation_id="o1",
                state_digest="state-1",
                authority_snapshot="authority-1",
                language_id="lang-old",
                substrate_id="nand-v1",
                protected_consequences=("old-parity",),
                observational_equivalence=("00~01",),
                unresolved=("00|01",),
                completeness=self.complete,
                no_resolution=None,
                necessary_constraints=("separate:00|01",),
                candidate_version_space_digest="versions-1",
                replay_evidence=("fixture",),
            )

    def test_expressivity_rejects_stale_state_and_authority(self):
        stale = NoResolutionCertificate(
            language_id="lang-old",
            state_digest="state-OLD",
            authority_snapshot="authority-1",
            unresolved=("00|01",),
            checked_signatures=("0000",),
            verifier_id="finite-exhaustive-v1",
            replay_evidence=("stale",),
        )
        with self.assertRaises(ValueError):
            make_expressivity_residual(
                obligation_id="o1",
                state_digest="state-1",
                authority_snapshot="authority-1",
                language_id="lang-old",
                substrate_id="nand-v1",
                protected_consequences=(),
                observational_equivalence=("00~01",),
                unresolved=("00|01",),
                completeness=self.complete,
                no_resolution=stale,
                necessary_constraints=("separate:00|01",),
                candidate_version_space_digest="v",
                replay_evidence=(),
            )

        wrong_authority = CompletenessCertificate(
            language_id="lang-old",
            substrate_scope="unary-x",
            state_digest="state-1",
            authority_snapshot="authority-OLD",
            enumerated_signatures=("0000",),
            verifier_id="finite-exhaustive-v1",
            replay_evidence=("wrong-authority",),
        )
        with self.assertRaises(ValueError):
            make_expressivity_residual(
                obligation_id="o1",
                state_digest="state-1",
                authority_snapshot="authority-1",
                language_id="lang-old",
                substrate_id="nand-v1",
                protected_consequences=(),
                observational_equivalence=("00~01",),
                unresolved=("00|01",),
                completeness=wrong_authority,
                no_resolution=self.no_sep,
                necessary_constraints=("separate:00|01",),
                candidate_version_space_digest="v",
                replay_evidence=(),
            )

    def test_residual_round_trip_is_byte_exact_and_digest_stable(self):
        cert = make_expressivity_residual(
            obligation_id="o1",
            state_digest="state-1",
            authority_snapshot="authority-1",
            language_id="lang-old",
            substrate_id="nand-v1",
            protected_consequences=("old-parity",),
            observational_equivalence=("00~01",),
            unresolved=("00|01",),
            completeness=self.complete,
            no_resolution=self.no_sep,
            necessary_constraints=("separate:00|01",),
            candidate_version_space_digest="versions-1",
            replay_evidence=("fixture",),
        )
        text = cert.text()
        restarted = ResidualCertificate.from_text(text)
        self.assertEqual(restarted, cert)
        self.assertEqual(restarted.text(), text)
        self.assertEqual(restarted.digest, cert.digest)
        self.assertEqual(restarted.residual_type, ResultKind.UNKNOWN_EXPRESSIVITY)

    def test_only_expressivity_result_requires_structural_certificate(self):
        with self.assertRaises(ValueError):
            DevelopmentalResult(
                kind=ResultKind.UNKNOWN_EXPRESSIVITY,
                obligation_id="o1",
                detail="language inadequate",
            )
        search = DevelopmentalResult(
            kind=ResultKind.UNKNOWN_SEARCH,
            obligation_id="o1",
            detail="budget exhausted",
        )
        self.assertEqual(search.kind, ResultKind.UNKNOWN_SEARCH)
        self.assertEqual(search.certificate_digest, "")


if __name__ == "__main__":
    unittest.main()
