"""Cold restart must recheck the original finite Lean claim."""
import json
import unittest
from dataclasses import asdict, replace
from realitygraph.capability import FiniteCapability
from realitygraph.clc_lean import LeanCLCChecker, canonical_transport, sha

def fixture():
    cap = FiniteCapability("f", "X", "Y", (("x0","y0"),("x1","y1")),
        ("x0","x1"), "source:f", (), "audit-omega-1", "audit-v1",
        ("external-source-f",), 2)
    return cap, canonical_transport(cap)

def reauthenticate(checker, cap, claim, saved, expected):
    payload = {"capability":asdict(cap), "claim":claim.payload()}
    if sha(payload) != expected or saved != expected:
        raise ValueError("persistent identity conflict")
    return checker.check_transport(cap, cap.semantics, claim)

class LifetimeTests(unittest.TestCase):
    def test_restart_and_falsifiers(self):
        cap, claim = fixture()
        payload = {"capability":asdict(cap), "claim":claim.payload()}
        identity = sha(payload)
        first = LeanCLCChecker().check_transport(cap,cap.semantics,claim)
        new_process_checker = LeanCLCChecker()
        second = reauthenticate(new_process_checker,cap,claim,identity,identity)
        self.assertEqual(first, second)
        self.assertEqual(len(new_process_checker._cache), 1)
        with self.assertRaises(ValueError):
            reauthenticate(LeanCLCChecker(),cap,claim,"altered",identity)
        with self.assertRaises(ValueError):
            reauthenticate(LeanCLCChecker(),replace(cap,authority_snapshot="foreign"),
                           claim,identity,identity)
        with self.assertRaises(ValueError):
            reauthenticate(LeanCLCChecker(),cap,replace(claim,strict=False),
                           identity,identity)

if __name__ == "__main__":
    unittest.main()
