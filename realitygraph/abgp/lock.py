from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

from .manifest import ABGPAnalysisPlan, ABGPDesign, load_analysis_plan, load_design_manifest


_ROOT = Path(__file__).resolve().parents[2]
_DESIGN_PATH = _ROOT / "preregistration" / "abgp-design-manifest-v1.json"
_ANALYSIS_PATH = _ROOT / "preregistration" / "abgp-analysis-plan-v1.json"

_ARM_PATHS = {
    "A": "realitygraph/abgp/arm_a.py",
    "B": "realitygraph/abgp/arm_b.py",
    "G": "realitygraph/abgp/arm_g.py",
    "P": "realitygraph/abgp/arm_p.py",
}


def _canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha_text(value: str | bytes) -> str:
    payload = value if isinstance(value, bytes) else value.encode("utf-8")
    return sha256(payload).hexdigest()


def _lock_digest(lock_without_digest: Mapping[str, Any]) -> str:
    return sha256(_canonical_json(lock_without_digest).encode("utf-8")).hexdigest()


def build_review_lock(
    repo_file_map: Mapping[str, str | bytes],
    runtime_metadata: Mapping[str, Any],
) -> dict[str, Any]:
    """Construct a review-only lock candidate.

    This function deliberately cannot freeze or enable confirmation.  A future,
    separately reviewed step must create any FROZEN lock from the reviewed candidate.
    """

    design = load_design_manifest(_DESIGN_PATH)
    analysis = load_analysis_plan(_ANALYSIS_PATH)

    missing_arm_files = [path for path in _ARM_PATHS.values() if path not in repo_file_map]
    if missing_arm_files:
        raise ValueError(f"missing arm generator files: {missing_arm_files}")
    if "realitygraph/abgp/analysis.py" not in repo_file_map:
        raise ValueError("missing frozen analysis implementation")

    scientific_code_hashes = {
        path: _sha_text(repo_file_map[path]) for path in sorted(repo_file_map)
    }
    arm_generator_code_hashes = {
        arm: scientific_code_hashes[path] for arm, path in _ARM_PATHS.items()
    }

    required_runtime = {
        field
        for field in design.raw["final_lock_requirements"]
        if field
        not in {
            "design_manifest_digest",
            "analysis_plan_digest",
            "arm_generator_code_hashes",
            "analysis_implementation_hash",
        }
    }
    missing_runtime = sorted(field for field in required_runtime if field not in runtime_metadata)
    if missing_runtime:
        raise ValueError(f"missing final-lock runtime metadata: {missing_runtime}")

    lock: dict[str, Any] = {
        "schema": "realitygraph.abgp.final-lock-review.v1",
        "status": "REVIEW_PENDING",
        "confirmatory_execution_enabled": False,
        "design_version": design.design_version,
        "design_manifest_digest": design.digest,
        "analysis_plan_digest": analysis.digest,
        "scientific_code_hashes": scientific_code_hashes,
        "arm_generator_code_hashes": arm_generator_code_hashes,
        "analysis_implementation_hash": scientific_code_hashes[
            "realitygraph/abgp/analysis.py"
        ],
    }
    for field in sorted(required_runtime):
        lock[field] = runtime_metadata[field]

    # Make the builder's safety property explicit in the serialized object itself.
    lock["review_only"] = True
    lock["builder_can_freeze"] = False
    lock["lock_digest"] = _lock_digest(lock)
    return lock


def validate_final_lock(
    lock: Mapping[str, Any],
    design: ABGPDesign,
    analysis: ABGPAnalysisPlan,
    *,
    expected_tree_hash: str | None = None,
) -> None:
    """Validate a separately produced frozen lock.

    Validation is intentionally separate from construction: this module can inspect a
    future FROZEN lock but build_review_lock itself never creates one.
    """

    if lock.get("status") != "FROZEN":
        raise ValueError("final lock is not FROZEN")
    if lock.get("confirmatory_execution_enabled") is not True:
        raise ValueError("frozen final lock does not enable confirmatory execution")
    if lock.get("design_manifest_digest") != design.digest:
        raise ValueError("final lock design-manifest digest mismatch")
    if lock.get("analysis_plan_digest") != analysis.digest:
        raise ValueError("final lock analysis-plan digest mismatch")

    for field in design.raw["final_lock_requirements"]:
        if field not in lock or lock[field] in (None, "", {}, []):
            raise ValueError(f"final lock missing required field: {field}")

    if expected_tree_hash is not None and lock.get("repository_tree_hash") != expected_tree_hash:
        raise ValueError("final lock repository tree mismatch")

    arm_hashes = lock.get("arm_generator_code_hashes")
    if not isinstance(arm_hashes, Mapping) or set(arm_hashes) != {"A", "B", "G", "P"}:
        raise ValueError("final lock arm-generator hashes are incomplete")

    scientific = lock.get("scientific_code_hashes")
    if not isinstance(scientific, Mapping) or not scientific:
        raise ValueError("final lock scientific-code hash map is missing")
    if lock.get("analysis_implementation_hash") != scientific.get(
        "realitygraph/abgp/analysis.py"
    ):
        raise ValueError("final lock analysis hash is not bound to scientific code map")

    namespace = lock.get("confirmatory_namespace_identifier")
    if namespace != design.confirmatory_namespace:
        raise ValueError("final lock confirmatory namespace mismatch")

    supplied_digest = lock.get("lock_digest")
    if not isinstance(supplied_digest, str) or len(supplied_digest) != 64:
        raise ValueError("final lock digest is missing or malformed")
    material = dict(lock)
    del material["lock_digest"]
    if _lock_digest(material) != supplied_digest:
        raise ValueError("final lock digest does not match its contents")
