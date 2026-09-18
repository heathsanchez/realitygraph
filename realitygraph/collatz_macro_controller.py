from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .capability import FiniteCapability
from .collatz_controller import generation2_ledger
from .ledger import Ledger


MACRO_CAPABILITY_ID="collatz-forward-descent-macro-bank-v1"
MACRO_AUTHORITY="collatz-forward-descent-exact-v1"
MACRO_VERIFIER="collatz-affine-macro-algebra-v1"
KERNEL="qckn-v1-collatz-adapter"


def canonical(obj)->str:
    return json.dumps(obj,sort_keys=True,separators=(",",":"))


def digest_rows(rows)->str:
    return hashlib.sha256(canonical(rows).encode()).hexdigest()


def verify_macro_row(row:dict)->dict:
    word=tuple(tuple(int(v) for v in t) for t in row["word"])
    if not word:
        raise ValueError("macro word empty")
    if any(len(t)!=3 or any(v<1 for v in t) for t in word):
        raise ValueError("invalid macro episode")
    if any(a[2]!=b[0] for a,b in zip(word,word[1:])):
        raise ValueError("macro episode anchors do not compose")

    A=1;B=0;D=0
    for r,s,rp in word:
        A,B,D=3**r*A,3**r*B+((1<<s)-1)*(1<<D),D+s+rp
    expected={
        "r0":word[0][0],
        "r1":word[-1][2],
        "A":A,"B":B,"D":D,
        "steps":sum(r+s for r,s,rp in word),
    }
    for k,v in expected.items():
        if int(row[k])!=int(v):
            raise ValueError(f"macro mismatch {row.get('macro_id')} {k}")

    body={**expected,"word":[list(t) for t in word]}
    mid="macro-"+hashlib.sha256(canonical(body).encode()).hexdigest()[:20]
    if str(row["macro_id"])!=mid:
        raise ValueError("macro identity mismatch")
    return {"macro_id":mid,**body}


def load_candidate(path:str):
    payload=json.loads(Path(path).read_text())
    if payload.get("version")!="collatz-forward-macro-candidate-v1":
        raise ValueError("unsupported macro candidate version")

    claimed=payload.get("evidence_digest")
    check=dict(payload)
    check.pop("evidence_digest",None)
    actual=hashlib.sha256(canonical(check).encode()).hexdigest()
    if actual!=claimed:
        raise ValueError("macro candidate evidence digest mismatch")

    rows=[verify_macro_row(r) for r in payload.get("macros",())]
    if len(rows)!=int(payload["macro_count"]):
        raise ValueError("macro count mismatch")
    if len({r["macro_id"] for r in rows})!=len(rows):
        raise ValueError("duplicate macro identities")
    return payload,tuple(sorted(rows,key=lambda r:r["macro_id"]))


def macro_capability(rows, candidate_digest:str, *, capability_id:str=MACRO_CAPABILITY_ID, provenance_ids:tuple[str,...]|None=None)->FiniteCapability:
    semantics=tuple(
        (r["macro_id"],canonical(r))
        for r in rows
    )
    return FiniteCapability(
        capability_id=capability_id,
        input_type="CollatzMacroID",
        output_type="ForwardDescentMacroCertificate",
        semantics=semantics,
        guard_inputs=tuple(mid for mid,_ in semantics),
        certificate_id="macro-bank-"+candidate_digest[:24],
        dependencies=(),
        authority_snapshot=MACRO_AUTHORITY,
        verifier_id=MACRO_VERIFIER,
        provenance_ids=provenance_ids or (
            "test-run-35327397877",
            "test-commit-91742a2d544e9a4e46d2b936560000b8ae6f5643",
        ),
        cost=len(rows),
    )


def promote_candidate(
    path:str,
    *,
    ledger:Ledger|None=None,
    capability_id:str=MACRO_CAPABILITY_ID,
    provenance_ids:tuple[str,...]|None=None,
):
    payload,rows=load_candidate(path)
    if ledger is None:
        ledger,_=generation2_ledger()
    cap=macro_capability(
        rows,
        str(payload["evidence_digest"]),
        capability_id=capability_id,
        provenance_ids=provenance_ids,
    )
    event=ledger.append_promote_capability(cap,KERNEL,parents=ledger.heads)
    present=ledger.materialize_compiled_present().restart()
    if capability_id not in present.capability_graph.active_ids():
        raise AssertionError("macro capability did not survive compile/restart")
    return ledger,present,event.id,rows


def active_macro_rows(present):
    active=set(present.capability_graph.active_ids())
    rows={}
    for cap in present.capability_graph.capabilities:
        if cap.capability_id not in active:
            continue
        if (
            cap.input_type!="CollatzMacroID"
            or cap.output_type!="ForwardDescentMacroCertificate"
        ):
            continue
        for mid,text in cap.semantics:
            row=json.loads(text)
            if row["macro_id"]!=mid:
                raise ValueError("active macro identity mismatch")
            verified=verify_macro_row(row)
            prior=rows.get(mid)
            if prior is not None and prior!=verified:
                raise ValueError(f"active macro identity conflict: {mid}")
            rows[mid]=verified
    return tuple(rows[mid] for mid in sorted(rows))


def bank_payload(present):
    rows=active_macro_rows(present)
    return {
        "version":"collatz-forward-macro-bank-v1",
        "compiled_present_digest":present.digest,
        "macro_count":len(rows),
        "bank_digest":digest_rows(rows),
        "macros":list(rows),
    }


def empty_bank_payload():
    rows=()
    return {
        "version":"collatz-forward-macro-bank-v1",
        "compiled_present_digest":"",
        "macro_count":0,
        "bank_digest":digest_rows(rows),
        "macros":[],
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--candidate-json")
    ap.add_argument("--export-bank")
    ap.add_argument("--export-ablated-bank")
    ap.add_argument("--report-json")
    a=ap.parse_args()
    if not a.candidate_json:
        raise SystemExit("--candidate-json required")

    ledger,present,event_id,rows=promote_candidate(a.candidate_json)
    bank=bank_payload(present)
    if a.export_bank:
        Path(a.export_bank).write_text(canonical(bank)+"\n")

    ablated=Ledger(ledger.events.values())
    ablated.append_revoke_capability(
        MACRO_CAPABILITY_ID,KERNEL,
        reason="macro-bank causal ablation",
        parents=ledger.heads,
    )
    ablated_present=ablated.materialize_compiled_present().restart()
    ablated_bank=bank_payload(ablated_present)
    if ablated_bank["macro_count"]!=0:
        raise AssertionError("macro ablation did not restore empty bank")
    if a.export_ablated_bank:
        Path(a.export_ablated_bank).write_text(canonical(ablated_bank)+"\n")

    report={
        "version":"collatz-qckn-macro-promotion-v1",
        "macro_count":len(rows),
        "bank_digest":bank["bank_digest"],
        "compiled_present_digest":present.digest,
        "promotion_event":event_id,
        "ablation_macro_count":ablated_bank["macro_count"],
        "ablation_restores_cold":True,
    }
    if a.report_json:
        Path(a.report_json).write_text(canonical(report)+"\n")
    print("PROMOTED_MACROS",len(rows))
    print("MACRO_BANK_DIGEST",bank["bank_digest"])
    print("COMPILED_PRESENT_DIGEST",present.digest)
    print("ABLATION_MACROS",ablated_bank["macro_count"])
    print("PASS_QCKN_MACRO_PROMOTION")


if __name__=="__main__":
    main()
