import unittest

from realitygraph.obstruction_fingerprint import canonicalize_obstruction


class ObstructionFingerprintTests(unittest.TestCase):
    def test_fingerprint_is_invariant_under_surface_relabeling(self):
        first = canonicalize_obstruction(
            input_type="pair",
            output_type="bit",
            current_partition=(("a", "b"), ("c", "d")),
            consequence_partition=(("a", "c"), ("b", "d")),
            current_language_semantic_count=4,
            authority_snapshot="authority-v3",
            verifier_id="exact-v3",
        )
        relabeled = canonicalize_obstruction(
            input_type="pair",
            output_type="bit",
            current_partition=(("z", "w"), ("v", "u")),
            consequence_partition=(("z", "v"), ("w", "u")),
            current_language_semantic_count=4,
            authority_snapshot="authority-v3",
            verifier_id="exact-v3",
        )
        self.assertEqual(first.digest, relabeled.digest)
        self.assertEqual(
            first.canonical_incidence_matrix,
            relabeled.canonical_incidence_matrix,
        )

    def test_nonisomorphic_obstruction_has_different_fingerprint(self):
        crossing = canonicalize_obstruction(
            input_type="pair",
            output_type="bit",
            current_partition=(("a", "b"), ("c", "d")),
            consequence_partition=(("a", "c"), ("b", "d")),
            current_language_semantic_count=4,
            authority_snapshot="authority-v3",
            verifier_id="exact-v3",
        )
        nested = canonicalize_obstruction(
            input_type="pair",
            output_type="bit",
            current_partition=(("a", "b", "c"), ("d",)),
            consequence_partition=(("a", "b"), ("c", "d")),
            current_language_semantic_count=4,
            authority_snapshot="authority-v3",
            verifier_id="exact-v3",
        )
        self.assertNotEqual(crossing.digest, nested.digest)

    def test_incidence_multiplicity_is_preserved(self):
        fingerprint = canonicalize_obstruction(
            input_type="row",
            output_type="label",
            current_partition=(("a", "b", "c"), ("d", "e")),
            consequence_partition=(("a", "b", "d"), ("c", "e")),
            current_language_semantic_count=7,
            authority_snapshot="authority-v3",
            verifier_id="exact-v3",
        )
        self.assertEqual(fingerprint.carrier_size, 5)
        self.assertEqual(
            sum(sum(row) for row in fingerprint.canonical_incidence_matrix),
            5,
        )

    def test_partition_validation_rejects_overlap_or_mismatched_carrier(self):
        with self.assertRaises(ValueError):
            canonicalize_obstruction(
                input_type="pair",
                output_type="bit",
                current_partition=(("a", "b"), ("b", "c")),
                consequence_partition=(("a", "b"), ("c",)),
                current_language_semantic_count=2,
                authority_snapshot="authority-v3",
                verifier_id="exact-v3",
            )
        with self.assertRaises(ValueError):
            canonicalize_obstruction(
                input_type="pair",
                output_type="bit",
                current_partition=(("a", "b"),),
                consequence_partition=(("a", "c"),),
                current_language_semantic_count=2,
                authority_snapshot="authority-v3",
                verifier_id="exact-v3",
            )

    def test_authority_and_verifier_are_part_of_fingerprint_identity(self):
        base = canonicalize_obstruction(
            input_type="pair",
            output_type="bit",
            current_partition=(("a", "b"), ("c", "d")),
            consequence_partition=(("a", "c"), ("b", "d")),
            current_language_semantic_count=4,
            authority_snapshot="authority-v3",
            verifier_id="exact-v3",
        )
        stale_authority = canonicalize_obstruction(
            input_type="pair",
            output_type="bit",
            current_partition=(("a", "b"), ("c", "d")),
            consequence_partition=(("a", "c"), ("b", "d")),
            current_language_semantic_count=4,
            authority_snapshot="authority-v3-stale",
            verifier_id="exact-v3",
        )
        other_verifier = canonicalize_obstruction(
            input_type="pair",
            output_type="bit",
            current_partition=(("a", "b"), ("c", "d")),
            consequence_partition=(("a", "c"), ("b", "d")),
            current_language_semantic_count=4,
            authority_snapshot="authority-v3",
            verifier_id="exact-v3-other",
        )
        self.assertNotEqual(base.digest, stale_authority.digest)
        self.assertNotEqual(base.digest, other_verifier.digest)


if __name__ == "__main__":
    unittest.main()
