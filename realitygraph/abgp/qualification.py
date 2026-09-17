from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from .analysis import analyze_matrix
from .manifest import load_analysis_plan, load_design_manifest
from .power import qualification_power_audit
from .qualification_fixtures import passing_qualification_matrix, qualification_fixtures
from .statistical_reference import run_statistical_reference_audit


_ROOT = Path(__file__).resolve().parents[2]
_DESIGN_PATH = _ROOT / "preregistration" / "abgp-design-manifest-v1.json"
_ANALYSIS_PATH = _ROOT / "preregistration" / "abgp-analysis-plan-v1.json"
_QUALIFICATION_SCHEMA = "realitygraph.abgp.qualification.v1"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(value: Any) -> str:
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _fixture_row(fixture: Any, base_matrix: dict[str, dict[str, Any]]) -> dict[str, Any]:
    matrix = deepcopy(base_matrix)
    matrix[fixture.arm] = deepcopy(fixture.raw_input)
    result = analyze_matrix(matrix)
    arm_result = result["arms"][fixture.arm]
    observed_reason_codes = tuple(arm_result.get("validity_reason_codes", ()))
    expected_reason_codes = tuple(fixture.expected_reason_codes)
    reason_match = (
        observed_reason_codes == expected_reason_codes
        if expected_reason_codes
        else not observed_reason_codes
    )
    observed_verdict = str(arm_result["verdict"])
    matched = observed_verdict == fixture.expected_verdict and reason_match
    return {
        "fixture_id": fixture.fixture_id,
        "arm": fixture.arm,
        "fixture_class": fixture.fixture_class,
        "namespace": fixture.namespace,
        "expected_verdict": fixture.expected_verdict,
        "observed_verdict": observed_verdict,
        "expected_reason_codes": list(expected_reason_codes),
        "observed_reason_codes": list(observed_reason_codes),
        "matched_expectation": matched,
        "raw_input_digest": _digest(fixture.raw_input),
        "witness_digest": _digest(fixture.witness),
        "arm_raw_pvalue": arm_result.get("raw_pvalue"),
        "arm_effect": arm_result.get("effect"),
        "arm_analysis_mode": arm_result.get("analysis_mode"),
    }


def run_qualification() -> dict[str, Any]:
    """Run deterministic DEV/QUAL-only methodological qualification.

    This function never derives, inspects, or executes the confirmatory namespace.
    It exercises frozen qualification fixtures through the same scientific analysis
    path, then requires independent statistical-reference and power audits to pass.
    """

    design = load_design_manifest(_DESIGN_PATH)
    analysis = load_analysis_plan(_ANALYSIS_PATH)
    if design.status != "REVIEW_PENDING" or design.confirmatory_execution_enabled:
        raise ValueError("qualification requires the non-executable REVIEW_PENDING design")

    base_matrix = passing_qualification_matrix()
    rows = [_fixture_row(fixture, base_matrix) for fixture in qualification_fixtures()]
    reference_audit = run_statistical_reference_audit()
    power_audit = qualification_power_audit(analysis)

    fixtures_match = all(row["matched_expectation"] for row in rows)
    namespaces_safe = all(
        row["namespace"].startswith(("ABGP-DEV-", "ABGP-QUAL-"))
        and "ABGP-CONFIRM" not in row["namespace"]
        for row in rows
    )
    qualified = (
        fixtures_match
        and namespaces_safe
        and reference_audit.get("status") == "PASS"
        and bool(power_audit.get("qualified"))
    )

    class_counts: dict[str, int] = {}
    for row in rows:
        class_counts[row["fixture_class"]] = class_counts.get(row["fixture_class"], 0) + 1

    artifact: dict[str, Any] = {
        "schema": _QUALIFICATION_SCHEMA,
        "mode": "QUALIFICATION_ONLY",
        "verdict": "QUALIFIED" if qualified else "NOT_QUALIFIED",
        "confirmatory_namespace_used": False,
        "design_status": design.status,
        "confirmatory_execution_enabled": design.confirmatory_execution_enabled,
        "design_manifest_digest": design.digest,
        "analysis_plan_digest": analysis.digest,
        "fixture_count": len(rows),
        "fixture_class_counts": dict(sorted(class_counts.items())),
        "fixtures": rows,
        "statistical_reference_audit": reference_audit,
        "power_audit": power_audit,
        "safety": {
            "qualification_namespaces_only": namespaces_safe,
            "confirmatory_namespace_accessed": False,
            "all_fixture_expectations_matched": fixtures_match,
        },
        "scientific_interpretation": "METHODOLOGICAL_QUALIFICATION_ONLY_NOT_CONFIRMATORY_ABGP_EVIDENCE",
    }
    artifact["qualification_digest"] = _digest(artifact)
    return json.loads(_canonical_json(artifact))


def write_qualification_artifact(path: str | Path, artifact: dict[str, Any]) -> None:
    target = Path(path)
    target.write_text(_canonical_json(artifact) + "\n", encoding="utf-8")
