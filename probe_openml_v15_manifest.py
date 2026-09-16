from __future__ import annotations
import csv,hashlib,io,json,re,urllib.request
from pathlib import Path
import openml

SEED="realitygraph-openml-v15-source-only"
OLD={40981,41027,23,1464,40982,41156,1049,40983,42733,1487,188,1461,1494,31,40984,4538,1067,40498,40900,1475}
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
    tasks=openml.tasks.list_tasks(type=1,output_format="dataframe")
    tc=col(tasks,"tid","task_id"); dc=col(tasks,"did","data_id"); nc=col(tasks,"name")
    rc=col(tasks,"NumberOfInstances"); fc=col(tasks,"NumberOfFeatures")
    cc=col(tasks,"NumberOfClasses"); xc=col(tasks,"NumberOfNumericFeatures")
    req=urllib.request.Request(PMLB,headers={"User-Agent":"RealityGraph V15 manifest"})
    with urllib.request.urlopen(req,timeout=60) as r: raw=r.read()
    oldnames={stem(x["dataset"]) for x in csv.DictReader(io.StringIO(raw.decode()),delimiter="\t")}
    v7names={stem(x) for x in (
        "Australian","jungle_chess_2pcs_raw_endgame_complete","cmc",
        "blood-transfusion-service-center","steel-plates-fault","ada","pc4","wilt",
        "Click_prediction_small","ozone-level-8hr","eucalyptus","bank-marketing",
        "qsar-biodeg","credit-g","segment","GesturePhaseSegmentationProcessed",
        "kc1","wine-quality-white","Satellite","first-order-theorem-proving"
    )}
    v8names={stem(x) for x in (
        "airlines_seed_0_nrows_2000_nclasses_10_ncols_100_stratify_True",
        "Phishing_Legitimate_full","elevators","FOREX_audjpy-day-High",
        "FOREX_eurhuf-day-Close","fri_c2_250_5",
        "jungle_chess_2pcs_endgame_elephant_elephant","algerian_forest_fires",
        "Predicting_Risk_Factors_of_Chronic_Kidney_Disease","fri_c0_250_10",
        "autoUniv-au6-750","ilpd-numeric","online-shoppers-intention","houses",
        "FOREX_audsgd-hour-Close","Bank_marketing_data_set_UCI",
        "FOREX_nzdusd-hour-High",
        "road-safety_seed_0_nrows_2000_nclasses_10_ncols_100_stratify_True",
        "analcatdata_draft","jEdit_4.0_4.2"
    )}
    v9names={stem(x) for x in (
        "spambase_reproduced","kc3","football-player-position","PriceRunner",
        "fri_c0_500_50","glioma_grading_clinical_and_mutation_features",
        "E-CommereShippingData","volcanoes-e1","taiwanese_bankruptcy_prediction",
        "volcanoes-a4","FOREX_chfsgd-hour-High","fri_c2_1000_5",
        "FOREX_eurnzd-day-Close","volcanoes-b3","telco-customer-churn",
        "FOREX_eurdkk-day-Close","thyroid-dis","badges2","fri_c3_1000_25",
        "jungle_chess_2pcs_endgame_lion_elephant"
    )}
    v10names={stem(x) for x in (
        "FOREX_cadchf-hour-High","FOREX_euraud-day-Close","fri_c1_250_50",
        "Apple_Stock_Price_Trends_Classification","FOREX_audchf-hour-Close",
        "FOREX_eurrub-day-Close","ada_prior",
        "MiniBooNE_seed_0_nrows_2000_nclasses_10_ncols_100_stratify_True",
        "Dynamically-Generated-Hate-Speech-Dataset","FOREX_euraud-hour-High",
        "fri_c0_1000_5","fri_c4_1000_10","dataset_credit","heloc",
        "FOREX_chfjpy-day-Close","KDDCup09_upselling","fri_c3_500_5",
        "PizzaCutter1","Skin_Cancer_PAD-UFES-20","autos_clean"
    )}
    v11names={stem(x) for x in (
        "doa_bwin","FOREX_eurgbp-hour-High","fri_c1_250_10",
        "FOREX_audusd-hour-High","rmftsa_sleepdata","credit","volcanoes-a1",
        "eeg-eye-state","Diabetes130US_seed_0_nrows_2000_nclasses_10_ncols_100_stratify_True",
        "German-Credit-Data-Creditability","fri_c1_500_5","Interest_Rate",
        "FOREX_eurchf-day-High","NewspaperChurn","autoUniv-au7-700",
        "chscase_vine2","sick","FOREX_eurpln-hour-Close","FOREX_eurpln-day-High",
        "bank32nh"
    )}
    v12names={stem(x) for x in (
        "LED-display-domain-7digit","depression_2020","FOREX_eurcad-hour-High",
        "cardiotocography","credit-approval","MegaWatt1",
        "air-quality-and-pollution-assessment","volcanoes-d2","fri_c3_500_50",
        "dataset_credit_score","CastMetal1","FOREX_chfjpy-day-High",
        "insurance_company","student_depression_dataset","melbourne_airbnb",
        "dummy","disclosure_x_bias","mv","wine","FOREX_eurnzd-hour-High"
    )}
    v13names={stem(x) for x in (
        "FOREX_eurtry-hour-High","seismic-bumps","cylinder-bands",
        "analcatdata_halloffame","Cervical_Cancer_Risk_Factors",
        "Accidents_Prediction_Dataset_Pipeline","cleve","PieChart2",
        "chscase_whale","fri_c0_250_5","in_vehicle_coupon_recommendation",
        "CPMP-2015-classification","fri_c0_500_25","FOREX_cadchf-hour-Close",
        "glass","MiceProtein","seeds","FOREX_usdcad-hour-Close",
        "letter-challenge-unlabeled.arff","FOREX_nzdusd-day-Close"
    )}
    v14names={stem(x) for x in (
        "cars1","Credit_Approval_Classification","ailerons","ibm-employee-attrition",
        "FOREX_eurdkk-hour-High","FOREX_audnzd-hour-High","fri_c2_500_5",
        "FICO-HELOC-cleaned","FOREX_eursek-hour-High",
        "covertype_seed_0_nrows_2000_nclasses_10_ncols_100_stratify_True",
        "kc2","BNG(breast-w)","user-knowledge","Advanced_IoT_Dataset",
        "FOREX_eurjpy-hour-Close","vinnie","FOREX_eurusd-hour-Close","anneal",
        "credit_risk_china","volcanoes-c1"
    )}
    bydata={}
    for _,x in tasks.iterrows():
        try:
            tid=int(x[tc]); did=int(x[dc]); rows=int(float(x[rc])); f=int(float(x[fc])); c=int(float(x[cc])); num=int(float(x[xc]))
        except Exception:continue
        name=str(x[nc])
        lname=name.lower()
        # V15 raises the source-distinctness bar before any target payload is opened.
        # Exclude recurrent generator / market / legacy families already represented
        # in V7-V14, including obvious renamed replicas.
        if (
            lname.startswith("forex_")
            or lname.startswith("fri_")
            or lname.startswith("volcanoes")
            or "credit" in lname
            or "anneal" in lname
            or "breast" in lname
            or "sick" in lname
        ):
            continue
        if did in OLD or stem(name) in oldnames or stem(name) in v7names or stem(name) in v8names or stem(name) in v9names or stem(name) in v10names or stem(name) in v11names or stem(name) in v12names or stem(name) in v13names or stem(name) in v14names or not(200<=rows<=50000 and 2<=f<=100 and 2<=c<=10 and num>=2):continue
        z={"task_id":tid,"data_id":did,"name":name,"instances":rows,"features":f,"classes":c,"numeric_features":num}
        family=stem(name)
        if family not in bydata or tid<bydata[family]["task_id"]:
            bydata[family]=z
    a=list(bydata.values())
    a.sort(key=lambda z:(hashlib.sha256(f"{SEED}|{z['task_id']}|{z['data_id']}|{z['name']}|{z['instances']}|{z['features']}|{z['classes']}".encode()).digest(),z["task_id"]))
    block=a[:20]
    if len(block)<20:raise AssertionError(f"eligible={len(a)}")
    digest=hashlib.sha256("\n".join(f"{z['task_id']}|{z['data_id']}|{z['name']}|{z['instances']}|{z['features']}|{z['classes']}|{z['numeric_features']}" for z in block).encode()).hexdigest()
    out={"eligible_count":len(a),"manifest_digest":digest,"worlds":block,"target_data_downloaded":False}
    Path("openml-v15-manifest.json").write_text(json.dumps(out,sort_keys=True,indent=2)+"\n")
    print("eligible",len(a));print("manifest_digest",digest);print("target_data_downloaded=0")
    for i,z in enumerate(block):print(i,z)

if __name__=="__main__":main()
