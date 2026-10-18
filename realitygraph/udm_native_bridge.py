"""Evidence-scoped bridge from real UDM attrs observation to finite CLC/FLASH.

The exact native artifact is the evidence authority. This adapter does not
verify the original Python execution or license transfer to a new repository.
"""
from __future__ import annotations
from .capability import FiniteCapability
from .clc_lean import canonical_transport

ATTRS_SOURCE="6851ab593cd25f3c14393e9355d57d22bec2a074"
ATTRS_AUTHOR_HEAD="2e082f1c1efb019885fbdb601b32f8464dbe5d47"
ARTIFACT_SHA256="b03bb1c284f91d88b77cd2644b646432d01ea0da2b212e70723dbfeca8252c2c"
REPAIR_SHA256="ebef4d0aebed93ec80e98ad1b50fcd79528d235f93fa3904e4bb79b9fdd1e03f"
OBSERVATION_CLASS="obs-class:571b5338c5cfb47b05d4"
VECTOR=(False,False,False,False,True)
AUTH="attrs:6851ab593cd25f3c14393e9355d57d22bec2a074:author-test:2e082f1c1efb019885fbdb601b32f8464dbe5d47"
VERIFIER="pytest-attrs-native-artifact-12124688134"


def attrs_observation_capability(native_result: dict):
    """Require exact frozen evidence and reject extrapolated applicability."""
    if (native_result.get("schema") != "UDM_ATTRS_RESIDUAL_OBSERVATION_GENESIS_V1_RESULT"
        or native_result.get("status") != "WARRANTED_BOUNDED_REAL_SOURCE_RESIDUAL_TO_OBSERVATION_TO_REPAIR"
        or native_result.get("source_base") != ATTRS_SOURCE
        or native_result.get("author_head") != ATTRS_AUTHOR_HEAD
        or native_result.get("case_count") != 5
        or native_result.get("failing_case_indices") != [4]
        or native_result.get("causal_withdrawal") is not True
        or native_result.get("restoration") is not True
        or native_result.get("G2") != "UNKNOWN"
        or native_result.get("future_source") != "UNOPENED"):
        raise ValueError("native observation result not admissible")
    observations = native_result.get("observation_classes")
    selected = native_result.get("selected_observation")
    if (not isinstance(observations,list) or len(observations)!=1
        or observations[0].get("class_id")!=OBSERVATION_CLASS
        or tuple(observations[0].get("projection_vector",()))!=VECTOR
        or selected.get("repair_sha256")!=REPAIR_SHA256
        or selected.get("class_id")!=OBSERVATION_CLASS
        or selected.get("selected_attribute")!=observations[0].get("representative")
        or native_result.get("candidate_observation_count")!=1):
        raise ValueError("native observation witness changed")
    cap=FiniteCapability(
        "udm-attrs-observation-v1","AttrsObservedCaseV1","BooleanObservationV1",
        tuple((f"case:{i}",str(v).lower()) for i,v in enumerate(VECTOR)),
        tuple(f"case:{i}" for i in range(5)), "attrs-native-repair:"+REPAIR_SHA256,
        (),AUTH,VERIFIER,
        ("attrs-source:"+ATTRS_SOURCE,"native-artifact-sha256:"+ARTIFACT_SHA256,
         "observation:"+OBSERVATION_CLASS), 1)
    return cap, canonical_transport(cap)


def require_applicability(cap:FiniteCapability, *, source_authority:str,
                          case_id:str):
    if cap.authority_snapshot != AUTH or source_authority != ATTRS_SOURCE:
        raise ValueError("external applicability not established")
    if case_id not in cap.guarded_inputs:
        raise ValueError("case outside finite native observation carrier")
    return cap.execute(case_id)
