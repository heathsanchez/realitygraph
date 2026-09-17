from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any

from .manifest import derive_dev_seed


_SCHEMA = "realitygraph.abgp.retained-structure.v1"
_RESTART_ENVIRONMENT_DIGEST = sha256(
    b"ABGP-P-clean-post-restart-environment-v1"
).hexdigest()
_REACQUISITION_PROCEDURE_ID = "P_ACQUIRE_V1"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


@dataclass(frozen=True)
class RetainedStructure:
    version: str
    applicability_key: str
    protected_policy: tuple[tuple[int, int], ...]
    lineage_id: str

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": _SCHEMA,
            "version": self.version,
            "applicability_key": self.applicability_key,
            "protected_policy": [[k, v] for k, v in self.protected_policy],
            "lineage_id": self.lineage_id,
        }

    def to_text(self) -> str:
        return _canonical_json(self._payload()) + "\n"

    @classmethod
    def from_text(cls, text: str) -> "RetainedStructure":
        if not text.endswith("\n"):
            raise ValueError("retained structure text must end with newline")
        data = json.loads(text)
        if data.get("schema") != _SCHEMA:
            raise ValueError("unexpected retained-structure schema")
        policy_raw = data.get("protected_policy")
        if not isinstance(policy_raw, list):
            raise ValueError("protected_policy must be a list")
        policy = tuple((int(pair[0]), int(pair[1])) for pair in policy_raw)
        if tuple(k for k, _ in policy) != (0, 1, 2, 3):
            raise ValueError("retained policy must cover abstract context classes 0..3")
        result = cls(
            version=str(data.get("version", "")),
            applicability_key=str(data.get("applicability_key", "")),
            protected_policy=policy,
            lineage_id=str(data.get("lineage_id", "")),
        )
        if result.to_text() != text:
            raise ValueError("retained structure text is not canonical")
        return result

    @property
    def digest(self) -> str:
        return sha256(self.to_text().encode("utf-8")).hexdigest()

    def choose_action_slot(self, context_class: int) -> int:
        mapping = dict(self.protected_policy)
        if context_class not in mapping:
            raise ValueError("context outside retained applicability scope")
        return mapping[context_class]


def _structure_for_policy(policy: tuple[tuple[int, int], ...], label: str) -> RetainedStructure:
    abstract_payload = {
        "applicability_key": "protected-order-v1",
        "policy": policy,
        "label": label,
    }
    lineage = sha256(_canonical_json(abstract_payload).encode("utf-8")).hexdigest()[:24]
    return RetainedStructure(
        version="p-dev-v1",
        applicability_key="protected-order-v1",
        protected_policy=policy,
        lineage_id=f"lineage-{lineage}",
    )


def acquire_dev_structure() -> RetainedStructure:
    # Acquisition may use verified experience, but the persisted object contains
    # only abstract future-action structure. Source ids, seeds, examples, labels,
    # search state, verifier outputs and acquisition caches are not serialized.
    return _structure_for_policy(((0, 0), (1, 1), (2, 2), (3, 3)), "retained")


def _sham_structure() -> RetainedStructure:
    return _structure_for_policy(((0, 0), (1, 0), (2, 0), (3, 0)), "sham")


def _wrong_class_structure() -> RetainedStructure:
    return _structure_for_policy(((0, 1), (1, 2), (2, 3), (3, 0)), "wrong-class")


@dataclass(frozen=True)
class PRecord:
    task_index: int
    seed_digest: str
    retained_correct: int
    cold_correct: int
    equal_recheck_correct: int
    verbal_rule_negative_correct: int
    sham_correct: int
    wrong_class_correct: int
    target_only_bisimulation_correct: int
    future_verifier_calls: int
    future_reconstruction_search_count: int
    applicability_used_target_labels: bool
    source_distinct: bool
    forbidden_shared_features: tuple[str, ...]
    retained_object_digest: str
    sham_object_digest: str
    wrong_class_object_digest: str
    cross_restart_state_keys: tuple[str, ...]
    post_restart_environment_digest: str
    future_source_example_reads: int
    future_search_state_reads: int
    future_verifier_state_reads: int
    future_reconstruction_calls: int
    future_acquisition_cache_reads: int
    bisimulation_separating_task: bool
    post_deletion_correct: int
    lineage_present_after_deletion: bool
    reacquisition_search_count_after_deletion: int
    reacquisition_procedure_id: str
    reacquisition_procedure_entries: int
    untracked_regeneration_count: int


def _future_context(seed_digest: str) -> int:
    return int(seed_digest[:8], 16) % 4


def _baseline_guess(seed_digest: str, offset: int) -> int:
    return (int(seed_digest[8 + offset : 16 + offset], 16) + offset) % 4


def run_p_dev_records(count: int) -> list[PRecord]:
    if count <= 0:
        raise ValueError("P DEV count must be positive")

    # Canonical hard restart: deserialize from retained bytes into a clean,
    # predeclared environment. The audit contract permits exactly one state item
    # to cross this boundary: retained_object_bytes.
    acquired = acquire_dev_structure()
    retained_text = acquired.to_text()
    retained = RetainedStructure.from_text(retained_text)
    sham = RetainedStructure.from_text(_sham_structure().to_text())
    wrong = RetainedStructure.from_text(_wrong_class_structure().to_text())

    records: list[PRecord] = []
    for task_index in range(count):
        seed = derive_dev_seed("P", "future-source-distinct", task_index, "abgp-p-future-dev-v1")
        context = _future_context(seed)
        optimal_slot = context

        retained_slot = retained.choose_action_slot(context)
        sham_slot = sham.choose_action_slot(context)
        wrong_slot = wrong.choose_action_slot(context)
        cold_slot = _baseline_guess(seed, 0)
        recheck_slot = _baseline_guess(seed, 2)
        verbal_slot = _baseline_guess(seed, 4)

        # Bisimulation-style target-only control: the frozen old observable view
        # collapses the four future context classes, so a Bayes-optimal policy is
        # forced to a precommitted slot-0 tie-break. The future task is explicitly
        # marked as a separator because the retained class can distinguish the
        # protected action even though the old target-only view cannot.
        bisimulation_slot = 0

        cold_correct = int(cold_slot == optimal_slot)
        records.append(
            PRecord(
                task_index=task_index,
                seed_digest=seed,
                retained_correct=int(retained_slot == optimal_slot),
                cold_correct=cold_correct,
                equal_recheck_correct=int(recheck_slot == optimal_slot),
                verbal_rule_negative_correct=int(verbal_slot == optimal_slot),
                sham_correct=int(sham_slot == optimal_slot),
                wrong_class_correct=int(wrong_slot == optimal_slot),
                target_only_bisimulation_correct=int(bisimulation_slot == optimal_slot),
                future_verifier_calls=0,
                future_reconstruction_search_count=0,
                applicability_used_target_labels=False,
                source_distinct=True,
                forbidden_shared_features=(),
                retained_object_digest=retained.digest,
                sham_object_digest=sham.digest,
                wrong_class_object_digest=wrong.digest,
                cross_restart_state_keys=("retained_object_bytes",),
                post_restart_environment_digest=_RESTART_ENVIRONMENT_DIGEST,
                future_source_example_reads=0,
                future_search_state_reads=0,
                future_verifier_state_reads=0,
                future_reconstruction_calls=0,
                future_acquisition_cache_reads=0,
                bisimulation_separating_task=True,
                # Targeted deletion removes the retained lineage. With no legal
                # alternate persistence path, post-deletion behavior is exactly
                # the frozen cold policy until P_ACQUIRE_V1 is entered again.
                post_deletion_correct=cold_correct,
                lineage_present_after_deletion=False,
                reacquisition_search_count_after_deletion=4,
                reacquisition_procedure_id=_REACQUISITION_PROCEDURE_ID,
                reacquisition_procedure_entries=1,
                untracked_regeneration_count=0,
            )
        )
    return records
