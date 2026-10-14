#!/usr/bin/env python3
"""Source file currentness is separate from historical proof and live warrant."""
import copy
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from current_source import inspect_observation
from consumer import Refused

OLD_COMMIT = "56a005855ea17e0b0958f73ec801ae140b0a1679"
NEW_COMMIT = "d20f010dc809f2bb8f94969ccc8ed1691bad2531"


class CurrentSourceTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads((HERE / "policy.json").read_text())
        self.ids = [rec["id"] for rec in self.policy["receipts"]]
        self.historical = {
            "accepted_history": True,
            "source_commit": OLD_COMMIT,
            "claims": {
                rid: {"recipient_support": "WARRANTED_BOUNDED_HISTORICAL"}
                for rid in self.ids
            },
        }
        self.obs = {
            item["id"]: {
                "status": "present", "commit": NEW_COMMIT,
                "path": item["file"], "blob_sha": item["git_blob"],
            }
            for item in self.policy["receipts"]
        }

    def evaluate(self, obs=None, **overrides):
        inputs = {
            "observed_commit": NEW_COMMIT,
            "observations": self.obs if obs is None else obs,
            "repo_default_branch": "master",
            "branch_name": "master",
            "observation_channel": "github-repository-https-api-at-sha",
        }
        inputs.update(overrides)
        return inspect_observation(self.historical, self.policy, **inputs)

    def assert_refused(self, reason, **kwargs):
        with self.assertRaises(Refused) as caught:
            self.evaluate(**kwargs)
        self.assertEqual(caught.exception.reason, reason)

    def test_head_moves_but_source_file_unchanged_no_current_proof_promotion(self):
        result = self.evaluate()
        self.assertNotEqual(OLD_COMMIT, NEW_COMMIT)
        self.assertTrue(result["historical_admission"])
        self.assertEqual(result["dependency_closure"], "NOT_REPLAYED_AT_CURRENT_HEAD")
        self.assertEqual(result["publisher_withdrawal"], "NOT_CHECKED")
        self.assertEqual(result["publisher_signature_authority"], "NOT_ESTABLISHED")
        for rec in result["observed_source_files"].values():
            self.assertEqual(rec["current_file_observation"],
                             "SOURCE_FILE_UNCHANGED_AT_OBSERVED_HEAD")
            self.assertEqual(rec["current_proof_warrant"],
                             "UNKNOWN_DEPENDENCY_CLOSURE_NOT_RECHECKED")
            self.assertEqual(rec["historical_support"],
                             "WARRANTED_BOUNDED_HISTORICAL")

    def test_one_file_changed_only_that_file_requires_requalification(self):
        obs = copy.deepcopy(self.obs)
        key = self.ids[0]
        obs[key]["blob_sha"] = "f" * 40
        result = self.evaluate(obs)["observed_source_files"]
        self.assertEqual(result[key]["current_file_observation"],
                         "SOURCE_FILE_CHANGED_REQUALIFICATION_REQUIRED")
        self.assertEqual(result[self.ids[1]]["current_file_observation"],
                         "SOURCE_FILE_UNCHANGED_AT_OBSERVED_HEAD")
        self.assertEqual(result[key]["historical_support"],
                         "WARRANTED_BOUNDED_HISTORICAL")

    def test_missing_file_does_not_mean_publisher_withdrawal_or_false_theorem(self):
        obs = copy.deepcopy(self.obs)
        obs[self.ids[1]].update(status="missing", blob_sha=None)
        result = self.evaluate(obs)
        self.assertEqual(
            result["observed_source_files"][self.ids[1]]["current_file_observation"],
            "SOURCE_PATH_MISSING_REQUALIFICATION_REQUIRED")
        self.assertEqual(result["publisher_withdrawal"], "NOT_CHECKED")
        self.assertEqual(result["observed_source_files"][self.ids[0]]["current_file_observation"],
                         "SOURCE_FILE_UNCHANGED_AT_OBSERVED_HEAD")

    def test_reject_altered_source_file_path(self):
        obs = copy.deepcopy(self.obs)
        obs[self.ids[0]]["path"] = "Mathlib/Other.lean"
        self.assert_refused("CURRENT_OBSERVATION_SCOPE_MISMATCH", obs=obs)

    def test_reject_altered_commit_scope_on_one_source(self):
        obs = copy.deepcopy(self.obs)
        obs[self.ids[0]]["commit"] = OLD_COMMIT
        self.assert_refused("CURRENT_OBSERVATION_SCOPE_MISMATCH", obs=obs)

    def test_untrusted_source_assertion_field_cannot_promote_warrant(self):
        obs = copy.deepcopy(self.obs)
        obs[self.ids[0]]["verified_current"] = True
        self.assert_refused("UNSUPPORTED_SOURCE_OBSERVATION", obs=obs)

    def test_no_unauthorized_branch_or_communication_channel(self):
        self.assert_refused("UPSTREAM_BRANCH_NOT_AUTHORIZED",
                            repo_default_branch="not-the-original-issuer")
        self.assert_refused("UPSTREAM_BRANCH_NOT_AUTHORIZED",
                            branch_name="untrusted-fork")
        self.assert_refused("UNAUTHORIZED_OBSERVATION_CHANNEL",
                            observation_channel="publisher-claimed-success")

    def test_refuse_missing_or_untrusted_historical_warrant(self):
        self.historical["accepted_history"] = False
        self.assert_refused("HISTORIC_ADMISSION_REQUIRED")
        self.historical["accepted_history"] = True
        self.historical["claims"][self.ids[0]]["recipient_support"] = "UNKNOWN"
        self.assert_refused("HISTORIC_SUPPORT_NOT_WARRANTED")

    def test_refuse_non_sha_observation_or_missing_inputs(self):
        self.assert_refused("INVALID_OBSERVED_HEAD", observed_commit="main")
        obs = copy.deepcopy(self.obs)
        del obs[self.ids[0]]
        self.assert_refused("SOURCE_RECEIPT_SET_CHANGED", obs=obs)
        obs = copy.deepcopy(self.obs)
        obs[self.ids[0]]["blob_sha"] = "publisher says safe"
        self.assert_refused("INVALID_CURRENT_SOURCE_BLOB", obs=obs)

    def test_invalid_missing_claim_cannot_have_blob(self):
        obs = copy.deepcopy(self.obs)
        obs[self.ids[0]]["status"] = "missing"
        self.assert_refused("MISSING_FILE_HAS_BLOB", obs=obs)


if __name__ == "__main__":
    unittest.main()
