from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from realitygraph.collatz_macro_controller import (
    MACRO_CAPABILITY_ID,
    active_macro_rows,
    canonical,
    promote_candidate,
)


def row_for_word(word):
    A=1;B=0;D=0
    for r,s,rp in word:
        A,B,D=3**r*A,3**r*B+((1<<s)-1)*(1<<D),D+s+rp
    body={
        "r0":word[0][0],
        "r1":word[-1][2],
        "A":A,"B":B,"D":D,
        "steps":sum(r+s for r,s,rp in word),
        "word":[list(t) for t in word],
    }
    mid="macro-"+hashlib.sha256(canonical(body).encode()).hexdigest()[:20]
    return {"macro_id":mid,**body}


class CollatzMacroControllerTests(unittest.TestCase):
    def _candidate(self, word=((1,1,1),)):
        row=row_for_word(word)
        payload={
            "version":"collatz-forward-macro-candidate-v1",
            "train_range":[3,31],
            "training_sources":1,
            "maxlen":1,
            "macro_count":1,
            "anchors":1,
            "macros":[row],
        }
        payload["evidence_digest"]=hashlib.sha256(canonical(payload).encode()).hexdigest()
        path=Path(tempfile.mkdtemp())/(row["macro_id"]+".json")
        path.write_text(canonical(payload)+"\n")
        return str(path),row

    def test_candidate_promotes_restarts_and_ablates(self):
        path,row=self._candidate()
        ledger,present,_event,rows=promote_candidate(path)
        self.assertIn(MACRO_CAPABILITY_ID,present.capability_graph.active_ids())
        self.assertEqual(rows,(row,))
        self.assertEqual(active_macro_rows(present),(row,))

        ablated=type(ledger)(ledger.events.values())
        ablated.append_revoke_capability(
            MACRO_CAPABILITY_ID,
            "qckn-v1-collatz-adapter",
            reason="test",
            parents=ledger.heads,
        )
        restarted=ablated.materialize_compiled_present().restart()
        self.assertEqual(active_macro_rows(restarted),())

    def test_distinct_generations_union_and_targeted_ablation_restores_ancestor(self):
        p1,r1=self._candidate(((1,1,1),))
        p2,r2=self._candidate(((1,1,2),))

        ledger,present1,_e1,_=promote_candidate(p1)
        self.assertEqual(active_macro_rows(present1),(r1,))

        gen2_id="collatz-forward-descent-macro-bank-test-gen2"
        ledger,present2,_e2,_=promote_candidate(
            p2,
            ledger=ledger,
            capability_id=gen2_id,
            provenance_ids=("test-gen2",),
        )
        self.assertEqual(
            {row["macro_id"] for row in active_macro_rows(present2)},
            {r1["macro_id"],r2["macro_id"]},
        )

        # Revoking only generation 2 reconstructs generation 1 exactly at the
        # active macro identity level.
        ablated=type(ledger)(ledger.events.values())
        ablated.append_revoke_capability(
            gen2_id,
            "qckn-v1-collatz-adapter",
            reason="generation-test",
            parents=ledger.heads,
        )
        restarted=ablated.materialize_compiled_present().restart()
        self.assertEqual(active_macro_rows(restarted),(r1,))

    def test_tampered_macro_is_rejected(self):
        path,row=self._candidate()
        payload=json.loads(Path(path).read_text())
        payload["macros"][0]["A"]+=1
        # Recompute outer digest so only algebra verifier can catch it.
        payload.pop("evidence_digest")
        payload["evidence_digest"]=hashlib.sha256(canonical(payload).encode()).hexdigest()
        Path(path).write_text(canonical(payload)+"\n")
        with self.assertRaisesRegex(ValueError,"macro mismatch"):
            promote_candidate(path)


if __name__=="__main__":
    unittest.main()
