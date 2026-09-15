from __future__ import annotations
import csv, hashlib, io, json, urllib.request
from pathlib import Path
import openml

SUITE="amlb-classification-all"
SEED="realitygraph-openml-v7-source-only"
PMLB="https://raw.githubusercontent.com/EpistasisLab/pmlb/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/pmlb/all_summary_stats.tsv"

def norm(x):
    return str(x).lower().replace("_","").replace(" ","")

def col(frame,*names):
    table={norm(x):x for x in frame.columns}
    for n in names:
        if norm(n) in table:
            return table[norm(n)]
    raise KeyError((names,list(frame.columns)))

def main():
    suite=openml.study.get_suite(SUITE)
    tasks=openml.tasks.list_tasks(task_id=list(suite.tasks),output_format="dataframe")
    tid=col(tasks,"tid","task_id"); did=col(tasks,"did","data_id")
    namec=col(tasks,"name"); nc=col(tasks,"NumberOfInstances")
    fc=col(tasks,"NumberOfFeatures"); cc=col(tasks,"NumberOfClasses")
    numc=col(tasks,"NumberOfNumericFeatures")

    req=urllib.request.Request(PMLB,headers={"User-Agent":"RealityGraph source manifest"})
    with urllib.request.urlopen(req,timeout=60) as r: raw=r.read()
    rr=csv.DictReader(io.StringIO(raw.decode()),delimiter="\t")
    old={x["dataset"] for x in rr if x.get("task")=="classification" and not x["dataset"].startswith("_deprecated_")}

    rows=[]
    for _,x in tasks.iterrows():
        try:
            task_id=int(x[tid]); data_id=int(x[did]); n=int(float(x[nc]))
            f=int(float(x[fc])); classes=int(float(x[cc])); numeric=int(float(x[numc]))
        except Exception:
            continue
        name=str(x[namec])
        if name in old or not (200<=n<=50000 and 2<=f<=100 and 2<=classes<=10 and numeric>=2):
            continue
        rows.append({"task_id":task_id,"data_id":data_id,"name":name,"instances":n,"features":f,"classes":classes,"numeric_features":numeric})

    def k(x):
        body=f"{SEED}|{x['task_id']}|{x['data_id']}|{x['name']}|{x['instances']}|{x['features']}|{x['classes']}"
        return hashlib.sha256(body.encode()).digest(),x["task_id"]
    rows.sort(key=k)
    if len(rows)<20: raise AssertionError(f"eligible={len(rows)}")
    block=rows[:20]
    digest=hashlib.sha256("\n".join(f"{x['task_id']}|{x['data_id']}|{x['name']}|{x['instances']}|{x['features']}|{x['classes']}|{x['numeric_features']}" for x in block).encode()).hexdigest()
    out={"suite":SUITE,"suite_id":int(suite.id),"suite_tasks":len(suite.tasks),"eligible_count":len(rows),"manifest_digest":digest,"worlds":block,"target_data_downloaded":False}
    Path("openml-v7-manifest.json").write_text(json.dumps(out,sort_keys=True,indent=2)+"\n")
    print(f"suite={SUITE} suite_id={suite.id} tasks={len(suite.tasks)} eligible={len(rows)}")
    print(f"manifest_digest={digest}")
    print("target_data_downloaded=0")
    for i,x in enumerate(block):
        print(f"{i:02d} task={x['task_id']} data={x['data_id']} {x['name']} n={x['instances']} f={x['features']} num={x['numeric_features']} c={x['classes']}")

if __name__=="__main__": main()
