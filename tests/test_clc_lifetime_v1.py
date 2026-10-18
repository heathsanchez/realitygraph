"""Finite checkpoint identity and independent fresh-process Lean reauthentication."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from dataclasses import asdict, replace
from pathlib import Path
from realitygraph.capability import FiniteCapability
from realitygraph.clc_lean import LeanCLCChecker, canonical_transport, sha

def fixture():
    cap = FiniteCapability("f", "X", "Y", (("x0","y0"),("x1","y1")),
        ("x0","x1"), "source:f", (), "audit-omega-1", "audit-v1",
        ("external-source-f",), 2)
    return cap, canonical_transport(cap)

def checkpoint(cap, claim, receipt):
    payload = {"capability":asdict(cap), "claim":claim.payload(),
               "receipt":asdict(receipt)}
    return {"payload":payload, "digest":sha(payload)}

def validate_envelope(envelope, expected):
    if sha(envelope["payload"]) != envelope["digest"] or envelope["digest"] != expected:
        raise ValueError("persistent identity conflict")

class LifetimeTests(unittest.TestCase):
    def test_fresh_process_checkpoint_and_falsifiers(self):
        cap, claim = fixture()
        initial = LeanCLCChecker().check_transport(cap,cap.semantics,claim)
        saved = checkpoint(cap,claim,initial)
        expected = saved["digest"]
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "checkpoint.json"
            path.write_text(json.dumps(saved,sort_keys=True))
            code = """
import json,sys
from dataclasses import asdict
from realitygraph.capability import FiniteCapability
from realitygraph.clc_lean import LeanCLCChecker,canonical_transport,sha
envelope=json.load(open(sys.argv[1]))
p=envelope['payload']
assert sha(p)==envelope['digest']==sys.argv[2], 'CHECKPOINT_IDENTITY_REJECTED'
d=p['capability']
cap=FiniteCapability(d['capability_id'],d['input_type'],d['output_type'],
 tuple(map(tuple,d['semantics'])),tuple(d['guard_inputs']),
 d['certificate_id'],tuple(d['dependencies']),d['authority_snapshot'],
 d['verifier_id'],tuple(d['provenance_ids']),d['cost'])
claim=canonical_transport(cap)
assert claim.payload()==p['claim'], 'CLAIM_REJECTED'
receipt=LeanCLCChecker().check_transport(cap,cap.semantics,claim)
assert asdict(receipt)==p['receipt'], 'RECEIPT_REJECTED'
print('FRESH_PROCESS_LEAN_REAUTHENTICATED')
"""
            def run(identity=expected):
                return subprocess.run([sys.executable,"-c",code,str(path),identity],
                    capture_output=True,text=True,timeout=90)
            good=run()
            self.assertEqual(good.returncode,0,good.stdout+good.stderr)
            self.assertIn("FRESH_PROCESS_LEAN_REAUTHENTICATED",good.stdout)
            self.assertNotEqual(run("incorrect").returncode,0)
            for key,value in (("authority_snapshot","foreign"),
                              ("certificate_id","replaced-source")):
                mutant=json.loads(json.dumps(saved))
                mutant["payload"]["capability"][key]=value
                path.write_text(json.dumps(mutant))
                self.assertNotEqual(run().returncode,0,key)
            mutant=json.loads(json.dumps(saved))
            mutant["payload"]["receipt"]["stdout_sha256"]="0"*64
            path.write_text(json.dumps(mutant))
            self.assertNotEqual(run().returncode,0)
            path.write_text(json.dumps(saved))
            self.assertEqual(run().returncode,0)
if __name__=="__main__":
    unittest.main()
