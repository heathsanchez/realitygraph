#!/usr/bin/env python3
"""Independently replay current Mathlib theorems using original Lean kernel.

One exact observed HEAD, two source-derived declarations, separate receiver code.
No claim of second independent kernel, signatures or cross-revision equivalence.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import time
import urllib.request
from consumer import Refused, git_blob, h256, policy_from_bytes, source_declaration

HERE = Path(__file__).resolve().parent
WORK = HERE / "current_native_workspace"
OUT = HERE / "current_native_evidence"
REPO, BRANCH = "leanprover-community/mathlib4", "master"
SHA = re.compile(r"^[0-9a-f]{40}$")
STEPS = []

def step(name, args, cwd=WORK, expected_code=0, marker=None, timeout=650):
    started = time.monotonic()
    try:
        p = subprocess.run(args, cwd=cwd, check=False, text=True,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           errors="replace", timeout=timeout)
        code, output = p.returncode, p.stdout
    except subprocess.TimeoutExpired:
        code, output = 124, "PROCESS_TIMEOUT"
    raw = ("$ " + " ".join(args) + "\n" + output).encode()
    (OUT / (name + ".log")).write_bytes(raw)
    entry = {"name": name, "code": code, "expected_code": expected_code,
             "log_sha256": h256(raw),
             "elapsed_seconds": round(time.monotonic()-started, 3),
             "marker": marker, "marker_found": marker in output if marker else None}
    STEPS.append(entry)
    print("STEP", json.dumps(entry, sort_keys=True), flush=True)
    if code != expected_code or (marker and marker not in output):
        raise Refused("NATIVE_CHECK_FAILED_" + name)
    return output

def github_head():
    url = "https://api.github.com/repos/" + REPO + "/branches/" + BRANCH
    headers = {"Accept":"application/vnd.github+json",
               "X-GitHub-Api-Version":"2022-11-28",
               "User-Agent":"realitygraph-current-lean-replay"}
    if os.environ.get("GH_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GH_TOKEN"]
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers=headers),
                                    timeout=55) as r:
            if r.geturl() != url:
                raise Refused("UPSTREAM_REDIRECT_UNTRUSTED")
            data = json.loads(r.read(250000))
    except Refused:
        raise
    except Exception:
        raise Refused("UPSTREAM_HEAD_UNAVAILABLE") from None
    try:
        tip = data["commit"]["sha"]
        if data["name"] != BRANCH or not SHA.fullmatch(tip):
            raise Refused("UPSTREAM_BRANCH_MISMATCH")
        return tip
    except (KeyError,TypeError):
        raise Refused("UPSTREAM_BRANCH_RESPONSE_INVALID") from None

def generate(module, name):
    honest = f"""import Lean
import {module}
open Lean Elab Command
run_cmd do
  let some (.thmInfo original) := (← getEnv).find? ``{name}
    | throwError "ORIGINAL_THEOREM_MISSING"
  let levels := original.levelParams.map Lean.Level.param
  liftCoreM <| addDecl <| Lean.Declaration.thmDecl {{
    name := `ReceiverProof.checked
    levelParams := original.levelParams
    type := original.type
    value := Lean.mkConst ``{name} levels
  }}
  let some candidate := (← getEnv).find? `ReceiverProof.checked
    | throwError "WRAPPER_THEOREM_MISSING"
  unless (← liftTermElabM <| Lean.Meta.isDefEq original.type candidate.type) do
    throwError "SOURCE_STATEMENT_MISMATCH"
  logInfo "SOURCE_STATEMENT_MATCH"
"""
    forged = f"""import Lean
import {module}
theorem ReceiverProof.checked : True := True.intro
open Lean Elab Command
run_cmd do
  let some (.thmInfo original) := (← getEnv).find? ``{name}
    | throwError "ORIGINAL_THEOREM_MISSING"
  let some candidate := (← getEnv).find? `ReceiverProof.checked
    | throwError "WRAPPER_THEOREM_MISSING"
  unless (← liftTermElabM <| Lean.Meta.isDefEq original.type candidate.type) do
    throwError "SOURCE_STATEMENT_MISMATCH"
  logInfo "SOURCE_STATEMENT_MATCH"
"""
    (WORK/"CurrentHonest.lean").write_text(honest)
    (WORK/"CurrentForged.lean").write_text(forged)
    (WORK/"CurrentForgedValid.lean").write_text(
        f"import {module}\n\ntheorem ReceiverProof.checked : True := True.intro\n")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--policy",type=Path,required=True)
    ap.add_argument("--policy-sha256",required=True)
    ap.add_argument("--observed-head",required=True)
    args=ap.parse_args()
    WORK.mkdir(parents=True,exist_ok=True)
    OUT.mkdir(parents=True,exist_ok=True)
    result={"schema":"realitygraph.native-current-mathlib-replay.v1",
            "status":"UNKNOWN","failure":None,"observed_head":args.observed_head,
            "timestamp_utc":datetime.now(timezone.utc).isoformat(),
            "policy_sha256":args.policy_sha256,"source_repo":REPO,
            "source_branch":BRANCH,"theorems":{},"steps":STEPS,
            "cross_revision_meaning":"NOT_PROVED",
            "outside_owner_operator":"NO",
            "independent_second_kernel":"NOT_RUN",
            "publisher_signature":"NOT_VERIFIED"}
    try:
        policy=policy_from_bytes(args.policy.read_bytes(),args.policy_sha256)
        if policy["source"]["repository"]!=REPO or not SHA.fullmatch(args.observed_head):
            raise Refused("UPSTREAM_POLICY_OR_HEAD_UNAUTHORIZED")
        if github_head()!=args.observed_head:
            raise Refused("HEAD_MOVED_BEFORE_NATIVE_REPLAY")
        (WORK/"lean-toolchain").write_text("leanprover/lean4:v4.35.0\n")
        (WORK/"lakefile.toml").write_text(
            'name = "realitygraph_current_mathlib"\nversion = "0.1.0"\n'
            '[[require]]\nname = "mathlib"\n'
            'git = "https://github.com/leanprover-community/mathlib4.git"\n'
            f'rev = "{args.observed_head}"\n')
        step("lean_version",["lean","--version"],
             marker=policy["source"]["lean_version"])
        step("mathlib_update",["lake","update"])
        checkout=WORK/".lake"/"packages"/"mathlib"
        got=step("mathlib_sha",["git","rev-parse","HEAD"],cwd=checkout)
        if got.strip().splitlines()[-1]!=args.observed_head:
            raise Refused("MATHLIB_CHECKOUT_REVISION_MISMATCH")
        if (checkout/"lean-toolchain").read_text().strip()!="leanprover/lean4:v4.35.0":
            raise Refused("UPSTREAM_TOOLCHAIN_CHANGED")
        for item in policy["receipts"]:
            source=(checkout/item["file"]).read_bytes()
            if git_blob(source)!=item["git_blob"]:
                raise Refused("SOURCE_FILE_CHANGED_"+item["id"])
            name=source_declaration(source)
            generate(item["module"],name)
            label=item["id"].replace(".","_")
            step(label+"_cache",["lake","exe","cache","get",item["module"]])
            step(label+"_module",["lake","build",item["module"]])
            step(label+"_native",["lake","env","lean","CurrentHonest.lean"],
                 marker="SOURCE_STATEMENT_MATCH",timeout=200)
            step(label+"_forgery_valid",["lake","env","lean","CurrentForgedValid.lean"],
                 timeout=200)
            step(label+"_misattribution",["lake","env","lean","CurrentForged.lean"],
                 expected_code=1,marker="SOURCE_STATEMENT_MISMATCH",timeout=200)
            result["theorems"][item["id"]]={
                "original":name,"git_blob":item["git_blob"],
                "native":"CHECKED_AT_EXACT_OBSERVED_HEAD",
                "false_attribution":"REJECTED"}
        if github_head()!=args.observed_head:
            raise Refused("HEAD_MOVED_DURING_REPLAY")
        result["status"]="WARRANTED_BOUNDED_RECEIVER_NATIVE_AT_OBSERVED_HEAD"
    except (Refused,OSError,ValueError,KeyError,TypeError) as ex:
        result["failure"]=ex.reason if isinstance(ex,Refused) else "NATIVE_INFRA_FAILURE"
    (OUT/"report.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("RESULT",json.dumps({"status":result["status"],"head":result["observed_head"],
                               "claims":list(result["theorems"]),"failure":result["failure"]}),
          flush=True)
    return 0 if result["status"]=="WARRANTED_BOUNDED_RECEIVER_NATIVE_AT_OBSERVED_HEAD" else 1

if __name__=="__main__":
    raise SystemExit(main())
