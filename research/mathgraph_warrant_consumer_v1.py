"""Independent, conservative consumer of one source-pinned MathGraph warrant graph.

This module deliberately imports no MathGraph implementation. It independently
reconstructs a strictly typed AND/OR warrant fixpoint from published edges.
The original JPL finite-result qualification is an explicit external premise,
not independently rerun Lean or a general real-world correctness guarantee.

Only the immutable research snapshot listed here is admitted. Neither an
embedded self-hash nor a digital signature can authorize a new trust root.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any

PRODUCER_COMMIT = "040456fc8862c79c8b384ce63846628274b678be"
PRODUCER_PATH = "evidence/living_warrant_openai_jpl_20261010.json"
PRODUCER_SHA256 = "0a850b112cce200f2fa97f0d861db712f3752712a6326e62f4c0d56996a95d87"
SNAPSHOT_SHA256 = "b95297a081d513fb0ec145a776cc997eaed18109d6b2af39fa8e61f6d637af41"
SCHEMA = "mathgraph.living-warrant-snapshot.v1"
RECORD_ID = "mg-living-warrant-openai-jpl-20261010"

OPENAI_COMMIT = "fd4aeeb2ee4fc729c18d98444fed42fd0529eeeb"
OPENAI_HISTORY_SHA256 = "41c2a2d470014b3628695c7aabf5fd0c93f6f687621fca172062f22b59ed6a1e"
OPENAI_HISTORY_GIT_BLOB = "693874f398905b1bc59e01b898b223ae9956bfc2"
PUBLISHER_TITLES = (
    "Algebraicity of Weil classes on split abelian eightfolds",
    "Algebraicity of Kuga–Satake Correspondences for K3 Surfaces",
    "The rational Hodge conjecture for products of K3 surfaces",
)

JPL_RECEIPT = "mathgraph.l4yaml.48-case-qualification"
JPL_CLAIM = "jpl.l4yaml.finite_parser_acceptance"
JPL_PINNED_RECORD_ID = "mg-l4yaml-source-check-20261010"
JPL_PINNED_RECORD_SHA256 = "f0d092974d5d710fe9e17fb6759a894f2c28f2d3f5456439c071bd0a71c8d3cb"
JPL_SCOPE = (
    "nasa-jpl/L4YAML@62bf7077910e888a0bc8adfc8e08a5f500ff3ca3:"
    "yaml/yaml-test-suite@da267a5c4782e7361e82889e76c0dc7df0e1e870:48-cases"
)
SUPPORTED_KINDS = frozenset(("documentary", "formal"))
MAX_BYTES = 131072


class InvalidWarrant(ValueError):
    """An unsupported, changed, unauthenticated or overclaimed warrant."""


def _reject(reason: str) -> None:
    raise InvalidWarrant(reason)


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def read_strict_json(raw: bytes) -> dict:
    if not isinstance(raw, bytes) or len(raw) > MAX_BYTES:
        _reject("INVALID_RECORD_SIZE")

    def unique(pairs: list[tuple[str, Any]]) -> dict:
        result: dict = {}
        for k, v in pairs:
            if k in result:
                _reject("DUPLICATE_JSON_KEY")
            result[k] = v
        return result

    try:
        obj = json.loads(raw.decode("utf-8"), object_pairs_hook=unique,
                         parse_constant=lambda x: _reject("INVALID_JSON_CONSTANT"))
    except (ValueError, UnicodeError) as exc:
        raise InvalidWarrant("INVALID_JSON_ENCODING") from exc
    if type(obj) is not dict or canonical(obj) + b"\n" != raw:
        _reject("NONCANONICAL_RECORD")
    return obj


def _object_hash(obj: dict) -> str:
    return hashlib.sha256(canonical(obj)).hexdigest()


def _source_valid(history_bytes: bytes, manifest: dict) -> tuple[str, ...]:
    if hashlib.sha256(history_bytes).hexdigest() != OPENAI_HISTORY_SHA256:
        _reject("OPENAI_SOURCE_SHA256_MISMATCH")
    git_blob = hashlib.sha1(
        b"blob " + str(len(history_bytes)).encode("ascii") + b"\0" + history_bytes
    ).hexdigest()
    if git_blob != OPENAI_HISTORY_GIT_BLOB:
        _reject("OPENAI_SOURCE_GIT_BLOB_MISMATCH")
    source = manifest.get("sources", {}).get("openai", {})
    if not isinstance(source, dict) or (
        source.get("commit") != OPENAI_COMMIT
        or source.get("git_blob_sha1") != git_blob
        or source.get("byte_sha256") != OPENAI_HISTORY_SHA256
        or source.get("path") != "history.md"
        or source.get("notice_date") != "2026-10-07"
        or source.get("url") != (
            "https://github.com/openai/math/blob/" + OPENAI_COMMIT + "/history.md"
        )
    ):
        _reject("OPENAI_SOURCE_AUTHORITY_CHANGED")
    try:
        text = history_bytes.decode("utf-8")
    except UnicodeError as exc:
        raise InvalidWarrant("SOURCE_NOT_UTF8") from exc
    if text.count("## October 7, 2026") != 1:
        _reject("AMBIGUOUS_OPENAI_WITHDRAWAL")
    section = text.split("## October 7, 2026", 1)[1].split("\n## ", 1)[0]
    if ("**Withdrawals**" not in section or "**Fixes**" not in section
        or "sign error invalidates a stabilization-trace cancellation argument" not in section):
        _reject("WITHDRAWAL_REASON_NOT_GROUNDED")
    withdrawn = section.split("**Withdrawals**", 1)[1].split("**Fixes**", 1)[0]
    names = tuple(line.strip()[2:].strip() for line in withdrawn.splitlines()
                  if line.strip().startswith("- "))
    if names != PUBLISHER_TITLES:
        _reject("WITHDRAWAL_LIST_NOT_MATCHED")
    return names


def _typed_records(graph: dict, name: str) -> dict[str, dict]:
    items = graph.get(name)
    if not isinstance(items, list) or len(items) > 1000:
        _reject("MALFORMED_" + name.upper())
    result = {}
    for x in items:
        if (not isinstance(x, dict) or set(x) != {"id", "kind", "scope"}
            or any(not isinstance(x.get(k), str) or not x.get(k) for k in x)
            or x["kind"] not in SUPPORTED_KINDS
            or x["id"] in result):
            _reject("INVALID_OR_DUPLICATE_" + name.upper())
        result[x["id"]] = x
    return result


def _typed_routes(graph: dict, claims: dict[str, dict],
                  receipts: dict[str, dict]) -> list[dict]:
    source = graph.get("routes")
    if not isinstance(source, list) or len(source) > 1000:
        _reject("MALFORMED_ROUTES")
    routes: list[dict] = []
    seen: set[tuple] = set()
    for r in source:
        if not isinstance(r, dict) or set(r) != {"conclusion", "evidence", "premises"}:
            _reject("MALFORMED_ROUTE")
        target = r["conclusion"]
        ev, pre = r["evidence"], r["premises"]
        if (not isinstance(target, str) or target not in claims
            or not isinstance(ev, list) or not ev
            or not isinstance(pre, list)
            or any(not isinstance(x, str) for x in ev + pre)
            or len(ev) != len(set(ev)) or len(pre) != len(set(pre))):
            _reject("BAD_ROUTE_REFERENCES")
        if any(x not in receipts for x in ev) or any(x not in claims for x in pre):
            _reject("UNKNOWN_ROUTE_PREMISE_OR_EVIDENCE")
        if any((receipts[x]["scope"], receipts[x]["kind"]) !=
               (claims[target]["scope"], claims[target]["kind"]) for x in ev):
            _reject("UNPROVED_EVIDENCE_TRANSPORT")
        if any((claims[x]["scope"], claims[x]["kind"]) !=
               (claims[target]["scope"], claims[target]["kind"]) for x in pre):
            _reject("UNPROVED_PREMISE_TRANSPORT")
        key = (target, tuple(ev), tuple(pre))
        if key in seen:
            _reject("DUPLICATE_ROUTE")
        seen.add(key)
        routes.append(r)
    return routes


def independently_close(claims: dict[str, dict], routes: list[dict],
                        withdrawn: frozenset[str]) -> dict[str, str]:
    """Recompute the least justified fixpoint; cycles cannot invent authority."""
    supported = set()
    for _ in range(len(claims) + 1):
        fresh = {
            r["conclusion"] for r in routes
            if not any(ref in withdrawn for ref in r["evidence"])
            and all(dep in supported for dep in r["premises"])
        } - supported
        if not fresh:
            break
        supported.update(fresh)
    return {
        k: (("WARRANTED_BOUNDED" if claims[k]["kind"] == "formal"
             else "SOURCE_DOCUMENTED") if k in supported else "UNKNOWN")
        for k in sorted(claims)
    }


def reclose_from_bytes(manifest_raw: bytes, history_raw: bytes) -> dict:
    """Validate external pins before considering any published claimed verdict."""
    if hashlib.sha256(manifest_raw).hexdigest() != PRODUCER_SHA256:
        _reject("UNTRUSTED_PUBLICATION_BYTES")
    record = read_strict_json(manifest_raw)
    if record.get("schema") != SCHEMA or record.get("id") != RECORD_ID:
        _reject("UNSUPPORTED_PRODUCER_SNAPSHOT")
    declared = record.get("snapshot_sha256")
    content = {k: v for k, v in record.items() if k != "snapshot_sha256"}
    if declared != SNAPSHOT_SHA256 or _object_hash(content) != declared:
        _reject("INVALID_INNER_SNAPSHOT_HASH")

    names = _source_valid(history_raw, record)
    sources = record.get("sources", {})
    if (sources.get("jpl_record_id") != JPL_PINNED_RECORD_ID or
            sources.get("jpl_record_sha256") != JPL_PINNED_RECORD_SHA256):
        _reject("JPL_RECEIPT_PIN_MISMATCH")

    report = record.get("publisher_notice", {})
    if (report.get("kind") != "PUBLICATION_WITHDRAWAL"
        or report.get("cause_as_reported") != "sign_error_in_original_argument"
        or report.get("does_not_imply") != "mathematical_theorem_refuted"
        or not isinstance(report.get("documents"), list)
        or len(report["documents"]) != 3):
        _reject("PUBLISHER_NOTICE_OVERSOLD")

    graph = record.get("derivation", {})
    if not isinstance(graph, dict) or set(graph) != {
            "claims", "receipts", "routes", "withdrawn_evidence", "receipt_admission"}:
        _reject("MISSING_TYPED_DERIVATION")
    claims = _typed_records(graph, "claims")
    receipts = _typed_records(graph, "receipts")
    routes = _typed_routes(graph, claims, receipts)
    expected_claims: dict[str, tuple[str, str]] = {JPL_CLAIM: ("formal", JPL_SCOPE)}
    expected_receipts: dict[str, tuple[str, str]] = {JPL_RECEIPT: ("formal", JPL_SCOPE)}
    for i, title in enumerate(names, 1):
        scope = "openai/math:" + title + ":original-withdrawn-edition"
        expected_claims["openai.original_support.%d" % i] = ("documentary", scope)
        expected_claims["openai.theorem.%d" % i] = ("formal", scope)
        expected_receipts["openai.original_publication_receipt.%d" % i] = (
            "documentary", scope
        )
        paper = report["documents"][i - 1]
        if paper != {
            "name": title,
            "original_support_claim": "openai.original_support.%d" % i,
            "mathematical_truth": "UNKNOWN",
            "editorial_status": "WITHDRAWN_BY_PUBLISHER",
        }:
            _reject("UNSUPPORTED_PUBLICATION_INFERENCE")
    if {k: (v["kind"], v["scope"]) for k, v in claims.items()} != expected_claims:
        _reject("UNSUPPORTED_CLAIM_UNIVERSE")
    if {k: (v["kind"], v["scope"]) for k, v in receipts.items()} != expected_receipts:
        _reject("UNSUPPORTED_EVIDENCE_ROOT")
    if graph.get("receipt_admission") != {
        "documentary": "exact pinned OpenAI history notice",
        "formal": "exact pinned JPL finite parser receipt",
    }:
        _reject("UNSUPPORTED_RECEIPT_QUALIFICATION")

    withdrawn = graph["withdrawn_evidence"]
    expected_withdrawn = {
        "openai.original_publication_receipt.%d" % i for i in range(1, 4)
    }
    if not isinstance(withdrawn, list) or set(withdrawn) != expected_withdrawn:
        _reject("UNSUPPORTED_SOURCE_WITHDRAWAL")
    before = independently_close(claims, routes, frozenset())
    after = independently_close(claims, routes, frozenset(withdrawn))
    states = {}
    for k, initial in before.items():
        final = after[k]
        if initial != "UNKNOWN" and final == "UNKNOWN":
            final = "STALE"
        states[k] = {"before": initial, "after": final,
                     "changed": initial != final}
    if states != record.get("resolutions"):
        _reject("PUBLISHED_VERDICTS_DIVERGE_FROM_INDEPENDENT_REPLAY")
    if states[JPL_CLAIM] != {
            "before": "WARRANTED_BOUNDED", "after": "WARRANTED_BOUNDED",
            "changed": False}:
        _reject("JPL_PROTECTED_FUTURE_WAS_MUTATED")
    if any(states["openai.theorem.%d" % i]["after"] != "UNKNOWN"
           for i in range(1, 4)):
        _reject("WITHDRAWAL_PROMOTED_TO_FALSE_THEOREM")
    if any(states["openai.original_support.%d" % i]["after"] != "STALE"
           for i in range(1, 4)):
        _reject("WITHDRAWN_EVIDENCE_WAS_RETAINED")
    interpretation = record.get("interpretation", {})
    if (interpretation.get("runtime_status") !=
        "IMMUTABLE_HISTORICAL_SNAPSHOT_NOT_CONTINUOUSLY_MONITORED"):
        _reject("CURRENT_REQUALIFICATION_NOT_ESTABLISHED")

    return {"status": "WARRANTED_BOUNDED_CONSUMER_REPLAY",
            "snapshot_sha256": declared,
            "publisher": OPENAI_COMMIT,
            "jpl_record_sha256": JPL_PINNED_RECORD_SHA256,
            "checked_claims": len(claims),
            "stale_documentary_paths": 3,
            "unaffected_formal_controls": 1,
            "unknown_mathematical_truths": 3,
            "independent_states": states,
            "authority_limit": (
                "Independently replayed graph/provenance pins; prior JPL formal "
                "evidence is a pinned external premise, not rerun by this consumer"
            )}


def main() -> None:
    cli = argparse.ArgumentParser(description="Independent MathGraph evidence consumer")
    cli.add_argument("--snapshot", type=Path, required=True)
    cli.add_argument("--history", type=Path, required=True)
    args = cli.parse_args()
    result = reclose_from_bytes(args.snapshot.read_bytes(), args.history.read_bytes())
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
