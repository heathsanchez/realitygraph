#!/usr/bin/env python3
"""Current GitHub source observation after historical Mathlib receipt admission.

Authority separation:
- Historical proof receipts are admitted independently by consumer.py.
- This module obtains the CURRENT default-branch tip directly from GitHub HTTPS
  repository and branch APIs, then fetches each source file by that exact tip.
- Matching a single source file is not a current Lean proof recheck and does not
  cover transitive dependencies, toolchain changes or publisher notices.
- An absent/changed file is a requalification obligation, not theorem refutation.
- GitHub API TLS and namespace trust are not a publisher cryptographic signature.
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

from consumer import Refused, insist, policy_from_bytes, replay, git_blob

BASE = "https://api.github.com"
ALLOWED_REPO = "leanprover-community/mathlib4"
ALLOWED_BRANCH = "master"
OUTPUT_SCHEMA = "realitygraph.mathlib-current-source-observation.v1"
SHA = re.compile(r"^[0-9a-f]{40}$")


def fail(reason: str) -> None:
    raise Refused(reason)


def inspect_observation(historical: dict, policy: dict, *, observed_commit: str,
                        observations: dict[str, dict], repo_default_branch: str,
                        branch_name: str, observation_channel: str) -> dict:
    """Pure recipient decision, reusable for adversarial tests, no network."""
    insist(historical.get("accepted_history") is True, "HISTORIC_ADMISSION_REQUIRED")
    insist(historical.get("source_commit") == policy["source"]["commit"],
           "HISTORIC_SOURCE_PIN_MISMATCH")
    insist(policy["source"]["repository"] == ALLOWED_REPO and
           repo_default_branch == ALLOWED_BRANCH and branch_name == ALLOWED_BRANCH,
           "UPSTREAM_BRANCH_NOT_AUTHORIZED")
    insist(type(observed_commit) is str and SHA.fullmatch(observed_commit) is not None,
           "INVALID_OBSERVED_HEAD")
    insist(observation_channel == "github-repository-https-api-at-sha",
           "UNAUTHORIZED_OBSERVATION_CHANNEL")
    ids = {item["id"] for item in policy["receipts"]}
    insist(set(observations) == ids and set(historical["claims"]) == ids,
           "SOURCE_RECEIPT_SET_CHANGED")
    result = {}
    for item in policy["receipts"]:
        rid = item["id"]
        obs = observations[rid]
        insist(type(obs) is dict and set(obs) == {"status", "commit", "path", "blob_sha"},
               "UNSUPPORTED_SOURCE_OBSERVATION")
        insist(obs["commit"] == observed_commit and obs["path"] == item["file"],
               "CURRENT_OBSERVATION_SCOPE_MISMATCH")
        insist(historical["claims"][rid]["recipient_support"] ==
               "WARRANTED_BOUNDED_HISTORICAL", "HISTORIC_SUPPORT_NOT_WARRANTED")
        if obs["status"] == "present":
            insist(type(obs["blob_sha"]) is str and
                   SHA.fullmatch(obs["blob_sha"]) is not None,
                   "INVALID_CURRENT_SOURCE_BLOB")
            exact = obs["blob_sha"] == item["git_blob"]
            verdict = ("SOURCE_FILE_UNCHANGED_AT_OBSERVED_HEAD" if exact else
                       "SOURCE_FILE_CHANGED_REQUALIFICATION_REQUIRED")
        elif obs["status"] == "missing":
            insist(obs["blob_sha"] is None, "MISSING_FILE_HAS_BLOB")
            verdict = "SOURCE_PATH_MISSING_REQUALIFICATION_REQUIRED"
        else:
            fail("UNKNOWN_SOURCE_OBSERVATION_STATUS")
        result[rid] = {
            "historical_support": "WARRANTED_BOUNDED_HISTORICAL",
            "current_file_observation": verdict,
            "current_proof_warrant": "UNKNOWN_DEPENDENCY_CLOSURE_NOT_RECHECKED",
            "publisher_withdrawal": "NOT_CHECKED",
            "original_git_blob": item["git_blob"],
            "observed_git_blob": obs["blob_sha"],
            "observed_source_path": item["file"],
        }
    return {
        "schema": OUTPUT_SCHEMA,
        "observation_authority": "GitHub HTTPS repo and branch APIs, not producer claim",
        "publisher_signature_authority": "NOT_ESTABLISHED",
        "source_repository": ALLOWED_REPO,
        "default_branch": ALLOWED_BRANCH,
        "observed_head": observed_commit,
        "historical_source_commit": policy["source"]["commit"],
        "historical_admission": True,
        "observed_source_files": result,
        "dependency_closure": "NOT_REPLAYED_AT_CURRENT_HEAD",
        "publisher_withdrawal": "NOT_CHECKED",
    }


def api_get_json(url: str, token: str | None, *, allow_missing: bool = False) -> dict | None:
    insist(url.startswith(BASE + "/repos/" + ALLOWED_REPO + "/"),
           "UNTRUSTED_API_ENDPOINT")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "realitygraph-current-source-recipient",
    }
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            final_url = response.geturl()
            insist(final_url.startswith(BASE + "/repos/" + ALLOWED_REPO + "/"),
                   "UNTRUSTED_API_REDIRECT")
            raw = response.read(300000)
    except urllib.error.HTTPError as error:
        if allow_missing and error.code == 404:
            return None
        fail("GITHUB_LIVE_API_UNAVAILABLE_" + str(error.code))
    except (urllib.error.URLError, TimeoutError):
        fail("GITHUB_LIVE_API_UNAVAILABLE")
    try:
        body = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError):
        fail("MALFORMED_LIVE_API_RESPONSE")
    insist(type(body) is dict, "MALFORMED_LIVE_API_RESPONSE")
    return body


def observe_live(policy: dict, *, token: str | None) -> tuple[dict, dict]:
    repo = api_get_json(BASE + "/repos/" + ALLOWED_REPO, token)
    insist(repo.get("full_name") == ALLOWED_REPO and
           repo.get("default_branch") == ALLOWED_BRANCH and
           repo.get("private") is False, "UPSTREAM_REPO_IDENTITY_MISMATCH")
    branch_url = BASE + "/repos/" + ALLOWED_REPO + "/branches/" + ALLOWED_BRANCH
    branch = api_get_json(branch_url, token)
    tip = (branch.get("commit") or {}).get("sha")
    insist(branch.get("name") == ALLOWED_BRANCH and
           type(tip) is str and SHA.fullmatch(tip) is not None,
           "UPSTREAM_BRANCH_IDENTITY_MISMATCH")
    observations = {}
    audit = {"github_repository": ALLOWED_REPO, "branch": ALLOWED_BRANCH,
             "tip_sha": tip, "files": {}}
    for item in policy["receipts"]:
        file_url = (BASE + "/repos/" + ALLOWED_REPO + "/contents/" +
                    urllib.parse.quote(item["file"], safe="/") +
                    "?ref=" + urllib.parse.quote(tip, safe=""))
        response = api_get_json(file_url, token, allow_missing=True)
        if response is None:
            observations[item["id"]] = {
                "status": "missing", "commit": tip,
                "path": item["file"], "blob_sha": None,
            }
            audit["files"][item["id"]] = {"status": "missing", "blob_sha": None}
            continue
        insist(response.get("type") == "file" and
               response.get("path") == item["file"] and
               response.get("encoding") == "base64", "SOURCE_CONTENT_API_MISMATCH")
        payload = response.get("content")
        insist(type(payload) is str, "SOURCE_CONTENT_API_MISMATCH")
        try:
            decoded = base64.b64decode("".join(payload.split()), validate=True)
        except (ValueError, Exception) as err:
            # Never classify a transport decoding failure as source withdrawal.
            fail("SOURCE_CONTENT_DECODE_FAILURE")
        reported_blob = response.get("sha")
        insist(type(reported_blob) is str and
               SHA.fullmatch(reported_blob) is not None and
               reported_blob == git_blob(decoded) and
               response.get("size") == len(decoded),
               "CURRENT_GITHUB_CONTENT_HASH_MISMATCH")
        observations[item["id"]] = {
            "status": "present", "commit": tip,
            "path": item["file"], "blob_sha": reported_blob,
        }
        audit["files"][item["id"]] = {
            "status": "present",
            "blob_sha": reported_blob,
            "sha256": hashlib.sha256(decoded).hexdigest(),
            "source_bytes": len(decoded),
        }
    # Prevent attaching a file snapshot to a branch that moved while reading.
    second = api_get_json(branch_url, token)
    if (second.get("commit") or {}).get("sha") != tip:
        fail("UPSTREAM_BRANCH_MOVED_DURING_OBSERVATION")
    return {
        "commit": tip, "observations": observations,
        "repo_default_branch": repo["default_branch"],
        "branch_name": branch["name"],
    }, audit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--policy-sha256", required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report: dict = {
        "schema": OUTPUT_SCHEMA, "historical_admission": False,
        "live_status": "UNKNOWN", "failure": None,
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "dependency_closure": "NOT_REPLAYED_AT_CURRENT_HEAD",
        "publisher_withdrawal": "NOT_CHECKED",
    }
    try:
        policy_raw = args.policy.read_bytes()
        policy = policy_from_bytes(policy_raw, args.policy_sha256)
        archives = {
            item["id"]: (args.artifacts / (item["id"] + ".zip")).read_bytes()
            for item in policy["receipts"]
        }
        originals = {
            item["id"]: (args.sources / item["file"]).read_bytes()
            for item in policy["receipts"]
        }
        historical = replay(policy_raw, args.policy_sha256, archives, originals)
        live, audit = observe_live(policy, token=os.getenv("GH_TOKEN"))
        assessment = inspect_observation(
            historical, policy, observed_commit=live["commit"],
            observations=live["observations"],
            repo_default_branch=live["repo_default_branch"],
            branch_name=live["branch_name"],
            observation_channel="github-repository-https-api-at-sha",
        )
        report.update(assessment)
        report["live_status"] = "OBSERVED_SOURCE_FILES_ONLY"
        report["fetched_git_blobs"] = audit
        report["observed_at_utc"] = datetime.now(timezone.utc).isoformat()
        report["policy_sha256"] = args.policy_sha256
    except (Refused, OSError, TypeError, KeyError, ValueError) as error:
        report["failure"] = error.reason if isinstance(error, Refused) else "LIVE_OBSERVATION_INFRA_FAILURE"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"live_status": report["live_status"],
                      "failure": report["failure"],
                      "head": report.get("observed_head"),
                      "results": {k:v["current_file_observation"] for k,v in
                                  report.get("observed_source_files", {}).items()}},
                     sort_keys=True), flush=True)
    return 0 if report["live_status"] == "OBSERVED_SOURCE_FILES_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
