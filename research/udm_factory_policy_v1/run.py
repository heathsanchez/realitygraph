#!/usr/bin/env python3
"""One frozen policy-inheritance patch; native verification and causal withdrawal."""
from pathlib import Path
import hashlib,json,subprocess,sys,xml.etree.ElementTree as ET
BASE="b3fb197563bd784adcbe7a385bf7d414a9c82829"
HEAD="ff4682ad7a6d180feed4a527f8e5059afeb02432"
PROD="src/cattrs/gen/__init__.py"
TESTS=["tests/strategies/test_include_subclasses.py","tests/test_gen_dict.py"]
NODE="tests/strategies/test_include_subclasses.py::test_omit_if_default_with_discriminator_override"
def git(w,*args):
    return subprocess.check_output(["git","-C",str(w),*args]).decode().strip()
def native(w,out,targets):
    out.mkdir(parents=True,exist_ok=False)
    cmd=[sys.executable,"-m","pytest","-q","--junitxml="+str(out/"junit.xml"),*targets]
    p=subprocess.run(cmd,cwd=w,capture_output=True,text=True,timeout=600)
    (out/"stdout.txt").write_text(p.stdout);(out/"stderr.txt").write_text(p.stderr)
    if not (out/"junit.xml").exists():return {"tests":0,"failures":0,"errors":1,"skipped":0,"returncode":p.returncode}
    root=ET.parse(out/"junit.xml").getroot()
    suites=[root] if root.tag=="testsuite" else list(root.iter("testsuite"))
    return {**{k:sum(int(s.get(k,0)) for s in suites) for k in ("tests","failures","errors","skipped")},"returncode":p.returncode}
def patch(data):
    src=data.decode()
    old="_cattrs_omit_if_default: bool = False,"
    new='_cattrs_omit_if_default: bool | Literal["from_converter"] = "from_converter",'
    if src.count(old)!=2:raise ValueError("SOURCE_SHAPE_CHANGED")
    src=src.replace(old,new)
    anchor='    if _cattrs_use_alias == "from_converter":'
    if src.count(anchor)<1:raise ValueError("SENTINEL_INSERTION_MISSING")
    insertion='    if _cattrs_omit_if_default == "from_converter":\n        _cattrs_omit_if_default = getattr(converter, "omit_if_default", False)\n\n'
    src=src.replace(anchor,insertion+anchor,1)
    compile(src,PROD,"exec")
    return src.encode()
def main(out):
    out.mkdir(parents=True,exist_ok=False)
    w=out/"cattrs"
    subprocess.run(["git","clone","-q","https://github.com/python-attrs/cattrs.git",str(w)],check=True,timeout=180)
    subprocess.run(["git","-C",str(w),"fetch","-q","origin",BASE,HEAD],check=True,timeout=90)
    git(w,"checkout","-q",BASE)
    if git(w,"rev-parse","HEAD")!=BASE:raise ValueError("BASE_MISMATCH")
    prod=w/PROD
    original=subprocess.check_output(["git","-C",str(w),"show",BASE+":"+PROD])
    if prod.read_bytes()!=original:raise ValueError("PRODUCTION_NOT_ORIGINAL")
    for t in TESTS:
        (w/t).write_bytes(subprocess.check_output(["git","-C",str(w),"show",HEAD+":"+t]))
    subprocess.run([sys.executable,"-m","pip","install","-e",str(w)],check=True,capture_output=True,timeout=180)
    result={"schema":"UDM_FACTORY_POLICY_V1","base":BASE,"head":HEAD,
        "original_sha256":hashlib.sha256(original).hexdigest(),
        "G2":"UNKNOWN","future":"UNSELECTED","status":"UNKNOWN"}
    before=native(w,out/"baseline",[NODE])
    result["baseline"]=before
    if before["tests"]!=2 or before["failures"]!=2 or before["errors"]!=0:
        result["status"]="UNKNOWN_BASELINE_NOT_REPRODUCED"
    else:
        edited=patch(original)
        result["patch_sha256"]=hashlib.sha256(edited).hexdigest()
        (out/"CANDIDATE_SOURCE.py").write_bytes(edited)
        prod.write_bytes(edited)
        checks={}
        checks["protected_a"]=native(w,out/"protected_a",[NODE])
        checks["protected_b"]=native(w,out/"protected_b",[NODE])
        checks["author_files"]=native(w,out/"author_files",TESTS)
        result["checks"]=checks
        good=all(x["tests"]>0 and x["failures"]==x["errors"]==0 for x in checks.values())
        if not good:result["status"]="REJECTED_NATIVE_PATCH"
        else:
            prod.write_bytes(original)
            withdrawal=native(w,out/"withdrawal",[NODE])
            result["withdrawal"]=withdrawal
            if withdrawal["failures"]!=2 or withdrawal["errors"]!=0:
                result["status"]="UNKNOWN_WITHDRAWAL_NOT_CAUSAL"
            else:
                prod.write_bytes(edited)
                if prod.read_bytes()!=edited:raise ValueError("RESTORATION_BYTES_CHANGED")
                restoration=native(w,out/"restoration",[NODE])
                result["restoration"]=restoration
                if restoration["tests"]!=2 or restoration["failures"] or restoration["errors"]:
                    result["status"]="UNKNOWN_RESTORATION_FAILED"
                else:result["status"]="WARRANTED_BOUNDED_FACTORY_POLICY_INHERITANCE_TRAINING"
    (out/"RESULT.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result,sort_keys=True))
    return 0 if not result["status"].startswith("UNKNOWN") and not result["status"].startswith("REJECTED") else 2
if __name__=="__main__":sys.exit(main(Path(sys.argv[1]).resolve()))
