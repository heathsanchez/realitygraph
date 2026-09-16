from __future__ import annotations
import csv,hashlib,io,json,re,urllib.request
from pathlib import Path
import openml

SEED="realitygraph-capability-generator-transfer-v2-source-only"
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

    req=urllib.request.Request(PMLB,headers={"User-Agent":"RealityGraph capability generator transfer V2 manifest"})
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
    v2names={stem(x) for x in (
        "cybersecurity_attacks","train","rdata","jc_penney_products","avocado_sales",
        "kidtran","libras_move","pbcseq","treasury","std","grace","kings_county",
        "metabric","2dplanes","Reading_Hydro","munich-rent-index-1999",
        "concrete_compressive_strength","TRS_SCZ","test_dataset","space_ga"
    )}
    generator_v1_names={stem(x) for x in (
        "fps_benchmark","flchain","Performance-Prediction","bodyfat",
        "CookbookReviews","Nintendo3DS-Games","health_insurance","dataFTR",
        "support","shrutime","forest_fires_cat","turing_course_binary_data",
        "baseball-hitter","svmguide1","LimeSoda_BB.250_dataset","Wheat",
        "liver-disorders","kdd_el_nino-small",
        "Pokemon-(Generation-1---Generation-8)","SWD"
    )}
    byfamily={}
    for _,x in tasks.iterrows():
        try:
            tid=int(x[tc]); did=int(x[dc]); rows=int(float(x[rc]))
            feats=int(float(x[fc])); nums=int(float(x[xc]))
        except Exception:
            continue
        name=str(x[nc]); s=stem(name); low=name.lower()
        if s in pmlb_names or s in v1names or s in v2names or s in generator_v1_names: continue
        if any(tok in low for tok in banned_tokens): continue
        if (
            "arsenic" in low
            or low.startswith("chscase_")
            or low.startswith("disclosure_")
            or "superconduct" in low
            or "grid_stability" in low
            or "electrical_grid" in low
            or "kdd_coil" in low
            or low.startswith("ele-")
            or "cpmp" in low
            or "mabbob" in low
            or "bike_sharing" in low
            or "bike-sharing" in low
            or low.startswith("visualizing_")
            or low == "cmc"
            or "test_dsn" in low
            or "turing" in low
            or "german" in low
            or "pokemon" in low
            or "svmguide" in low
            or "satellite" in low
            or "qsar" in low
            or "titanic" in low
        ): continue
        if not (250<=rows<=50000 and 3<=feats<=100 and nums>=3): continue
        z={"task_id":tid,"data_id":did,"name":name,"instances":rows,"features":feats,"numeric_features":nums}
        family=("microwave_contaminant_urbinati" if "contaminant-detection-in-packaged-cocoa-hazelnut-spread-jars" in low else s)
        if family not in byfamily or tid<byfamily[family]["task_id"]:
            byfamily[family]=z

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
    Path("capability-generator-transfer-v2-manifest.json").write_text(json.dumps(out,sort_keys=True,indent=2)+"\n")
    print("eligible",len(worlds)); print("manifest_digest",digest); print("target_data_downloaded=0")
    for i,z in enumerate(block): print(i,z)

if __name__=="__main__": main()
