import unittest

from realitygraph.generation_spec import GenerationSpec, LanguageEnumeration


class _Adapter:
    def __init__(self, ident: str):
        self.adapter_id = ident


def make_spec(*, future_manifest=("future-a",)):
    return GenerationSpec(
        generation_id="gen",
        obligation_id="obligation",
        input_type="pair",
        output_type="bit",
        current_language_adapter=_Adapter("current-v1"),
        lower_substrate_adapter=_Adapter("lower-v1"),
        verifier_adapter=_Adapter("verifier-v1"),
        attack_adapter=_Adapter("attack-v1"),
        acquisition_manifest=("acq",),
        growth_manifest=("growth",),
        future_manifest=future_manifest,
        resource_envelope=(("candidate_budget", 10),),
        authority_snapshot="authority-v2",
        protected_consequences=("protected",),
        required_dependency_ids=(),
    )


class GenerationSpecTests(unittest.TestCase):
    def test_generation_spec_digest_changes_when_future_manifest_changes(self):
        a = make_spec(future_manifest=("f1",))
        b = make_spec(future_manifest=("f2",))
        self.assertNotEqual(a.digest, b.digest)

    def test_generation_spec_digest_is_reproducible(self):
        self.assertEqual(make_spec().digest, make_spec().digest)

    def test_partial_language_enumeration_cannot_claim_complete(self):
        enumeration = LanguageEnumeration(
            constructors=(),
            carrier_digest="carrier",
            enumeration_digest="enum",
            replay_evidence=("budget-stop",),
            complete=False,
            search_exhausted=False,
            raw_count=0,
        )
        self.assertFalse(enumeration.complete)
        self.assertFalse(enumeration.search_exhausted)
        self.assertEqual(enumeration.semantic_signatures, ())

    def test_generation_spec_rejects_duplicate_required_dependencies(self):
        with self.assertRaises(ValueError):
            GenerationSpec(
                generation_id="gen",
                obligation_id="obligation",
                input_type="pair",
                output_type="bit",
                current_language_adapter=_Adapter("current-v1"),
                lower_substrate_adapter=_Adapter("lower-v1"),
                verifier_adapter=_Adapter("verifier-v1"),
                attack_adapter=_Adapter("attack-v1"),
                acquisition_manifest=("acq",),
                growth_manifest=("growth",),
                future_manifest=("future",),
                resource_envelope=(("candidate_budget", 10),),
                authority_snapshot="authority-v2",
                protected_consequences=("protected",),
                required_dependency_ids=("x", "x"),
            )


if __name__ == "__main__":
    unittest.main()
