#!/usr/bin/env python3
"""Frozen V2 native admission, original production, no method changes."""
import ast,json,subprocess,sys,pathlib,xml.etree.ElementTree as ET
BASE="3265c13945a9533f9a3ade8d47eb9b32412c4c27"
HEAD="919255db0f20580214b53f76b6d2295a84c2de1e"
REPO="https://github.com/marshmallow-code/marshmallow.git"
TEST="tests/test_deserialization.py"
PRODUCTION="src/marshmallow/fields.py"
def call(cmd,**kw):return subprocess.check_output(cmd,**kw).decode().strip()
def nodes(raw):
    t=ast.parse(raw);o={}
    def walk(body,p=()):
        for n in body:
            if isinstance(n,ast.ClassDef):walk(n.body,(*p,n.name))
            elif isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name.startswith("test_"):
                o["::".join((*p,n.name))]=ast.dump(n,include_attributes=False)
    walk(t.body);return o
def main(out):
    out.mkdir(parents=True,exist_ok=False);w=out/"world"
    subprocess.run(["git","clone","-q",REPO,str(w)],check=True,timeout=180)
    subprocess.run(["git","-C",str(w),"fetch","-q","origin",BASE,HEAD],check=True,timeout=90)
    subprocess.run(["git","-C",str(w),"checkout","-q",BASE],check=True)
    assert call(["git","-C",str(w),"rev-parse","HEAD"])==BASE
    old=subprocess.check_output(["git","-C",str(w),"show",BASE+":"+TEST])
    new=subprocess.check_output(["git","-C",str(w),"show",HEAD+":"+TEST])
    changes=sorted(k for k,v in nodes(new).items() if nodes(old).get(k)!=v)
    result={"schema":"UDM_FACTORY_PROSPECTIVE_V2","repository":"marshmallow-code/marshmallow",
            "pr":2994,"base":BASE,"head":HEAD,"selected_test":TEST,"changed_nodes":changes,
            "method":"c5bfc48a7213e47357240522bf3f51a6f99ea552","G2":"UNKNOWN","status":"UNKNOWN"}
    if not changes:
        result["status"]="UNKNOWN_NO_CHANGED_TEST_NODE"
    else:
        (w/TEST).write_bytes(new)
        # The exact base package, never repaired production.
        subprocess.run([sys.executable,"-m","pip","install","-e",str(w)],check=True,timeout=180,capture_output=True)
        xml=out/"junit.xml"
        p=subprocess.run([sys.executable,"-m","pytest","-q","--junitxml="+str(xml),*[TEST+"::"+x for x in changes]],
                         cwd=w,capture_output=True,text=True,timeout=360)
        (out/"native.stdout").write_text(p.stdout);(out/"native.stderr").write_text(p.stderr)
        if not xml.exists():result["status"]="UNKNOWN_NATIVE_APPARATUS"
        else:
            root=ET.parse(xml).getroot()
            suites=[root] if root.tag=="testsuite" else list(root.iter("testsuite"))
            counts={k:sum(int(s.get(k,0)) for s in suites) for k in ("tests","failures","errors","skipped")}
            result["native_counts"]=counts
            if not counts["tests"] or counts["errors"]:result["status"]="UNKNOWN_NATIVE_APPARATUS"
            elif not counts["failures"]:result["status"]="UNKNOWN_NO_AUTHENTIC_NATIVE_FAILURE"
            else:
                # Frozen method demands exact learned named option and converter inheritance factory.
                production=(w/PRODUCTION).read_text()
                t=ast.parse(production)
                matches=[]
                for n in ast.walk(t):
                    if not isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):continue
                    a=n.args.args
                    policy=[arg for arg in a if arg.arg=="_cattrs_omit_if_default"]
                    if not policy:continue
                    segment=ast.get_source_segment(production,n) or ""
                    if "converter" in [x.arg for x in a] and "omit_if_default" in segment:matches.append(n.name)
                result["factory_applicability_matches"]=matches
                result["status"]="REJECTED_METHOD_INAPPLICABLE" if not matches else "UNKNOWN_FACTORY_ROLE_AMBIGUITY"
    (out/"RESULT.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result,sort_keys=True))
    return 0 if result["status"]=="REJECTED_METHOD_INAPPLICABLE" else 2
if __name__=="__main__":sys.exit(main(pathlib.Path(sys.argv[1]).resolve()))
