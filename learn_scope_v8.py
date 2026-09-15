from __future__ import annotations
import json,math
from pathlib import Path

SRC=Path("openml-v7-summary.json")
OUT=Path("learned-scope-v8.json")

def score(rows,g,r):
    tp=fp=fn=0
    for w in rows:
        y=1 if w["survived"] else 0
        p=int(w["gain"]>=g and w["ratio"]<=r)
        tp+=p*y; fp+=p*(1-y); fn+=(1-p)*y
    precision=tp/(tp+fp) if tp+fp else 0.0
    recall=tp/(tp+fn) if tp+fn else 0.0
    f1=2*precision*recall/(precision+recall) if precision+recall else 0.0
    return f1,precision,recall,tp+fp

def fit(rows):
    gs=sorted({x["gain"] for x in rows})
    rs=sorted({x["ratio"] for x in rows})
    gset=[-1.0]+[(a+b)/2 for a,b in zip(gs[:-1],gs[1:])]+[gs[-1]+1e-12]
    rset=[rs[0]-1e-12]+[(a+b)/2 for a,b in zip(rs[:-1],rs[1:])]+[rs[-1]+1e-12]
    best=None
    for g in gset:
        for r in rset:
            f1,p,q,n=score(rows,g,r)
            key=(f1,q,p,-n,g,-r)
            if best is None or key>best[0]:
                best=(key,g,r,(f1,p,q,n))
    return best[1],best[2],best[3]

def main():
    raw=json.loads(SRC.read_text())
    worlds=[]
    for w in raw["worlds"]:
        stat=raw["base"]["source_stats"][str(w["task_id"])]
        worlds.append({
          "task_id":w["task_id"],
          "gain":w["adaptive_cal_gain"],
          "ratio":w["cold_search_cost"]/max(1,w["adaptive_search_cost"]),
          "survived":not stat["revoked"],
        })
    g,r,train=fit(worlds)
    loo=[]
    for i,w in enumerate(worlds):
        gg,rr,_=fit(worlds[:i]+worlds[i+1:])
        loo.append(int(w["gain"]>=gg and w["ratio"]<=rr))
    tp=sum(p and w["survived"] for p,w in zip(loo,worlds))
    fp=sum(p and not w["survived"] for p,w in zip(loo,worlds))
    fn=sum((not p) and w["survived"] for p,w in zip(loo,worlds))
    lp=tp/(tp+fp) if tp+fp else 0.0
    lr=tp/(tp+fn) if tp+fn else 0.0
    out={
      "grammar":"gain_ge_AND_search_ratio_le",
      "training_source":"openml-v7-summary.json",
      "gain_threshold":g,
      "search_ratio_threshold":r,
      "training_f1":train[0],
      "training_precision":train[1],
      "training_recall":train[2],
      "training_promoted":train[3],
      "loo_precision":lp,
      "loo_recall":lr,
      "worlds":len(worlds),
    }
    OUT.write_text(json.dumps(out,sort_keys=True,indent=2)+"\n")
    print(json.dumps(out,sort_keys=True,indent=2))

if __name__=="__main__":main()
