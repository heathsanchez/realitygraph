from __future__ import annotations

import itertools
import json
from pathlib import Path

from equational_residual_demo import _Parser, _read_corpus
from equational_transition_demo import _archive_files
from equational_concrete_table_bank import _download

SOURCE_EQ = 5837
RETAINED = {p.stem for p in Path("certificates").glob("*.lean")}


def E(a,b): return ("E",a,b)
def M(a,b): return ("M",a,b)
def R(a,b): return ("R",a,b)
e=("e",)


def owner(t):
    if t[0]=="M":
        return t[1]
    if t[0]=="E" and t[2][0]=="E":
        q=t[1]; s=t[2][1]; u=t[2][2]
        if s==u:
            o=owner(s)
            if o is not None and o==q:
                return E(s,u)
    return None


def cert(t):
    if t[0]=="E":
        s,u=t[1],t[2]
        if s==u:
            return owner(s)
    return None


def afterJ(a,b,o):
    if a[0]=="E":
        q=a[1]
        return M(a,q) if b==E(o,o) else R(b,a)
    return R(b,a)


def afterA(a,b):
    o=owner(a)
    if o is None:
        return R(b,a)
    if b[0]=="E" and b[2][0]=="E":
        o1=b[1]; o2=b[2][1]; t=b[2][2]
        if o1==o and o2==o:
            return M(a,t)
    return afterJ(a,b,o)


def afterG(a,b):
    return M(a,b) if a==E(b,b) else afterA(a,b)


def afterS(a,b):
    if b[0]=="R":
        k,p=b[1],b[2]
        if a==k:
            return M(a,p)
    return afterG(a,b)


def afterC(a,b):
    o=owner(b)
    return E(o,a) if o is not None else afterS(a,b)


def afterD(a,b):
    if a==b:
        o=cert(a)
        if o is not None:
            return o
    return afterC(a,b)


def op(a,b):
    if b[0]=="E":
        k,v=b[1],b[2]
        if a==k:
            return v
    return afterD(a,b)


def ev(node,env):
    if node[0]=="v":
        return env[node[1]]
    return op(ev(node[1],env),ev(node[2],env))


def pretty(t):
    if t[0]=="e": return "e"
    return f"{t[0]}({pretty(t[1])},{pretty(t[2])})"


def lean(t):
    if t[0]=="e": return "T.e"
    return f"T.{t[0]} ({lean(t[1])}) ({lean(t[2])})"


def parse(formula):
    lhs,rhs=[x.strip() for x in formula.split("=",1)]
    variables=tuple(dict.fromkeys(
        token for token in formula.replace("◇"," ").replace("="," ").replace("("," ").replace(")"," ").split()
        if token.isidentifier()
    ))
    return _Parser(lhs).parse(),_Parser(rhs).parse(),variables


def pools():
    p0=[e]
    p1=[e,E(e,e),M(e,e),R(e,e)]
    # A targeted depth-2 pool rather than all 52 terms: every constructor
    # applied to e/e plus constructor nesting used by the historical witnesses.
    p2=list(p1)
    for a in p1:
        for b in p1:
            for ctor in (E,M,R):
                t=ctor(a,b)
                if t not in p2:
                    p2.append(t)
    return [p0,p1,p2]


def find_witness(identity):
    lhs,rhs,variables=identity
    checked=0
    for pool in pools():
        # Avoid combinatorial explosion for high arity: first all-e, then
        # one-coordinate perturbations, then full p1 cube; p2 only for <=3 vars.
        assignments=[]
        assignments.append(tuple(e for _ in variables))
        for i in range(len(variables)):
            for value in pool:
                a=[e]*len(variables); a[i]=value; assignments.append(tuple(a))
        if len(pool)<=4:
            assignments.extend(itertools.product(pool,repeat=len(variables)))
        elif len(variables)<=3:
            assignments.extend(itertools.product(pool,repeat=len(variables)))
        seen=set()
        for values in assignments:
            if values in seen: continue
            seen.add(values); checked+=1
            env=dict(zip(variables,values))
            lv=ev(lhs,env); rv=ev(rhs,env)
            if lv!=rv:
                return {
                    "assignment":{k:lean(v) for k,v in env.items()},
                    "lhs_normal":lean(lv),
                    "rhs_normal":lean(rv),
                    "lhs_pretty":pretty(lv),
                    "rhs_pretty":pretty(rv),
                    "checked":checked,
                    "pool_size":len(pool),
                }
    return None


def main():
    raw=_download()
    rows,proofs,_,_,source_hashes,archive_hash=_read_corpus(raw)
    by={str(r["id"]):r for r in rows}
    current=sorted(
        pid for pid,row in by.items()
        if int(row["eq1_id"])==SOURCE_EQ and pid not in proofs and pid not in RETAINED
    )
    hits={}
    for pid in current:
        row=by[pid]
        w=find_witness(parse(str(row["equation2"])))
        if w is not None:
            hits[pid]=w
    out={
        "experiment":"realitygraph-5837-term-model-replay-v1",
        "upstream":{"archive_sha256":archive_hash,"dataset_sha256":source_hashes},
        "source_eq":SOURCE_EQ,
        "input_residuals":len(current),
        "residual_ids":current,
        "new_exact_model_witnesses":len(hits),
        "hits":hits,
        "frontier_cluster_if_verified":len(current)-len(hits),
        "new_model_search":0,
    }
    print(json.dumps(out,indent=2,sort_keys=True))
    p=Path("results/equational-5837-term-model-v1.json")
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
if __name__=="__main__":main()
