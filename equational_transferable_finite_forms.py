from __future__ import annotations
import hashlib,json,re,urllib.request
from collections import Counter,defaultdict
from pathlib import Path
from equational_residual_demo import _Parser,_read_corpus
from equational_transition_demo import _archive_files
from equational_internal_lemma_bank import _specializes

COMMIT="bed33e36c33fca139d902addd8cb77cd4172fe64"
URL=f"https://codeload.github.com/YanbiaoLab/equational-challenges/tar.gz/{COMMIT}"
SHA="284b45196a9e8a31f1bd3aeb05040c451a615fed2ca8ba724d7a14a833e842eb"
RETAINED={"17195_to_43536","4922_to_4158","4922_to_4258","22268_to_22436","22505_to_40367"}

def dl():
    q=urllib.request.Request(URL,headers={"User-Agent":"RealityGraph/1.0 finite-form-scan"})
    with urllib.request.urlopen(q,timeout=90) as r: raw=r.read()
    if hashlib.sha256(raw).hexdigest()!=SHA: raise ValueError("archive hash mismatch")
    return raw

def verdict(t):
    m=re.search(r"-- Recorded verdict:\s*(true|false)",t); return m.group(1) if m else None

def parse(s):
    a,b=[x.strip() for x in s.split("=",1)]
    return _Parser(a).parse(),_Parser(b).parse()

def form(t):
    if re.search(r"affineOp_\d+_\d+_\d+_\d+",t): return "affine_named"
    if re.search(r"magmaFin\s+\d+\s*\[",t,re.S): return "magmaFin_flat"
    if "finOpTable" in t: return "finOpTable"
    if "cyclic" in t.lower() or "skew" in t.lower(): return "cyclic_or_skew_named"
    if "ZMod" in t: return "zmod_custom"
    if re.search(r"def\s+\w+\s*\(i j : Fin \d+\)\s*:\s*Fin \d+",t): return "custom_fin_binary_def"
    if re.search(r"let\s+m\s*:\s*Magma\s*\(Fin\s+\d+\)",t): return "fin_model_other"
    return "other"

def main():
    raw=dl()
    rows,proofs,_,_,source_hashes,archive_hash=_read_corpus(raw)
    files=_archive_files(raw); rows_by={str(r["id"]):r for r in rows}
    current=sorted(set(rows_by)-proofs-RETAINED)
    eqtext={}
    for r in rows:
        eqtext.setdefault(int(r["eq1_id"]),str(r["equation1"]))
        eqtext.setdefault(int(r["eq2_id"]),str(r["equation2"]))
    parsed={k:parse(v) for k,v in eqtext.items()}
    donors=[]
    for pid in sorted(proofs):
        row=rows_by.get(pid); blob=files.get(f"proofs/{pid}.lean")
        if not row or not blob: continue
        t=blob.decode("utf-8",errors="replace")
        if verdict(t)!="false": continue
        if not re.search(r"\bMagma\s+\(Fin\s+\d+\)",t): continue
        donors.append({"id":pid,"source":int(row["eq1_id"]),"form":form(t),
                       "has_decideFin":"decideFin!" in t,
                       "has_decide":bool(re.search(r"\bdecide\b",t)),
                       "line_count":t.count("\n")+1})
    bysrc=defaultdict(list)
    for d in donors: bysrc[d["source"]].append(d)
    csources=sorted({int(rows_by[p]["eq1_id"]) for p in current})
    matches=defaultdict(list); checks=0
    for ds,ds_donors in bysrc.items():
        dlhs,drhs=parsed[ds]
        for cs in csources:
            checks+=1; clhs,crhs=parsed[cs]
            m=_specializes(dlhs,drhs,clhs,crhs)
            if m:
                for d in ds_donors: matches[cs].append({**d,"match":m})
    residuals=[]; forms=Counter(); unique=set()
    for pid in current:
        s=int(rows_by[pid]["eq1_id"]); ms=matches.get(s,[])
        if not ms: continue
        for d in ms: unique.add(d["id"])
        for f in {d["form"] for d in ms}: forms[f]+=1
        residuals.append({"residual_id":pid,"source_eq":s,"donors":ms})
    byform=defaultdict(list)
    for item in residuals:
        for f in {d["form"] for d in item["donors"]}: 
            if len(byform[f])<80: byform[f].append(item)
    result={"experiment":"realitygraph-transferable-finite-form-scan-v1",
            "upstream":{"commit":COMMIT,"archive_sha256":archive_hash,"dataset_sha256":source_hashes},
            "scope":{"input_frontier":len(current),"finite_donor_certificates":len(donors),
                     "finite_donor_sources":len(bysrc),"match_checks":checks,
                     "transferable_residuals":len(residuals),"transferable_unique_donors":len(unique)},
            "forms":{"residual_counts":dict(forms),"examples":dict(byform)}}
    print(json.dumps(result,indent=2,sort_keys=True))
    p=Path("results/equational-transferable-finite-forms-v1.json");p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
if __name__=="__main__": main()
