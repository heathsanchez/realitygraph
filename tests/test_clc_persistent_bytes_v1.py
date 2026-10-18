"""Real JSON byte boundary; the restored object graph starts empty."""
import hashlib
import json
import unittest
from dataclasses import replace
from realitygraph.clc_lean import LeanCLCChecker, canonical_transport
from realitygraph.clc_replay import persistent_event_bytes, replay_persistent_bytes
from test_clc_lean_admission_v3 import capability, admission, flash
from realitygraph.flash import CapabilityRevocationEvent

class PersistentFlashReplayTests(unittest.TestCase):
    def test_authentic_restore_revoke_restore_and_tamper(self):
        base,_=flash(LeanCLCChecker())
        obligations=tuple(base.obligations.values())
        rules=base.composition_rules
        events=(
            admission("add-f","f",claim=canonical_transport(capability("f"))),
            admission("add-g","g",claim=canonical_transport(capability("g"))),
        )
        def restore(log):
            raw=persistent_event_bytes(log)
            digest=hashlib.sha256(raw).hexdigest()
            closure,_=replay_persistent_bytes(raw,expected_sha256=digest,
                  obligations=obligations,rules=rules,checker=LeanCLCChecker())
            return closure,raw,digest
        closure,raw,digest=restore(events)
        self.assertEqual(closure.discharged_obligation_ids(),("p-0","p-1"))
        self.assertIn("h",closure.active_capability_ids())
        revoked=events+(CapabilityRevocationEvent("revoke-f","f","cause removed"),)
        other,_,_=restore(revoked)
        self.assertNotIn("h",other.active_capability_ids())
        self.assertEqual(other.open_obligation_ids(),("p-0","p-1"))
        supported=revoked+(
            admission("alt","alt",claim=canonical_transport(capability("alt"))),)
        restored,_,_=restore(supported)
        self.assertEqual(restored.obligations["p-0"].solved_by,"alt")
        with self.assertRaisesRegex(ValueError,"digest mismatch"):
            replay_persistent_bytes(raw,expected_sha256="0"*64,
                 obligations=obligations,rules=rules,checker=LeanCLCChecker())
        changed=json.loads(raw)
        changed["events"][0]["capability"]["authority_snapshot"]="fake"
        mutated=json.dumps(changed,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()
        with self.assertRaises(ValueError):
            replay_persistent_bytes(mutated,
                expected_sha256=hashlib.sha256(mutated).hexdigest(),
                obligations=obligations,rules=rules,checker=LeanCLCChecker())
        noncanonical=json.dumps(json.loads(raw),indent=2).encode()
        with self.assertRaisesRegex(ValueError,"noncanonical"):
            replay_persistent_bytes(noncanonical,
                expected_sha256=hashlib.sha256(noncanonical).hexdigest(),
                obligations=obligations,rules=rules,checker=LeanCLCChecker())
if __name__=="__main__":
    unittest.main()
