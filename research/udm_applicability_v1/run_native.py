#!/usr/bin/env python3
"""Frozen prospective first-stage native applicability admission for cattrs PR 788.

This protocol produces NO repaired code if a native failure or unchanged
applicability rule has not been warranted. Scientific negatives exit zero,
apparatus failures exit two; both retain their evidence.
"""
from __future__ import annotations
import ast, hashlib, json, os, pathlib, subprocess, sys, xml.etree.ElementTree as ET

BASE="b3fb197563bd784adcbe7a385bf7d414a9c82829"
HEAD="ff4682ad7a6d180feed4a527f8e5059afeb02432"
REMOTE="https://github.com/python-attrs/cattrs.git"
def git(cwd,*args):
    return subprocess.check_output(["git","-C",str(cwd),*args],stderr=subprocess.STDOUT).decode().strip()
def nodes(data):
    tree=ast.parse(data); found={}
    def walk(body,prefix=()):
        for node in body:
            if isinstance(node,ast.ClassDef) and node.name.startswith("Test"):
                walk(node.body,(*prefix,node.name))
            elif isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name.startswith("test"):
                found["::".join((*prefix,node.name))]=ast.dump(node,include_attributes=False)
    walk(tree.body);return found
def report(out,record,code=0):
    (out/"RESULT.json").write_text(json.dumps(record,indent=2,sort_keys=True)+"\n")
    print(json.dumps(record,sort_keys=True));return code
def main(out):
    out.mkdir(parents=True,exist_ok=False)
    result={"schema":"UDM_CATTRS_PROSPECTIVE_APPLICABILITY_V1",
      "source":"python-attrs/cattrs","pr":788,"base":BASE,"head":HEAD,
      "G2":"UNKNOWN","status":"UNKNOWN"}
    work=out/"cattrs"
    subprocess.run(["git","clone","--quiet","--filter=blob:none",REMOTE,str(work)],
                   check=True,timeout=180)
    git(work,"fetch","--quiet","origin",BASE,HEAD)
    git(work,"checkout","--quiet",BASE)
    assert git(work,"rev-parse","HEAD")==BASE
    changes=git(work,"diff","--name-only",BASE,HEAD).splitlines()
    eligible=sorted(p for p in changes if p.endswith(".py") and
                    (pathlib.PurePosixPath(p).name.startswith("test_") or
                     pathlib.PurePosixPath(p).name.endswith("_test.py")))
    result["test_file_candidates"]=eligible
    if not eligible:
        result["status"]="UNKNOWN_NO_CHANGED_AUTHOR_TEST_FILE"
        return report(out,result)
    selected=eligible[0]
    try:
        old=subprocess.check_output(["git","-C",str(work),"show",BASE+":"+selected])
    except subprocess.CalledProcessError:old=b""
    new=subprocess.check_output(["git","-C",str(work),"show",HEAD+":"+selected])
    original=nodes(old) if old else {};changed=nodes(new)
    modified=sorted(k for k,v in changed.items() if original.get(k)!=v)
    result.update({"selected_test":selected,"changed_nodes":modified,
                   "original_sha256":hashlib.sha256(old).hexdigest(),
                   "overlay_sha256":hashlib.sha256(new).hexdigest()})
    if not modified:
        result["status"]="UNKNOWN_NO_CHANGED_TEST_NODE"
        return report(out,result)
    target=work/selected
    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(new)
    # Run native pytest; avoid ever turning collection errors into learning failure.
    junit=out/"native.xml"
    cmd=[sys.executable,"-m","pytest","-q","--junitxml="+str(junit),
         *[selected+"::"+node for node in modified]]
    p=subprocess.run(cmd,cwd=work,capture_output=True,text=True,timeout=600)
    (out/"native.stdout").write_text(p.stdout)
    (out/"native.stderr").write_text(p.stderr)
    result["native_returncode"]=p.returncode
    result["native_command"]=cmd
    if not junit.is_file():
        result["status"]="UNKNOWN_NATIVE_ENVIRONMENT"
        return report(out,result,2)
    root=ET.parse(junit).getroot()
    suites=[root] if root.tag=="testsuite" else list(root.iter("testsuite"))
    count={k:sum(int(s.get(k,0)) for s in suites) for k in
           ("tests","failures","errors","skipped")}
    result["native_counts"]=count
    if count["errors"] or not count["tests"]:
        result["status"]="UNKNOWN_NATIVE_ENVIRONMENT"
        return report(out,result,2)
    if not count["failures"]:
        result["status"]="UNKNOWN_NO_AUTHENTIC_FUTURE_FAILURE"
        return report(out,result)
    # Frozen applicability predicate: no direct Boolean one-argument
    # parametrized test => no licensed acquired observer.
    tree=ast.parse(new)
    matches=[]
    def eligible_shape(fn):
        asserts=[n for n in ast.walk(fn) if isinstance(n,ast.Assert)]
        direct=[]
        for a in asserts:
            expr=a.test
            if isinstance(expr,ast.UnaryOp) and isinstance(expr.op,ast.Not):
                expr=expr.operand
            if (isinstance(expr,ast.Call) and isinstance(expr.func,ast.Name)
                and len(expr.args)==1 and isinstance(expr.args[0],ast.Name)):
                direct.append((expr.func.id,expr.args[0].id))
        for dec in fn.decorator_list:
            if (isinstance(dec,ast.Call) and isinstance(dec.func,ast.Attribute)
                and dec.func.attr=="parametrize" and len(dec.args)>=2):
                try:label=ast.literal_eval(dec.args[0])
                except (ValueError,TypeError):continue
                if len(direct)==1 and label==direct[0][1]:
                    return direct[0]
        return None
    def walk(body,prefix=()):
        for node in body:
            if isinstance(node,ast.ClassDef) and node.name.startswith("Test"):
                walk(node.body,(*prefix,node.name))
            elif isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
                key="::".join((*prefix,node.name))
                if key in modified:
                    shape=eligible_shape(node)
                    if shape:matches.append({"node":key,"classifier":shape[0],
                                              "argument":shape[1]})
    walk(tree.body)
    result["direct_boolean_parametrized_candidates"]=matches
    if not matches:
        result["status"]="REJECTED_PROSPECTIVE_APPLICABILITY_SHAPE"
        return report(out,result)
    # Failing shape is necessary but not sufficient. No production binding
    # or projection generator is inferred from AST alone.
    result["status"]="UNKNOWN_APPLICABILITY_AWAITS_INDEPENDENT_SOURCE_WITNESS"
    return report(out,result)
if __name__=="__main__":
    try:sys.exit(main(pathlib.Path(sys.argv[1]).resolve()))
    except Exception as e:
        print("UNKNOWN_APPARATUS:"+repr(e),file=sys.stderr)
        sys.exit(2)
