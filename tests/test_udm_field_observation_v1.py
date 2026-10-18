import json
import unittest
from pathlib import Path
from realitygraph.udm_field_observer import describe

RESULT=Path(__file__).resolve().parents[1]/"research/udm_field_observation_v1/TRAINING_RESULT.json"

class ObservationTests(unittest.TestCase):
    def test_distinguishes_unexpected_fields(self):
        self.assertEqual(describe({"kind":"parent","renamed":0},{"kind":"parent"}),
                         {"left_only":["renamed"],"right_only":[],"unequal":[],
                          "left_values":{"renamed":0},"right_values":{}})
    def test_preserves_negative_scientific_boundary(self):
        d=json.loads(RESULT.read_text())
        self.assertEqual(d["native_counts"],{"tests":2,"failures":2,"errors":0,"skipped":0})
        self.assertEqual(len(d["mapping_failure_observations"]),2)
        self.assertTrue(all(x["left_only"]==["renamed"] for x in d["mapping_failure_observations"]))
        self.assertEqual(d["status"],"CANDIDATE_FIELD_OBSERVATION_NO_REPAIR_WARRANT")
        self.assertEqual(d["heldout_future"],"NOT_SELECTED_NOT_OPENED")
        self.assertEqual(d["G2"],"UNKNOWN")
if __name__=="__main__":unittest.main()
