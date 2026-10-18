"""Bounded attrs acquisition is admissible; tox transfer is not."""
import hashlib
import unittest
from copy import deepcopy
from realitygraph.clc_lean import LeanCLCChecker
from realitygraph.udm_native_bridge import (attrs_observation_capability,
    require_applicability,ATTRS_SOURCE)
from realitygraph.flash import (FlashClosure,FlashEventRuntime,FlashContract,
    LiveObligation,CapabilityAdmissionEvent,CapabilityRevocationEvent)
from realitygraph.clc_replay import persistent_event_bytes,replay_persistent_bytes

def result_fixture():
    return {
        "schema":"UDM_ATTRS_RESIDUAL_OBSERVATION_GENESIS_V1_RESULT",
        "status":"WARRANTED_BOUNDED_REAL_SOURCE_RESIDUAL_TO_OBSERVATION_TO_REPAIR",
        "source_base":ATTRS_SOURCE,
        "author_head":"2e082f1c1efb019885fbdb601b32f8464dbe5d47",
        "case_count":5,"failing_case_indices":[4],
        "candidate_observation_count":1,"causal_withdrawal":True,
        "restoration":True,"G2":"UNKNOWN","future_source":"UNOPENED",
        "observation_classes":[{
          "class_id":"obs-class:571b5338c5cfb47b05d4",
          "projection_vector":[False,False,False,False,True],
          "representative":"__forward_arg__"}],
        "selected_observation":{
          "class_id":"obs-class:571b5338c5cfb47b05d4",
          "selected_attribute":"__forward_arg__",
          "repair_sha256":"ebef4d0aebed93ec80e98ad1b50fcd79528d235f93fa3904e4bb79b9fdd1e03f"}
    }

class NativeBridgeTests(unittest.TestCase):
    def test_native_witness_lean_flash_persistence_and_source_guard(self):
        cap,claim=attrs_observation_capability(result_fixture())
        rows=cap.semantics
        obligation=LiveObligation("attrs-observation","AttrsObservedCaseV1",
            "AttrsObservedCaseV1","BooleanObservationV1",rows,
            tuple((k,k) for k,_ in rows),
            FlashContract(cap.authority_snapshot,cap.verifier_id))
        events=(CapabilityAdmissionEvent("acquire-attrs",cap,rows,
                                        transport_claim=claim),)
        raw=persistent_event_bytes(events)
        def restart(blob=raw,anchor=hashlib.sha256(raw).hexdigest()):
            closure,_=replay_persistent_bytes(blob,expected_sha256=anchor,
                obligations=(obligation,),rules=(),checker=LeanCLCChecker())
            return closure
        live=restart()
        self.assertEqual(live.discharged_obligation_ids(),("attrs-observation",))
        self.assertEqual(require_applicability(cap,source_authority=ATTRS_SOURCE,
                             case_id="case:4"),"true")
        with self.assertRaisesRegex(ValueError,"applicability"):
            require_applicability(cap,source_authority="tox-dev/tox#4168",case_id="case:4")
        with self.assertRaisesRegex(ValueError,"outside"):
            require_applicability(cap,source_authority=ATTRS_SOURCE,case_id="case:5")
        ablated=events+(CapabilityRevocationEvent("revoke-attrs",cap.capability_id,
                                                  "causal ablation"),)
        ablated_raw=persistent_event_bytes(ablated)
        withdrawn,_=replay_persistent_bytes(ablated_raw,
           expected_sha256=hashlib.sha256(ablated_raw).hexdigest(),
           obligations=(obligation,),rules=(),checker=LeanCLCChecker())
        self.assertEqual(withdrawn.open_obligation_ids(),("attrs-observation",))
        self.assertEqual(restart().discharged_obligation_ids(),("attrs-observation",))
        with self.assertRaisesRegex(ValueError,"digest mismatch"):
            restart(anchor="0"*64)
    def test_forged_native_witnesses_rejected(self):
        for path,value in [
          (("G2",),"WARRANTED_BOUNDED_PROSPECTIVE_G2"),
          (("source_base",),"tox-dev/tox"),
          (("candidate_observation_count",),2),
          (("observation_classes",0,"projection_vector"),[True]*5),
          (("selected_observation","repair_sha256"),"0"*64),
          (("future_source",),"OPENED")]:
            with self.subTest(path=path):
                d=deepcopy(result_fixture())
                current=d
                for p in path[:-1]:current=current[p]
                current[path[-1]]=value
                with self.assertRaises(ValueError):
                    attrs_observation_capability(d)

if __name__=="__main__":unittest.main()
