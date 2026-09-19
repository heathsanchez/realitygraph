import tempfile
import unittest
from pathlib import Path

from realitygraph.flash import ExternalEventEnvelope
from qckn_flash_cross_repo_ingest import (
    ingest_bundles,
    restore_state_bundle,
)


def write_bundle(root, name, envelope, evidence):
    d=root/name
    d.mkdir()
    (d/"event.json").write_text(envelope.to_text())
    (d/"evidence.json").write_bytes(evidence)
    return d


def fixtures(root):
    rows=[]
    for i in range(2):
        evidence=f"cap-{i}".encode()
        env=ExternalEventEnvelope.capability(
            event_id=f"cap-{i}",
            repository=f"repo/cap{i}",
            commit="0123456789abcdef0123456789abcdef01234567",
            authority_snapshot=f"a{i}",
            verifier_id="v",
            source_evidence=evidence,
            capability={
                "capability_id":f"cap-{i}",
                "input_type":f"X{i}",
                "output_type":f"Y{i}",
                "semantics":[["x","y"]],
                "guard_inputs":["x"],
                "certificate_id":"cert",
                "dependencies":[],
                "authority_snapshot":f"a{i}",
                "verifier_id":"v",
                "provenance_ids":["p"],
                "cost":0,
            },
            oracle=[["x","y"]],
            origin=f"repo/cap{i}",
        )
        rows.append(write_bundle(root,f"cap{i}",env,evidence))
    for i in range(2):
        evidence=f"obs-{i}".encode()
        env=ExternalEventEnvelope.obstruction(
            event_id=f"obs-{i}",
            repository=f"repo/obs{i}",
            commit="0123456789abcdef0123456789abcdef01234567",
            authority_snapshot=f"oa{i}",
            verifier_id="v",
            source_evidence=evidence,
            obstruction={
                "obstruction_id":f"obs-{i}",
                "input_type":f"OX{i}",
                "output_type":f"OY{i}",
                "contract":{"authority_snapshot":f"oa{i}","verifier_id":"v"},
                "candidate_fingerprint":f"bad-{i}",
                "separating_input":"x",
                "expected_output":"yes",
                "actual_output":"no",
                "provenance":"p",
            },
        )
        rows.append(write_bundle(root,f"obs{i}",env,evidence))
    return rows


class FlashColdRestartTests(unittest.TestCase):
    def test_fresh_process_restores_same_compiled_present(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            summary,_manifest,state_text=ingest_bundles(fixtures(root))
            restored,runtime=restore_state_bundle(state_text)

            keys=[
                "external_events",
                "repositories",
                "event_ids",
                "active_capabilities",
                "active_capability_ids",
                "obstructions",
                "obstruction_ids",
                "discharged_obligations",
                "discharged_obligation_ids",
                "open_obligation_ids",
                "pruned_candidate_occurrences",
                "event_count",
            ]
            for key in keys:
                self.assertEqual(restored[key],summary[key],key)
            self.assertEqual(restored["cold_restart_replayed_events"],4)
            self.assertEqual(runtime.event_ids(),tuple(summary["event_ids"]))

    def test_unchanged_events_after_cold_restart_are_noops(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            bundles=fixtures(root)
            summary,_manifest,state_text=ingest_bundles(bundles)
            restored,runtime=restore_state_bundle(state_text)
            before={
                "event_count": runtime.closure.event_count,
                "closure_count": runtime.closure.closure_count,
                "active_capabilities": runtime.closure.active_capability_ids(),
                "obstructions": tuple(sorted(runtime.closure.obstructions)),
                "open": runtime.closure.open_obligation_ids(),
                "discharged": runtime.closure.discharged_obligation_ids(),
                "pruned": tuple(
                    (oid, tuple(sorted(row.pruned_fingerprints)))
                    for oid, row in sorted(runtime.closure.obligations.items())
                ),
            }

            for path in bundles:
                envelope=ExternalEventEnvelope.from_text((path/"event.json").read_text())
                runtime.apply(envelope.to_runtime_event())

            after={
                "event_count": runtime.closure.event_count,
                "closure_count": runtime.closure.closure_count,
                "active_capabilities": runtime.closure.active_capability_ids(),
                "obstructions": tuple(sorted(runtime.closure.obstructions)),
                "open": runtime.closure.open_obligation_ids(),
                "discharged": runtime.closure.discharged_obligation_ids(),
                "pruned": tuple(
                    (oid, tuple(sorted(row.pruned_fingerprints)))
                    for oid, row in sorted(runtime.closure.obligations.items())
                ),
            }
            self.assertEqual(after,before)

    def test_tampered_persisted_event_is_rejected_on_cold_restart(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            _summary,_manifest,state_text=ingest_bundles(fixtures(root))
            tampered=state_text.replace('"actual_output":"no"','"actual_output":"maybe"',1)
            with self.assertRaises(ValueError):
                restore_state_bundle(tampered)


if __name__=="__main__":
    unittest.main()
