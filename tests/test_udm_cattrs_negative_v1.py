"""Never admit source-mismatched native observation after authentic cattrs failure."""
import json
import unittest
from pathlib import Path
from realitygraph.udm_native_bridge import attrs_observation_capability
from realitygraph.flash import FlashClosure, FlashContract, LiveObligation
from realitygraph.clc_lean import LeanCLCChecker

ROOT=Path(__file__).resolve().parents[1]
NEGATIVE=ROOT/"research/udm_applicability_v1/QUALIFIED_NEGATIVE.json"

class ProspectiveNegativeTests(unittest.TestCase):
    def test_qualified_failure_does_not_imply_applicability(self):
        r=json.loads(NEGATIVE.read_text())
        self.assertEqual(r["source"],"python-attrs/cattrs")
        self.assertEqual(r["status"],"REJECTED_PROSPECTIVE_APPLICABILITY_SHAPE")
        self.assertEqual(r["native_counts"]["errors"],0)
        self.assertGreater(r["native_counts"]["failures"],0)
        self.assertEqual(r["direct_boolean_parametrized_candidates"],[])
        self.assertEqual(r["G2"],"UNKNOWN")
        # The actual bridge must refuse this external native evidence, not
        # synthesize a source-neutral claim merely because pytest failed.
        with self.assertRaises(ValueError):
            attrs_observation_capability(r)
        o=LiveObligation("cattrs-native","CattrsTest","CattrsTest","BooleanObservationV1",
            (("native:0","true"),("native:1","false")),
            (("native:0","native:0"),("native:1","native:1")),
            FlashContract("cattrs:"+r["base"],"native-pytest"))
        flash=FlashClosure((o,),kernel="clc-lean-v3",clc_checker=LeanCLCChecker())
        self.assertEqual(flash.open_obligation_ids(),("cattrs-native",))
        self.assertEqual(flash.active_capability_ids(),())
        self.assertEqual(flash.event_count,0)

if __name__=="__main__":unittest.main()
