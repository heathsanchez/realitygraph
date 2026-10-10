"""Independent warrant consumer: exact source replay and adversarial controls."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import unittest

from research.mathgraph_warrant_consumer_v1 import (
    PRODUCER_SHA256, JPL_CLAIM, InvalidWarrant, canonical,
    read_strict_json, _typed_routes, independently_close, reclose_from_bytes,
)


class IndependentConsumerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.snapshot = Path(os.environ["MATHGRAPH_WARRANT_SNAPSHOT"]).read_bytes()
            cls.history = Path(os.environ["MATHGRAPH_OPENAI_HISTORY"]).read_bytes()
        except KeyError as err:
            raise RuntimeError("Exact pinned source fixtures required") from err

    def test_exact_record_is_independently_accepted(self):
        result = reclose_from_bytes(self.snapshot, self.history)
        self.assertEqual(result["status"], "WARRANTED_BOUNDED_CONSUMER_REPLAY")
        self.assertEqual(result["checked_claims"], 7)
        self.assertEqual(result["stale_documentary_paths"], 3)
        self.assertEqual(result["unknown_mathematical_truths"], 3)
        self.assertEqual(result["unaffected_formal_controls"], 1)
        self.assertEqual(result["independent_states"][JPL_CLAIM]["after"], "WARRANTED_BOUNDED")
        self.assertEqual(hashlib.sha256(self.snapshot).hexdigest(), PRODUCER_SHA256)

    def test_unknown_is_not_refuted_by_publisher_notice(self):
        result = reclose_from_bytes(self.snapshot, self.history)
        states = result["independent_states"]
        self.assertTrue(all(states["openai.theorem.%d" % i]["after"] == "UNKNOWN"
                            for i in range(1, 4)))
        self.assertNotIn("REFUTED", json.dumps(result))

    def test_independent_unrelated_warrant_survives_retraction(self):
        graph = read_strict_json(self.snapshot)["derivation"]
        claims = {x["id"]: x for x in graph["claims"]}
        routes = graph["routes"]
        before = independently_close(claims, routes, frozenset())
        after = independently_close(claims, routes, frozenset(graph["withdrawn_evidence"]))
        self.assertEqual(before[JPL_CLAIM], after[JPL_CLAIM])
        self.assertEqual(after[JPL_CLAIM], "WARRANTED_BOUNDED")

    def test_content_tamper_fails_even_if_self_hash_recomputed(self):
        data = read_strict_json(self.snapshot)
        data["resolutions"]["openai.theorem.1"]["after"] = "WARRANTED_BOUNDED"
        copy_ = {k: v for k, v in data.items() if k != "snapshot_sha256"}
        data["snapshot_sha256"] = hashlib.sha256(canonical(copy_)).hexdigest()
        tampered = canonical(data) + b"\n"
        self.assertNotEqual(hashlib.sha256(tampered).hexdigest(), PRODUCER_SHA256)
        with self.assertRaisesRegex(InvalidWarrant, "UNTRUSTED_PUBLICATION_BYTES"):
            reclose_from_bytes(tampered, self.history)

    def test_fake_external_root_fails_before_any_replay(self):
        data = read_strict_json(self.snapshot)
        data["derivation"]["receipts"].append({
            "id": "self_signed_unknown", "kind": "formal", "scope": "openai/math:FAKE"
        })
        with self.assertRaisesRegex(InvalidWarrant, "UNTRUSTED_PUBLICATION_BYTES"):
            reclose_from_bytes(canonical(data) + b"\n", self.history)

    def test_mutated_openai_history_fails_source_pin(self):
        with self.assertRaisesRegex(InvalidWarrant, "OPENAI_SOURCE_SHA256_MISMATCH"):
            reclose_from_bytes(self.snapshot, self.history + b"\n# forged edit\n")

    def test_noncanonical_payload_rejected(self):
        with self.assertRaisesRegex(InvalidWarrant, "NONCANONICAL_RECORD"):
            read_strict_json(self.snapshot + b" ")
        with self.assertRaises(InvalidWarrant):
            read_strict_json(b'{"a":1,"a":2}\n')
        with self.assertRaisesRegex(InvalidWarrant, "NONCANONICAL_RECORD"):
            read_strict_json(b'{"a": 1}\n')

    def test_unproved_scope_bridge_must_fail(self):
        claims = {
            "source": {"id":"source","kind":"formal","scope":"one"},
            "target": {"id":"target","kind":"formal","scope":"two"},
        }
        evidence = {
            "rs": {"id":"rs","kind":"formal","scope":"one"},
            "rt": {"id":"rt","kind":"formal","scope":"two"},
        }
        with self.assertRaisesRegex(InvalidWarrant, "UNPROVED_PREMISE_TRANSPORT"):
            _typed_routes({"routes":[
                {"conclusion":"source","evidence":["rs"],"premises":[]},
                {"conclusion":"target","evidence":["rt"],"premises":["source"]},
            ]}, claims, evidence)

    def test_finitely_many_cycles_cannot_bootstrap_warrant(self):
        claims = {x:{"id":x,"kind":"formal","scope":"s"} for x in ("a","b","control")}
        routes = [
            {"conclusion":"a","evidence":["r1"],"premises":["b"]},
            {"conclusion":"b","evidence":["r2"],"premises":["a"]},
            {"conclusion":"control","evidence":["r3"],"premises":[]},
        ]
        states = independently_close(claims, routes, frozenset())
        self.assertEqual(states["a"], "UNKNOWN")
        self.assertEqual(states["b"], "UNKNOWN")
        self.assertEqual(states["control"], "WARRANTED_BOUNDED")

    def test_alternative_independent_route_preserves_supported_claim(self):
        claims = {"a": {"id":"a","kind":"formal","scope":"s"}}
        routes = [
            {"conclusion":"a","evidence":["r1"],"premises":[]},
            {"conclusion":"a","evidence":["r2"],"premises":[]},
        ]
        self.assertEqual(independently_close(claims, routes, frozenset({"r1"}))["a"],
                         "WARRANTED_BOUNDED")
        self.assertEqual(independently_close(claims, routes,
                                             frozenset({"r1","r2"}))["a"],
                         "UNKNOWN")

    def test_typed_route_with_missing_evidence_rejected(self):
        with self.assertRaisesRegex(InvalidWarrant, "UNKNOWN_ROUTE_PREMISE_OR_EVIDENCE"):
            _typed_routes(
                {"routes":[{"conclusion":"a","evidence":["invented"],"premises":[]}]},
                {"a":{"id":"a","kind":"formal","scope":"s"}}, {})


if __name__ == "__main__":
    unittest.main()
