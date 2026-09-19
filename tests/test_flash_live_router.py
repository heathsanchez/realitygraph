import tempfile
import unittest
from pathlib import Path

from realitygraph.flash import ExternalEventEnvelope
from qckn_flash_live_router import update_live_state


def write_bundle(root, name, envelope, evidence):
    d=root/name
    d.mkdir()
    (d/"event.json").write_text(envelope.to_text())
    (d/"evidence.json").write_bytes(evidence)
    return d


def cap(event_id, evidence=b"cap", authority="a"):
    return ExternalEventEnvelope.capability(
        event_id=event_id,
        repository="repo/cap",
        commit="0123456789abcdef0123456789abcdef01234567",
        authority_snapshot=authority,
        verifier_id="v",
        source_evidence=evidence,
        capability={
            "capability_id":event_id,
            "input_type":"X",
            "output_type":"Y",
            "semantics":[["x","y"]],
            "guard_inputs":["x"],
            "certificate_id":"cert",
            "dependencies":[],
            "authority_snapshot":authority,
            "verifier_id":"v",
            "provenance_ids":["p"],
            "cost":0,
        },
        oracle=[["x","y"]],
        origin="repo/cap",
    )


def obs(event_id, evidence=b"obs", authority="oa"):
    return ExternalEventEnvelope.obstruction(
        event_id=event_id,
        repository="repo/obs",
        commit="0123456789abcdef0123456789abcdef01234567",
        authority_snapshot=authority,
        verifier_id="v",
        source_evidence=evidence,
        obstruction={
            "obstruction_id":event_id,
            "input_type":"OX",
            "output_type":"OY",
            "contract":{"authority_snapshot":authority,"verifier_id":"v"},
            "candidate_fingerprint":event_id+":bad",
            "separating_input":"x",
            "expected_output":"yes",
            "actual_output":"no",
            "provenance":"p",
        },
    )


class FlashLiveRouterTests(unittest.TestCase):
    def test_first_cycle_admits_new_events_and_second_cycle_is_stable(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            bundles=[
                write_bundle(root,"cap",cap("cap-1"),b"cap"),
                write_bundle(root,"obs",obs("obs-1"),b"obs"),
            ]
            first=update_live_state(None,bundles)
            self.assertEqual(first["new_event_ids"],["cap-1","obs-1"])
            self.assertEqual(first["summary"]["external_events"],2)
            self.assertEqual(first["summary"]["active_capabilities"],1)
            self.assertEqual(first["summary"]["obstructions"],1)

            second=update_live_state(first["state_bundle_text"],bundles)
            self.assertEqual(second["new_event_ids"],[])
            self.assertEqual(second["unchanged_event_ids"],["cap-1","obs-1"])
            self.assertEqual(second["state_bundle_text"],first["state_bundle_text"])
            self.assertEqual(second["summary"]["event_count"],2)

    def test_absent_current_producer_does_not_erase_verified_past(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            b1=write_bundle(root,"cap",cap("cap-1"),b"cap")
            first=update_live_state(None,[b1])
            second=update_live_state(first["state_bundle_text"],[])
            self.assertEqual(second["summary"]["active_capability_ids"],["cap-1"])
            self.assertEqual(second["new_event_ids"],[])
            self.assertEqual(second["retained_past_event_ids"],["cap-1"])

    def test_same_identity_with_changed_payload_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            b1=write_bundle(root,"cap1",cap("cap-1",b"cap","a"),b"cap")
            first=update_live_state(None,[b1])
            b2=write_bundle(root,"cap2",cap("cap-1",b"cap2","different-authority"),b"cap2")
            with self.assertRaisesRegex(ValueError,"event identity conflict"):
                update_live_state(first["state_bundle_text"],[b2])

    def test_new_revocation_event_withdraws_previous_capability(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            admission=write_bundle(root,"cap",cap("cap-1"),b"cap")
            first=update_live_state(None,[admission])

            evidence=b"rev"
            revoke=ExternalEventEnvelope.capability_revocation(
                event_id="revoke-cap-1",
                repository="repo/cap",
                commit="fedcba9876543210fedcba9876543210fedcba98",
                authority_snapshot="a2",
                verifier_id="v2",
                source_evidence=evidence,
                capability_id="cap-1",
                reason="superseded",
            )
            rb=write_bundle(root,"revoke",revoke,evidence)
            second=update_live_state(first["state_bundle_text"],[rb])
            self.assertEqual(second["new_event_ids"],["revoke-cap-1"])
            self.assertEqual(second["summary"]["active_capabilities"],0)
            self.assertEqual(second["summary"]["open_obligation_ids"],["external:cap-1"])
            self.assertIn("cap-1",second["summary"]["revoked_capability_ids"])


if __name__=="__main__":
    unittest.main()
