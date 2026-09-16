from __future__ import annotations
import csv,hashlib,io,json,re,urllib.request
from pathlib import Path
import openml

SEED="realitygraph-openml-regression-transfer-v2-source-only"
PMLB="https://raw.githubusercontent.com/EpistasisLab/pmlb/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/pmlb/all_summary_stats.tsv"

def stem(x):
    s=str(x).lower().replace("-","_").replace(" ","_")
    s=re.sub(r"_seed_\d+.*$","",s)
    s=re.sub(r"_reproduced.*$","",s)
    return re.sub(r"[^a-z0-9]+","",s)

def n(x): return str(x).lower().replace("_","").replace(" ","")

def col(df,*xs):
    t={n(c):c for c in df.columns}
    for x in xs:
        if n(x) in t:return t[n(x)]
    raise KeyError(xs)

def main():
    tasks=openml.tasks.list_tasks(type=2,output_format="dataframe")
    tc=col(tasks,"tid","task_id"); dc=col(tasks,"did","data_id"); nc=col(tasks,"name")
    rc=col(tasks,"NumberOfInstances"); fc=col(tasks,"NumberOfFeatures")
    xc=col(tasks,"NumberOfNumericFeatures")

    req=urllib.request.Request(PMLB,headers={"User-Agent":"RealityGraph regression transfer V2 manifest"})
    with urllib.request.urlopen(req,timeout=60) as r: raw=r.read()
    pmlb_names={stem(x["dataset"]) for x in csv.DictReader(io.StringIO(raw.decode()),delimiter="\t")}

    # Family exclusions are source-only and deliberately broad. They remove families
    # already represented by earlier classification/PMLB work without consulting targets.
    banned_tokens=(
      "forex","credit","loan","fri","volcano","puma","kin8","boston","heart",
      "auto","colleges","wine","ailerons","cpu","house","housing","bank",
      "stock","financial","energy","abalone","diabetes","servo","friedman",
      "elevator","breast","kidney","covertype","rmftsa","bng("
    )
    v1names={stem(x) for x in (
        "DSN","Violent_Crime_by_County_1975_to_2016","mu284","project3_cat",
        "ucs_scm_3","ELE-1","superconductivity","medical_cost","wind","LEV",
        "cps88wages","DEE","airfoil_self_noise","liver",
        "mabbob_ela_as_2d_regression_modcma","auction_verification","bladder0",
        "mabbob_ela_as_5d_regression_RCobyla",
        "sustainable_development_report_zero_hunger",
        "Kaggle_bike_sharing_demand_challange"
    )}
    byfamily={}
    for _,x in tasks.iterrows():
        try:
            tid=int(x[tc]); did=int(x[dc]); rows=int(float(x[rc]))
            feats=int(float(x[fc])); nums=int(float(x[xc]))
        except Exception:
            continue
        name=str(x[nc]); s=stem(name); low=name.lower()
        if s in pmlb_names or s in v1names: continue
        if any(tok in low for tok in banned_tokens): continue
        if (
            "cpmp" in low
            or "mabbob" in low
            or "bike_sharing" in low
            or "bike-sharing" in low
            or low.startswith("visualizing_")
        ): continue
        if not (250<=rows<=50000 and 3<=feats<=100 and nums>=3): continue
        z={"task_id":tid,"data_id":did,"name":name,"instances":rows,"features":feats,"numeric_features":nums}
        if s not in byfamily or tid<byfamily[s]["task_id"]:
            byfamily[s]=z

    worlds=list(byfamily.values())
    worlds.sort(key=lambda z:(hashlib.sha256(
      f"{SEED}|{z['task_id']}|{z['data_id']}|{z['name']}|{z['instances']}|{z['features']}|{z['numeric_features']}".encode()
    ).digest(),z["task_id"]))
    block=worlds[:20]
    if len(block)<20: raise AssertionError(f"eligible={len(worlds)}")
    digest=hashlib.sha256("\n".join(
      f"{z['task_id']}|{z['data_id']}|{z['name']}|{z['instances']}|{z['features']}|{z['numeric_features']}"
      for z in block
    ).encode()).hexdigest()
    out={"eligible_count":len(worlds),"manifest_digest":digest,"worlds":block,
         "task_type":"Supervised Regression","target_data_downloaded":False}
    Path("openml-regression-transfer-v2-manifest.json").write_text(json.dumps(out,sort_keys=True,indent=2)+"\n")
    print("eligible",len(worlds)); print("manifest_digest",digest); print("target_data_downloaded=0")
    for i,z in enumerate(block): print(i,z)

if __name__=="__main__": main()
