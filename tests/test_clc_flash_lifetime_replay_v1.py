"""Original FLASH events replay through the genuine Lean admission gate."""
import unittest
from dataclasses import replace
from realitygraph.clc_lean import LeanCLCChecker, canonical_transport
from realitygraph.flash import CapabilityAdmissionEvent, CapabilityRevocationEvent
from realitygraph.clc_replay import authenticated_replay, event_log_digest
from test_clc_lean_admission_v3 import capability, admission, flash

class FlashLifetimeReplayTests(unittest.TestCase):
    def test_replay_revocation_alternative_and_tamper(self):
        checker=LeanCLCChecker()
        source,_=flash(checker)
        obligations=tuple(source.obligations.values())
        rules=source.composition_rules
        events=(
            admission("add-f","f",claim=canonical_transport(capability("f"))),
            admission("add-g","g",claim=canonical_transport(capability("g"))),
        )
        original,runtime=authenticated_replay(obligations,rules,events,checker,
                                                expected_log_digest=event_log_digest(events))
        self.assertEqual(original.discharged_obligation_ids(),("p-0","p-1"))
        self.assertIn("h",original.active_capability_ids())
        # Rebuild using a new checker and the exact same original frozen events.
        replayed,_=authenticated_replay(obligations,rules,events,LeanCLCChecker(),
                                         expected_log_digest=event_log_digest(events))
        self.assertEqual(replayed.discharged_obligation_ids(),("p-0","p-1"))
        revoked=events+(CapabilityRevocationEvent("rev-f","f","ablation"),)
        after,_=authenticated_replay(obligations,rules,revoked,LeanCLCChecker(),
                                      expected_log_digest=event_log_digest(revoked))
        self.assertEqual(after.open_obligation_ids(),("p-0","p-1"))
        self.assertNotIn("h",after.active_capability_ids())
        alternative=revoked+(
          admission("alt","alt",claim=canonical_transport(capability("alt"))),)
        restored,_=authenticated_replay(obligations,rules,alternative,LeanCLCChecker(),
                                         expected_log_digest=event_log_digest(alternative))
        self.assertEqual(restored.discharged_obligation_ids(),("p-0","p-1"))
        self.assertEqual(restored.obligations["p-0"].solved_by,"alt")
        with self.assertRaisesRegex(ValueError,"identity mismatch"):
            authenticated_replay(obligations,rules,revoked,LeanCLCChecker(),
                                 expected_log_digest=event_log_digest(events))
        altered=(replace(events[0],capability=replace(capability("f"),
                                            authority_snapshot="foreign")),events[1])
        with self.assertRaises(ValueError):
            authenticated_replay(obligations,rules,altered,LeanCLCChecker(),
                                 expected_log_digest=event_log_digest(events))
        # Even a digest computed over forged contents is not a Lean warrant.
        with self.assertRaises(ValueError):
            authenticated_replay(obligations,rules,altered,LeanCLCChecker(),
                                 expected_log_digest=event_log_digest(altered))
        without_claim=(replace(events[0],transport_claim=None),events[1])
        with self.assertRaisesRegex(ValueError,"missing persistent"):
            event_log_digest(without_claim)

if __name__=="__main__":
    unittest.main()
