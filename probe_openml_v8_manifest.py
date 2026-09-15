from __future__ import annotations
import csv,hashlib,io,json,re,urllib.request
from pathlib import Path
import openml

SEED="realitygraph-openml-v8-source-only"
OLD={40981,41027,23,1464,40982,41156,1049,40983,42733,1487,188,1461,1494,31,40984,4538,1067,40498,40900,1475}
PMLB="https://raw.githubusercontent.com/EpistasisLab/pmlb/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/pmlb/all_summary_stats.tsv"

def stem(x):
    s=str(x).lower().replace("-","_").replace(" ","_")
    s=re.sub(r"_seed_\\d+.*$","",s)
    return re.sub(r"[^a-z0-9]+","",s)
def n(x): return str(x).lower().replace("_","").replace(" ","")
def col(df,*xs):
    t={n(c):c for c in df.columns}
    for x in xs:
        if n(x) in t:return t[n(x)]
    raise KeyError(xs)

def main():
    tasks=openml.tasks.list_tasks(type=1,output_format="dataframe")
    tc=col(tasks,"tid","task_id"); dc=col(tasks,"did","data_id"); nc=col(tasks,"name")
    rc=col(tasks,"NumberOfInstances"); fc=col(tasks,"NumberOfFeatures")
    cc=col(tasks,"NumberOfClasses"); xc=col(tasks,"NumberOfNumericFeatures")
    req=urllib.request.Request(PMLB,headers={"User-Agent":"RealityGraph V8 manifest"})
    with urllib.request.urlopen(req,timeout=60) as r: raw=r.read()
    oldnames={x["dataset"] for x in csv.DictReader(io.StringIO(raw.decode()),delimiter="\t") if x.get("task")=="classification"}
    bydata={}
    for _,x in tasks.iterrows():
        try:
            tid=int(x[tc]); did=int(x[dc]); rows=int(float(x[rc])); f=int(float(x[fc])); c=int(float(x[cc])); num=int(float(x[xc]))
        except Exception:continue
        name=str(x[nc])
        if did in OLD or stem(name) in oldnames or stem(name) in v7names or not(200<=rows<=50000 and 2<=f<=100 and 2<=c<=10 and num>=2):continue
        z={"task_id":tid,"data_id":did,"name":name,"instances":rows,"features":f,"classes":c,"numeric_features":num}
        if did not in bydata or tid<bydata[did]["task_id"]:bydata[did]=z
    a=list(bydata.values())
    a.sort(key=lambda z:(hashlib.sha256(f"{SEED}|{z['task_id']}|{z['data_id']}|{z['name']}|{z['instances']}|{z['features']}|{z['classes']}".encode()).digest(),z["task_id"]))
    block=a[:20]
    if len(block)<20:raise AssertionError(f"eligible={len(a)}")
    digest=hashlib.sha256("\n".join(f"{z['task_id']}|{z['data_id']}|{z['name']}|{z['instances']}|{z['features']}|{z['classes']}|{z['numeric_features']}" for z in block).encode()).hexdigest()
    out={"eligible_count":len(a),"manifest_digest":digest,"worlds":block,"target_data_downloaded":False}
    Path("openml-v8-manifest.json").write_text(json.dumps(out,sort_keys=True,indent=2)+"\n")
    print("eligible",len(a));print("manifest_digest",digest);print("target_data_downloaded=0")
    for i,z in enumerate(block):print(i,z)

if __name__=="__main__":main()
