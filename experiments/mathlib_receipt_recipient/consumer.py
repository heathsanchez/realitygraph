#!/usr/bin/env python3
"""Independent, offline recipient for two exact Mathlib source-bound receipts.

Replays *historical receipt admission*, NOT the Lean proof, live Mathlib state,
or MathGraph's Resolve v1 fixed historical publication. The producer's status
field is never used to decide admission; policy pins are supplied externally.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import zipfile

SCHEMA = "realitygraph.mathlib-source-recipient.v1"
REPORT_SCHEMA = "mathgraph.native-mathlib-source-identity-transfer.v1"
STEP_ORDER = (
    "version", "lake_update", "source_commit", "mathlib_module_cache",
    "native_module_build", "honest_source_proof", "valid_but_unbound_proof",
    "forged_source_binding",
)

class Refused(ValueError):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def insist(condition: bool, reason: str) -> None:
    if not condition:
        raise Refused(reason)


def h256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def strict_json(raw: bytes) -> dict:
    def pairs(seq):
        obj = {}
        for key, value in seq:
            insist(key not in obj, "DUPLICATE_JSON_KEY")
            obj[key] = value
        return obj
    def constant(_):
        raise Refused("NONFINITE_JSON_NUMBER")
    try:
        obj = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                         parse_constant=constant)
    except Refused:
        raise
    except (ValueError, UnicodeError, RecursionError):
        raise Refused("MALFORMED_JSON") from None
    insist(type(obj) is dict, "WRONG_JSON_ROOT")
    return obj


def fields(value: object, required: set[str]):
    insist(type(value) is dict and set(value) == required, "WRONG_FIELDS")


def source_declaration(source: bytes) -> str:
    """Independent limited lexical scan: first theorem/lemma under a namespace.

    The method is deliberately restricted; unsupported grammar fails closed.
    This is not Lean parsing or a human-language specification check.
    """
    try:
        lines = source.decode("utf-8").splitlines()
    except UnicodeError:
        raise Refused("SOURCE_ENCODING") from None
    namespaces = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("namespace "):
            namespace = stripped.removeprefix("namespace ").strip()
            insist(re.fullmatch(r"[A-Za-z_][\w.]*", namespace) is not None, "UNSUPPORTED_NAMESPACE")
            namespaces.extend(namespace.split("."))
        elif stripped == "end" or stripped.startswith("end "):
            if namespaces:
                namespaces.pop()
        else:
            match = re.match(r"(?:theorem|lemma)\s+([A-Za-z_][A-Za-z_0-9']*)\b", stripped)
            if match:
                insist(bool(namespaces), "UNSCOPED_DECLARATION")
                return ".".join((*namespaces, match.group(1)))
    raise Refused("SOURCE_THEOREM_NOT_FOUND")


def policy_from_bytes(raw: bytes, externally_trusted_sha256: str) -> dict:
    insist(len(externally_trusted_sha256) == 64 and h256(raw) == externally_trusted_sha256,
           "POLICY_NOT_AUTHORIZED")
    policy = strict_json(raw)
    fields(policy, {"schema", "producer", "source", "receipts"})
    insist(policy["schema"] == SCHEMA, "POLICY_VERSION")
    fields(policy["producer"], {"repository", "commit", "actions_run"})
    fields(policy["source"], {"repository", "commit", "lean_version", "lean_commit"})
    insist(policy["producer"]["repository"] == "metalogiclabs/mathgraph", "UNAUTHORIZED_PRODUCER")
    insist(policy["source"]["repository"] == "leanprover-community/mathlib4", "UNAUTHORIZED_SOURCE")
    insist(policy["source"]["lean_version"] == "4.35.0", "UNAUTHORIZED_TOOLCHAIN")
    insist(type(policy["receipts"]) is list and len(policy["receipts"]) == 2,
           "UNAUTHORIZED_RECEIPT_SET")
    names = set()
    for receipt in policy["receipts"]:
        fields(receipt, {"id", "module", "file", "git_blob", "archive_sha256", "artifact_id"})
        insist(type(receipt["id"]) is str and receipt["id"] not in names, "DUPLICATE_RECEIPT")
        names.add(receipt["id"])
        for key in ("git_blob", "archive_sha256"):
            size = 40 if key == "git_blob" else 64
            value = receipt[key]
            insist(type(value) is str and re.fullmatch("[0-9a-f]{" + str(size) + "}", value) is not None,
                   "INVALID_PIN")
        insist(receipt["file"] == receipt["module"].replace(".", "/") + ".lean",
               "SOURCE_MODULE_MISMATCH")
    return policy


def _expected_commands(module: str) -> dict[str, tuple[list[str], int, str | None]]:
    return {
        "version": (["lean", "--version"], 0, "4.35.0"),
        "lake_update": (["lake", "update"], 0, None),
        "source_commit": (["git", "rev-parse", "HEAD"], 0, None),
        "mathlib_module_cache": (["lake", "exe", "cache", "get", module], 0, None),
        "native_module_build": (["lake", "build", module], 0, "Build completed successfully"),
        "honest_source_proof": (["lake", "env", "lean", "SourceHonest.lean"], 0, "SOURCE_STATEMENT_MATCH"),
        "valid_but_unbound_proof": (["lake", "env", "lean", "ForgeryCompiles.lean"], 0, None),
        "forged_source_binding": (["lake", "env", "lean", "SourceForged.lean"], 1,
                                  "error: SOURCE_STATEMENT_MISMATCH"),
    }


def admit(archive: bytes, source: bytes, policy: dict, allowed: dict) -> dict:
    """Verify one exact historical artifact and independently pinned source bytes."""
    insist(len(archive) <= 256_000 and h256(archive) == allowed["archive_sha256"],
           "UNAUTHORIZED_ARTIFACT_BYTES")
    insist(len(source) <= 2_000_000 and git_blob(source) == allowed["git_blob"],
           "UNAUTHORIZED_SOURCE_BYTES")
    declared_name = source_declaration(source)
    expected_module = allowed["module"]
    expected = _expected_commands(expected_module)
    try:
        with zipfile.ZipFile(__import__("io").BytesIO(archive)) as packed:
            entries = packed.infolist()
            expected_names = {"report.json"} | {k + ".log" for k in STEP_ORDER}
            insist(len(entries) == len(expected_names) and {e.filename for e in entries} == expected_names,
                   "WRONG_ARCHIVE_MEMBERS")
            insist(all(e.file_size < 70_000 and not e.is_dir() for e in entries),
                   "UNSAFE_ARCHIVE_CONTENT")
            report = strict_json(packed.read("report.json"))
            fields(report, {"error", "exclusions", "experiment_scope", "schema", "selection",
                            "source", "source_under_test", "status", "steps"})
            insist(report["schema"] == REPORT_SCHEMA, "UNKNOWN_PRODUCER_FORMAT")
            # Deliberately DO NOT consult report['status']: it is a publisher assertion.
            insist(report["error"] is None, "PRODUCER_REPORTED_ERROR")
            insist(report["source_under_test"] == policy["producer"]["commit"],
                   "PRODUCER_REVISION_MISMATCH")
            fields(report["source"], {"repository", "expected_commit", "module", "file",
                                      "expected_git_blob"})
            insist(report["source"] == {"repository": policy["source"]["repository"],
                "expected_commit": policy["source"]["commit"], "module": expected_module,
                "file": allowed["file"], "expected_git_blob": allowed["git_blob"]},
                   "CLAIM_SOURCE_MISMATCH")
            fields(report["selection"], {"discovered_name", "mutated_git_blob",
                                           "selection_rule", "source_bytes_modified", "source_sha256"})
            selected = report["selection"]
            insist(selected["discovered_name"] == declared_name and
                   selected["source_sha256"] == h256(source) and
                   selected["source_bytes_modified"] is False and
                   selected["mutated_git_blob"] == git_blob(source + b"\n"),
                   "CLAIM_STATEMENT_MISMATCH")
            insist(type(report["steps"]) is list and len(report["steps"]) == len(STEP_ORDER),
                   "INCOMPLETE_EVIDENCE")
            for step, name in zip(report["steps"], STEP_ORDER):
                fields(step, {"argv", "code", "diagnostic", "diagnostic_present", "elapsed_seconds",
                              "expected_code", "label", "sha256"})
                cmd, code, marker = expected[name]
                insist(step["label"] == name and step["argv"] == cmd and
                       type(step["code"]) is int and step["code"] == code and
                       step["expected_code"] == code, "WRONG_VERIFIER_TRACE")
                logged = packed.read(name + ".log")
                insist(h256(logged) == step["sha256"], "LOG_HASH_MISMATCH")
                text = logged.decode("utf-8")
                insist(text.startswith("$ " + " ".join(cmd) + "\n"), "LOG_COMMAND_MISMATCH")
                content = text.split("\n", 1)[1]
                if name == "version":
                    insist(policy["source"]["lean_commit"] in content, "VERIFIER_VERSION_MISMATCH")
                if name == "source_commit":
                    insist(content.strip() == policy["source"]["commit"], "SOURCE_COMMIT_MISMATCH")
                if marker:
                    insist(marker in content, "MISSING_VERIFIER_DIAGNOSTIC")
                insist(("error:" not in content) if code == 0 else True, "UNEXPECTED_VERIFIER_ERROR")
    except (zipfile.BadZipFile, UnicodeError, ValueError, RuntimeError, KeyError) as e:
        if isinstance(e, Refused):
            raise
        raise Refused("MALFORMED_RECEIPT_ARCHIVE") from None
    return {"claim_id": allowed["id"], "original_declaration": declared_name,
            "historical": "WARRANTED_BOUNDED_SOURCE_RECEIPT", "verified_by_receiver":
            "INTEGRITY_AND_PINNED_LOG_REPLAY_ONLY", "current_upstream": "NOT_CHECKED"}


def replay(policy_raw: bytes, expected_policy_sha: str, archives: dict[str, bytes],
           sources: dict[str, bytes], *, simulate_withdrawn: frozenset[str] = frozenset(),
           supplied_current_source_commit: str | None = None) -> dict:
    policy = policy_from_bytes(policy_raw, expected_policy_sha)
    ids = {item["id"] for item in policy["receipts"]}
    insist(set(archives) == ids and set(sources) == ids, "MISSING_RECEIPT_INPUT")
    insist(simulate_withdrawn <= ids, "UNAUTHORIZED_WITHDRAWAL_TARGET")
    historical = {}
    for item in policy["receipts"]:
        historical[item["id"]] = admit(archives[item["id"]], sources[item["id"]], policy, item)
    claims = {}
    for key in sorted(ids):
        item = historical[key]
        # Distinguish actual historical evidence from recipient's simulated local policy.
        scoped = "STALE_SIMULATED_WITHDRAWAL" if key in simulate_withdrawn else "WARRANTED_BOUNDED_HISTORICAL"
        applicability = "NOT_CHECKED"
        if supplied_current_source_commit is not None:
            applicability = ("PIN_MATCH_ONLY_NOT_LIVE_FRESHNESS"
                             if supplied_current_source_commit == policy["source"]["commit"]
                             else "UNKNOWN_SOURCE_REVISION_CHANGED")
        claims[key] = {**item, "recipient_support": scoped,
                       "current_applicability": applicability}
    return {"schema": "realitygraph.mathlib-receipt-consumer-report.v1", "accepted_history": True,
            "policy_sha256": expected_policy_sha, "source_commit": policy["source"]["commit"],
            "claims": claims, "simulated_withdrawal": sorted(simulate_withdrawn),
            "actual_publisher_withdrawal": "NOT_CHECKED"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", type=Path, required=True)
    ap.add_argument("--policy-sha256", required=True)
    ap.add_argument("--artifacts", type=Path, required=True)
    ap.add_argument("--sources", type=Path, required=True)
    args = ap.parse_args()
    try:
        policy_bytes = args.policy.read_bytes()
        policy = policy_from_bytes(policy_bytes, args.policy_sha256)
        archives = {item["id"]: (args.artifacts / (item["id"] + ".zip")).read_bytes()
                    for item in policy["receipts"]}
        sources = {item["id"]: (args.sources / item["file"]).read_bytes()
                   for item in policy["receipts"]}
        print(json.dumps(replay(policy_bytes, args.policy_sha256, archives, sources),
                         sort_keys=True, separators=(",", ":")))
        return 0
    except (Refused, OSError) as exc:
        reason = exc.reason if isinstance(exc, Refused) else "MISSING_OR_UNREADABLE_INPUT"
        print(json.dumps({"accepted_history": False, "reason": reason}), file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())