#!/usr/bin/env python3
"""Source-exact independent passing controls; native production unchanged."""
from __future__ import annotations
import hashlib,json,os,pathlib,subprocess,sys,xml.etree.ElementTree as ET
BASE="b3fb197563bd784adcbe7a385bf7d414a9c82829"
HEAD="ff4682ad7a6d180feed4a527f8e5059afeb02432"
TEST="tests/strategies/test_include_subclasses.py"
NODE="test_omit_if_default_with_discriminator_override"
SOURCE_ASSERT="assert converter.unstructure(instance) == expected"
def git(w,*args):
    return subprocess.check_output(["git","-C",str(w),*args]).decode().strip()
def run(w,out,node,env=None):
    p=subprocess.run([sys.executable,"-m","pytest","-q","--junitxml="+str(out/"junit.xml"),TEST+"::"+node],cwd=w,capture_output=True,text=True,env=env,timeout=480)
    (out/"stdout.txt").write_text(p.stdout);(out/"stderr.txt").write_text(p.stderr)
    if not (out/"junit.xml").exists():return {"tests":0,"failures":0,"errors":1,"skipped":0}
    root=ET.parse(out/"junit.xml").getroot();suites=[root] if root.tag=="testsuite" else list(root.iter("testsuite"))
    return {k:sum(int(s.get(k,0)) for s in suites) for k in ("tests","failures","errors","skipped")}
def main(dest):
    dest.mkdir(parents=True,exist_ok=False);w=dest/"source"
    subprocess.run(["git","clone","-q","https://github.com/python-attrs/cattrs.git",str(w)],check=True,timeout=180)
    subprocess.run(["git","-C",str(w),"fetch","-q","origin",BASE,HEAD],check=True,timeout=90)
    git(w,"checkout","-q",BASE)
    assert git(w,"rev-parse","HEAD")==BASE
    raw=subprocess.check_output(["git","-C",str(w),"show",HEAD+":"+TEST])
    target=w/TEST;target.write_bytes(raw)
    subprocess.run([sys.executable,"-m","pip","install","-e",str(w)],check=True,capture_output=True,timeout=180)
    baseline=dest/"baseline";baseline.mkdir()
    baseline_counts=run(w,baseline,NODE)
    result={"schema":"UDM_PASSING_CENSUS_V1","base":BASE,"head":HEAD,"test_sha256":hashlib.sha256(raw).hexdigest(),"baseline":baseline_counts,"G2":"UNKNOWN","status":"UNKNOWN"}
    if baseline_counts["tests"]!=2 or baseline_counts["failures"]!=2 or baseline_counts["errors"]!=0:
        result["status"]="UNKNOWN_BASELINE_NOT_REPRODUCED"
    else:
        source=raw.decode()
        if source.count(SOURCE_ASSERT)!=1:
            result["status"]="UNKNOWN_ASSERTION_NOT_UNIQUE"
        else:
            # Observation-only transformed execution. The original baseline remains untouched.
            helper="""
def __udm_record(left,right):
    import json,os
    equal=left==right
    with open(os.environ["UDM_CENSUS_PATH"],"a",encoding="utf8") as f:
        f.write(json.dumps({"actual":left,"expected":right,"equal":equal},sort_keys=True)+"\\n")
    return equal
"""
            # Preserve equality computation, defer collective failure to the end
            # of the loop so later passing controls are observed.
            transformed=source.replace(SOURCE_ASSERT,"__udm_equalities.append(__udm_record(converter.unstructure(instance), expected))")
            anchor="    for instance in (Parent(), Child(), Parent(count=3), Child(count=3)):"
            if transformed.count(anchor)!=1:
                result["status"]="UNKNOWN_LOOP_NOT_UNIQUE"
            else:
                transformed=transformed.replace(anchor,"    __udm_equalities = []\\n"+anchor)
                next_line="        assert converter.structure(expected, Parent) == instance"
                if transformed.count(next_line)!=1:
                    result["status"]="UNKNOWN_NEXT_ASSERTION_NOT_UNIQUE"
                else:
                    transformed=transformed.replace(next_line,next_line+"\\n    assert all(__udm_equalities)")
                    target.write_text(transformed+"\\n"+helper)
                    env=os.environ.copy();env["UDM_CENSUS_PATH"]=str(dest/"census.jsonl")
                    stage=dest/"census";stage.mkdir()
                    census_counts=run(w,stage,NODE,env)
                    result["instrumented"]=census_counts
                    rows=[json.loads(x) for x in (dest/"census.jsonl").read_text().splitlines()] if (dest/"census.jsonl").exists() else []
                    result["comparisons"]=rows
                    if census_counts["errors"] or len(rows)!=8:
                        result["status"]="UNKNOWN_INCOMPLETE_CENSUS"
                    else:
                        failures=[r for r in rows if not r["equal"]]
                        passing=[r for r in rows if r["equal"]]
                        result["passing_count"]=len(passing);result["failure_count"]=len(failures)
                        if len(failures)!=2 or len(passing)!=6:
                            result["status"]="UNKNOWN_CENSUS_MISMATCH"
                        else:
                            extra=[(k,v) for r in failures for k,v in r["actual"].items() if k not in r["expected"]]
                            if len(extra)!=2 or extra[0]!=extra[1]:
                                result["status"]="REJECTED_NO_UNIQUE_EXTRA_FIELD"
                            else:
                                key,value=extra[0]
                                def op(d):
                                    x=dict(d)
                                    if x.get(key,object())==value:x.pop(key,None)
                                    return x
                                safe=all(op(r["actual"])==r["actual"] for r in passing)
                                fixes=all(op(r["actual"])==r["expected"] for r in failures)
                                result["selected_operator"]={"field":key,"value":value,"passing_preserved":safe,"failure_resolved":fixes}
                                result["status"]=("CANDIDATE_CONTROL_PRESERVED_REPAIR_UNSUPPORTED" if safe and fixes else "REJECTED_CONTROL_COLLISION")
                                # No unique directly-returned mapping in generic converter factory established.
                                result["production_repair"]="UNKNOWN_UNSUPPORTED_REPAIR_SHAPE"
    (dest/"RESULT.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\\n")
    print(json.dumps({k:result.get(k) for k in ("status","baseline","instrumented","passing_count","failure_count","selected_operator","production_repair","G2")},sort_keys=True))
    return 0 if not result["status"].startswith("UNKNOWN_") else 2
if __name__=="__main__":sys.exit(main(pathlib.Path(sys.argv[1]).resolve()))
