#!/usr/bin/env python3
"""Source-exact cattrs training observation, no future opened."""
import hashlib,json,os,pathlib,subprocess,sys,xml.etree.ElementTree as ET
from realitygraph.udm_field_observer import describe
BASE="b3fb197563bd784adcbe7a385bf7d414a9c82829"
HEAD="ff4682ad7a6d180feed4a527f8e5059afeb02432"
TEST="tests/strategies/test_include_subclasses.py"
NODE="test_omit_if_default_with_discriminator_override"
def git(w,*args):
    return subprocess.check_output(["git","-C",str(w),*args]).decode().strip()
def main(out):
    out.mkdir(parents=True,exist_ok=False)
    world=out/"cattrs"
    subprocess.run(["git","clone","-q","https://github.com/python-attrs/cattrs.git",str(world)],check=True,timeout=180)
    subprocess.run(["git","-C",str(world),"fetch","-q","origin",BASE,HEAD],check=True,timeout=60)
    git(world,"checkout","--quiet",BASE)
    if git(world,"rev-parse","HEAD")!=BASE:raise ValueError("BASE_NOT_EXACT")
    before=subprocess.check_output(["git","-C",str(world),"show",BASE+":"+TEST])
    overlay=subprocess.check_output(["git","-C",str(world),"show",HEAD+":"+TEST])
    (world/TEST).write_bytes(overlay)
    subprocess.run([sys.executable,"-m","pip","install","-e",str(world)],check=True,timeout=180,capture_output=True)
    obs=out/"mapping-observations.jsonl"
    junit=out/"junit.xml"
    env=os.environ.copy()
    env["UDM_FIELD_OBSERVATIONS"]=str(obs)
    env["PYTHONPATH"]=str(pathlib.Path(__file__).resolve().parents[2])+os.pathsep+env.get("PYTHONPATH","")
    cmd=[sys.executable,"-m","pytest","-q","-p","realitygraph.udm_field_observer","--junitxml="+str(junit),TEST+"::"+NODE]
    p=subprocess.run(cmd,cwd=world,capture_output=True,text=True,timeout=480,env=env)
    (out/"native.stdout").write_text(p.stdout)
    (out/"native.stderr").write_text(p.stderr)
    result={"schema":"UDM_FIELD_GENESIS_TRAINING_V1","base":BASE,"head":HEAD,
       "test":TEST,"node":NODE,"baseline_test_sha256":hashlib.sha256(before).hexdigest(),
       "overlay_sha256":hashlib.sha256(overlay).hexdigest(),"status":"UNKNOWN",
       "G2":"UNKNOWN","native_returncode":p.returncode}
    if not junit.exists():
        result["status"]="UNKNOWN_NATIVE_ENVIRONMENT"
    else:
        root=ET.parse(junit).getroot()
        suites=[root] if root.tag=="testsuite" else list(root.iter("testsuite"))
        counts={k:sum(int(s.get(k,0)) for s in suites) for k in ("tests","failures","errors","skipped")}
        result["native_counts"]=counts
        rows=[json.loads(line) for line in obs.read_text().splitlines()] if obs.exists() else []
        result["mapping_failure_observations"]=rows
        classes={}
        for row in rows:
            key=(tuple(row["left_only"]),tuple(row["right_only"]),tuple(row["unequal"]))
            classes[str(key)]=classes.get(str(key),0)+1
        result["field_difference_classes"]=classes
        if counts["tests"]==0 or counts["errors"]:
            result["status"]="UNKNOWN_NATIVE_ENVIRONMENT"
        elif counts["failures"]==0:
            result["status"]="UNKNOWN_NO_AUTHENTIC_TRAINING_FAILURE"
        elif not rows:
            result["status"]="REJECTED_NO_MAPPING_RESIDUAL_CAPTURE"
        else:
            # Failing observations do not prove preservation on passing controls.
            result["status"]="CANDIDATE_FIELD_OBSERVATION_NO_REPAIR_WARRANT"
    (out/"RESULT.json").write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"status":result["status"],"native_counts":result.get("native_counts"),
        "mapping_observations":len(result.get("mapping_failure_observations",[]))}))
    return 0 if result["status"] not in ("UNKNOWN_NATIVE_ENVIRONMENT",) else 2
if __name__=="__main__":sys.exit(main(pathlib.Path(sys.argv[1]).resolve()))
