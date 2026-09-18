from __future__ import annotations

from dataclasses import dataclass

from .capability import FiniteCapability
from .compiled_present import CompiledPresent
from .developmental_core import route_residual
from .developmental_types import (
    DevelopmentalResult,
    ResultKind,
    canonical_digest,
)
from .ledger import Ledger
from .meta_memory import (
    MetaMemory,
    RepairEpisode,
    RepairPhase,
    RepairRule,
    RepairRuleStatus,
)


AUTHORITY = "collatz-shortcut-exact-v1"
VERIFIER = "collatz-exact-integer-replay-v1"
KERNEL = "qckn-v1-collatz-adapter"
ENDPOINT_BANK_ID = "collatz-c9-endpoint-bank-pre27-v1"
OBSTRUCTION = "collatz:c9:live-two-replay-endpoint-unseen"
STRATEGY = "verify-endpoint-tail-to-one-and-promote"
STRATEGY_VERSION = "v1"

INTERFACE_DIGEST = canonical_digest(
    {
        "map": "T(n)=n/2 if even else (3n+1)/2",
        "protected_consequence": "lower_merge",
        "capability_input": "concrete_endpoint",
        "capability_output": "shared_tail_at_1",
    },
    prefix="collatz-qckn-interface-v1:",
)
PORTFOLIO_DIGEST = canonical_digest(
    {
        "strategies": (
            "reuse-verified-endpoint",
            STRATEGY,
        ),
    },
    prefix="collatz-qckn-portfolio-v1:",
)


# Frozen before the prospective 27-bit holdout.
FROZEN_ENDPOINT_EVIDENCE: tuple[tuple[int, int], ...] = (
    (147_269_353, 124),
    (153_560_809, 102),
    (157_755_113, 105),
    (260_515_561, 98),
    (373_761_769, 146),
    (1_205_282_537, 97),
    (1_290_217_193, 165),
    (1_928_799_977, 123),
    (2_196_186_857, 82),
    (4_083_623_657, 205),
)

# The six unique endpoint capabilities acquired on the untouched 27-bit band.
HELDOUT_NEW_ENDPOINT_EVIDENCE: tuple[tuple[int, int], ...] = (
    (733_423_337, 166),
    (1_076_307_689, 127),
    (2_786_535_145, 171),
    (17_417_316_073, 164),
    (18_786_756_329, 234),
    (64_877_962_985, 220),
)

# Exact 27-bit live-hit multiplicities measured before promotion of the new bank.
HELDOUT_ENDPOINT_SEQUENCE: tuple[int, ...] = (
    147_269_353,
    373_761_769,
    373_761_769,
    373_761_769,
    373_761_769,
    1_205_282_537,
    1_205_282_537,
    1_205_282_537,
    1_290_217_193,
    1_290_217_193,
    1_928_799_977,
    1_928_799_977,
    2_196_186_857,
    2_196_186_857,
    2_196_186_857,
    733_423_337,
    733_423_337,
    733_423_337,
    1_076_307_689,
    1_076_307_689,
    1_076_307_689,
    2_786_535_145,
    17_417_316_073,
    18_786_756_329,
    64_877_962_985,
)

EVIDENCE_CATALOG = dict((*FROZEN_ENDPOINT_EVIDENCE, *HELDOUT_NEW_ENDPOINT_EVIDENCE))


def shortcut(n: int) -> int:
    if n <= 0:
        raise ValueError("Collatz endpoint must be positive")
    return n // 2 if n % 2 == 0 else (3 * n + 1) // 2


def verify_tail_to_one(endpoint: int, expected_steps: int, *, guard: int = 10_000) -> bool:
    y = int(endpoint)
    for step in range(guard + 1):
        if y == 1:
            return step == int(expected_steps)
        y = shortcut(y)
    return False


def _certificate_id(rows: tuple[tuple[int, int], ...]) -> str:
    return "collatz-endpoint-cert-" + canonical_digest(
        {"rows": rows, "verifier": VERIFIER},
        prefix="collatz-endpoint-bank-v1:",
    )[:20]


def endpoint_bank_capability(
    rows: tuple[tuple[int, int], ...] = FROZEN_ENDPOINT_EVIDENCE,
    *,
    capability_id: str = ENDPOINT_BANK_ID,
    provenance_ids: tuple[str, ...] = (
        "test-run-35318888802",
        "test-run-35323204493",
    ),
) -> FiniteCapability:
    if not rows:
        raise ValueError("endpoint bank requires evidence")
    for endpoint, steps in rows:
        if not verify_tail_to_one(endpoint, steps):
            raise ValueError(f"endpoint evidence failed independent replay: {endpoint}")
    semantics = tuple(
        (str(endpoint), f"lower_merge:1:steps={steps}")
        for endpoint, steps in sorted(rows)
    )
    return FiniteCapability(
        capability_id=capability_id,
        input_type="CollatzEndpoint",
        output_type="LowerMergeCertificate",
        semantics=semantics,
        guard_inputs=tuple(endpoint for endpoint, _ in semantics),
        certificate_id=_certificate_id(rows),
        dependencies=(),
        authority_snapshot=AUTHORITY,
        verifier_id=VERIFIER,
        provenance_ids=provenance_ids,
        cost=len(rows),
    )


def _repair_episode(phase: RepairPhase, evidence_id: str) -> RepairEpisode:
    return RepairEpisode(
        episode_id=f"collatz-endpoint-repair-{phase.value.lower()}",
        phase=phase,
        obstruction_fingerprint=OBSTRUCTION,
        strategy_id=STRATEGY,
        strategy_version=STRATEGY_VERSION,
        portfolio_digest=PORTFOLIO_DIGEST,
        authority_snapshot=AUTHORITY,
        verifier_id=VERIFIER,
        interface_digest=INTERFACE_DIGEST,
        selection_cost=1,
        object_evidence_digest=canonical_digest(
            {"evidence": evidence_id, "strategy": STRATEGY},
            prefix="collatz-repair-evidence-v1:",
        ),
    )


def promoted_endpoint_repair_rule() -> RepairRule:
    memory = MetaMemory.empty()
    memory = memory.record_success(
        _repair_episode(RepairPhase.ACQUISITION, "test-run-35318888802")
    )
    memory = memory.record_success(
        _repair_episode(RepairPhase.CALIBRATION, "test-run-35323204493")
    )
    rules = [
        rule for rule in memory.rules
        if rule.status is RepairRuleStatus.PROMOTED
    ]
    if len(rules) != 1:
        raise AssertionError("Collatz endpoint repair rule did not promote exactly once")
    return rules[0]


def build_promoted_ledger() -> tuple[Ledger, str, str]:
    capability = endpoint_bank_capability()
    rule = promoted_endpoint_repair_rule()
    ledger = Ledger()
    cap_event = ledger.append_promote_capability(capability, KERNEL)
    rule_event = ledger.append_promote_repair_rule(
        rule,
        KERNEL,
        parents=(cap_event.id,),
    )
    return ledger, capability.capability_id, rule.rule_id


def warm_present() -> CompiledPresent:
    ledger, _capability_id, _rule_id = build_promoted_ledger()
    return ledger.materialize_compiled_present().restart()


def empty_present() -> CompiledPresent:
    return Ledger().materialize_compiled_present().restart()


def sham_present() -> CompiledPresent:
    # Same shape, wrong endpoint carrier and wrong obstruction boundary.
    sham_cap = endpoint_bank_capability(
        ((3, 5),),
        capability_id="sham-collatz-endpoint-bank-v1",
        provenance_ids=("sham",),
    )
    sham_episode_a = RepairEpisode(
        episode_id="sham-acq",
        phase=RepairPhase.ACQUISITION,
        obstruction_fingerprint="collatz:sham-obstruction",
        strategy_id=STRATEGY,
        strategy_version=STRATEGY_VERSION,
        portfolio_digest=PORTFOLIO_DIGEST,
        authority_snapshot=AUTHORITY,
        verifier_id=VERIFIER,
        interface_digest=INTERFACE_DIGEST,
        selection_cost=1,
        object_evidence_digest="sham-a",
    )
    sham_episode_b = RepairEpisode(
        episode_id="sham-cal",
        phase=RepairPhase.CALIBRATION,
        obstruction_fingerprint="collatz:sham-obstruction",
        strategy_id=STRATEGY,
        strategy_version=STRATEGY_VERSION,
        portfolio_digest=PORTFOLIO_DIGEST,
        authority_snapshot=AUTHORITY,
        verifier_id=VERIFIER,
        interface_digest=INTERFACE_DIGEST,
        selection_cost=1,
        object_evidence_digest="sham-b",
    )
    memory = MetaMemory.empty().record_success(sham_episode_a).record_success(sham_episode_b)
    sham_rule = next(
        rule for rule in memory.rules
        if rule.status is RepairRuleStatus.PROMOTED
    )
    ledger = Ledger()
    cap_event = ledger.append_promote_capability(sham_cap, KERNEL)
    ledger.append_promote_repair_rule(sham_rule, KERNEL, parents=(cap_event.id,))
    return ledger.materialize_compiled_present().restart()


@dataclass(frozen=True)
class FutureCost:
    hits: int
    unique_endpoints: int
    reused_hits: int
    verifier_calls: int
    portfolio_search_calls: int
    closed_hits: int


def _active_endpoint_bank(present: CompiledPresent) -> dict[int, int]:
    rows: dict[int, int] = {}
    active = set(present.capability_graph.active_ids())
    for capability in present.capability_graph.capabilities:
        if capability.capability_id not in active:
            continue
        if capability.input_type != "CollatzEndpoint":
            continue
        for endpoint, result in capability.semantics:
            if not result.startswith("lower_merge:1:steps="):
                continue
            rows[int(endpoint)] = int(result.rsplit("=", 1)[1])
    return rows


def _active_repair_rule(present: CompiledPresent) -> RepairRule | None:
    return present.meta_memory.promoted_match(
        obstruction_fingerprint=OBSTRUCTION,
        portfolio_digest=PORTFOLIO_DIGEST,
        authority_snapshot=AUTHORITY,
        verifier_id=VERIFIER,
        interface_digest=INTERFACE_DIGEST,
    )


def classify_endpoint_obligation(
    present: CompiledPresent,
    endpoint: int,
) -> DevelopmentalResult:
    if endpoint in _active_endpoint_bank(present):
        return DevelopmentalResult(
            ResultKind.COMPILED,
            obligation_id=f"collatz-endpoint:{endpoint}",
            detail="verified endpoint capability active",
        )
    return DevelopmentalResult(
        ResultKind.UNKNOWN_IDENTITY,
        obligation_id=f"collatz-endpoint:{endpoint}",
        detail="live endpoint not represented in active bank",
    )


def run_future_endpoint_sequence(
    present: CompiledPresent,
    endpoints: tuple[int, ...] = HELDOUT_ENDPOINT_SEQUENCE,
) -> FutureCost:
    active_bank = _active_endpoint_bank(present)
    repair_rule = _active_repair_rule(present)
    local = dict(active_bank)

    verifier_calls = 0
    portfolio_search_calls = 0
    reused_hits = 0
    closed_hits = 0

    for endpoint in endpoints:
        if endpoint in local:
            reused_hits += 1
            closed_hits += 1
            continue

        expected_steps = EVIDENCE_CATALOG.get(endpoint)
        if expected_steps is None:
            raise ValueError(f"missing independent endpoint evidence: {endpoint}")

        if repair_rule is None:
            portfolio_search_calls += 1

        verifier_calls += 1
        if not verify_tail_to_one(endpoint, expected_steps):
            raise AssertionError(f"future endpoint verification failed: {endpoint}")
        local[endpoint] = expected_steps
        closed_hits += 1

    return FutureCost(
        hits=len(endpoints),
        unique_endpoints=len(set(endpoints)),
        reused_hits=reused_hits,
        verifier_calls=verifier_calls,
        portfolio_search_calls=portfolio_search_calls,
        closed_hits=closed_hits,
    )


def ablated_present(*, capability: bool, repair_rule: bool) -> CompiledPresent:
    ledger, capability_id, rule_id = build_promoted_ledger()
    if capability:
        ledger.append_revoke_capability(
            capability_id,
            KERNEL,
            reason="Collatz QCKN qualification ablation",
        )
    if repair_rule:
        ledger.append_revoke_repair_rule(
            rule_id,
            KERNEL,
            reason="Collatz QCKN qualification ablation",
        )
    return ledger.materialize_compiled_present().restart()
