import tempfile
import unittest
from pathlib import Path

from realitygraph.flash import ExternalEventEnvelope
from qckn_flash_cross_repo_ingest import ingest_bundles


def write_bundle(root, name, envelope, evidence):
    d = root / name
    d.mkdir()
    (d / "event.json").write_text(envelope.to_text())
    (d / "evidence.json").write_bytes(evidence)
    return d


class CrossRepoIngestionTests(unittest.TestCase):
    def test_four_typed_external_events_close_one_shared_runtime(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cap1_e = b"lean-evidence"
            cap2_e = b"sair-evidence"
            obs1_e = b"arc-evidence"
            obs2_e = b"collatz-evidence"

            def cap(event_id, repo, evidence, authority):
                return ExternalEventEnvelope.capability(
                    event_id=event_id,
                    repository=repo,
                    commit="0123456789abcdef0123456789abcdef01234567",
                    authority_snapshot=authority,
                    verifier_id="v",
                    source_evidence=evidence,
                    capability={
                        "capability_id": event_id,
                        "input_type": event_id + ":in",
                        "output_type": event_id + ":out",
                        "semantics": [["x", "y"]],
                        "guard_inputs": ["x"],
                        "certificate_id": "cert",
                        "dependencies": [],
                        "authority_snapshot": authority,
                        "verifier_id": "v",
                        "provenance_ids": ["p"],
                        "cost": 0,
                    },
                    oracle=[["x", "y"]],
                    origin=repo,
                )

            def obs(event_id, repo, evidence, authority):
                return ExternalEventEnvelope.obstruction(
                    event_id=event_id,
                    repository=repo,
                    commit="0123456789abcdef0123456789abcdef01234567",
                    authority_snapshot=authority,
                    verifier_id="v",
                    source_evidence=evidence,
                    obstruction={
                        "obstruction_id": event_id,
                        "input_type": event_id + ":in",
                        "output_type": event_id + ":out",
                        "contract": {
                            "authority_snapshot": authority,
                            "verifier_id": "v",
                        },
                        "candidate_fingerprint": event_id + ":bad",
                        "separating_input": "x",
                        "expected_output": "yes",
                        "actual_output": "no",
                        "provenance": "p",
                    },
                )

            bundles = [
                write_bundle(root, "lean", cap("lean", "repo/lean", cap1_e, "a1"), cap1_e),
                write_bundle(root, "sair", cap("sair", "repo/sair", cap2_e, "a2"), cap2_e),
                write_bundle(root, "arc", obs("arc", "repo/arc", obs1_e, "a3"), obs1_e),
                write_bundle(root, "collatz", obs("collatz", "repo/collatz", obs2_e, "a4"), obs2_e),
            ]
            summary, manifest = ingest_bundles(bundles)

            self.assertEqual(summary["external_events"], 4)
            self.assertEqual(summary["active_capabilities"], 2)
            self.assertEqual(summary["obstructions"], 2)
            self.assertEqual(summary["discharged_obligations"], 2)
            self.assertEqual(summary["pruned_candidate_occurrences"], 2)
            self.assertEqual(summary["event_count"], 4)
            self.assertEqual(summary["replay_added_events"], 0)
            self.assertEqual(len(manifest["events"]), 4)

    def test_tampered_evidence_is_rejected_before_state_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            evidence = b"right"
            envelope = ExternalEventEnvelope.capability(
                event_id="e",
                repository="repo/name",
                commit="0123456789abcdef0123456789abcdef01234567",
                authority_snapshot="a",
                verifier_id="v",
                source_evidence=evidence,
                capability={
                    "capability_id": "e",
                    "input_type": "X",
                    "output_type": "Y",
                    "semantics": [["x", "y"]],
                    "guard_inputs": ["x"],
                    "certificate_id": "c",
                    "dependencies": [],
                    "authority_snapshot": "a",
                    "verifier_id": "v",
                    "provenance_ids": [],
                    "cost": 0,
                },
                oracle=[["x", "y"]],
            )
            bundle = write_bundle(root, "bad", envelope, b"wrong")
            with self.assertRaisesRegex(ValueError, "source evidence digest"):
                ingest_bundles([bundle])


if __name__ == "__main__":
    unittest.main()
