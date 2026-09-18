from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

from .collatz_adapter import (
    AUTHORITY,
    ENDPOINT_BANK_ID,
    KERNEL,
    VERIFIER,
    _active_endpoint_bank,
    _active_repair_rule,
    build_promoted_ledger,
    endpoint_bank_capability,
    verify_tail_to_one,
)
from .ledger import Ledger


GEN2_CAPABILITY_ID = "collatz-c9-endpoint-acquisitions-27bit-v1"
GEN2_ENDPOINT_EVIDENCE: tuple[tuple[int, int], ...] = (
    (733_423_337, 166),
    (1_076_307_689, 127),
    (2_786_535_145, 171),
    (17_417_316_073, 164),
    (18_786_756_329, 234),
    (64_877_962_985, 220),
)

GEN3_CAPABILITY_ID = "collatz-qckn-fresh-endpoints-cb8501461fe9cf8a"
GEN3_ENDPOINT_EVIDENCE: tuple[tuple[int, int], ...] = (
    (17_843_037_929, 131),
)


def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def endpoint_bank_digest(rows: dict[int, int]) -> str:
    payload = sorted((int(k), int(v)) for k, v in rows.items())
    return hashlib.sha256(canonical_json(payload).encode()).hexdigest()


def generation2_ledger() -> tuple[Ledger, str]:
    ledger, _base_capability_id, _rule_id = build_promoted_ledger()
    capability = endpoint_bank_capability(
        GEN2_ENDPOINT_EVIDENCE,
        capability_id=GEN2_CAPABILITY_ID,
        provenance_ids=(
            "test-run-35324969758",
            "prospective-27-bit-endpoint-acquisition",
        ),
    )
    event = ledger.append_promote_capability(
        capability,
        KERNEL,
        parents=ledger.heads,
    )
    return ledger, event.id


def generation2_present():
    ledger, _event_id = generation2_ledger()
    present = ledger.materialize_compiled_present().restart()
    bank = _active_endpoint_bank(present)
    if len(bank) != 16:
        raise AssertionError(f"unexpected generation-2 endpoint bank size: {len(bank)}")
    if _active_repair_rule(present) is None:
        raise AssertionError("generation-2 present lost promoted endpoint repair rule")
    return present


def generation3_ledger() -> tuple[Ledger, str]:
    ledger, _base_event = generation2_ledger()
    capability = endpoint_bank_capability(
        GEN3_ENDPOINT_EVIDENCE,
        capability_id=GEN3_CAPABILITY_ID,
        provenance_ids=(
            "realitygraph-run-35337836903",
            "complete-29-bit-source-coverage",
        ),
    )
    event = ledger.append_promote_capability(
        capability,
        KERNEL,
        parents=ledger.heads,
    )
    return ledger, event.id


def generation3_present():
    ledger, _event_id = generation3_ledger()
    present = ledger.materialize_compiled_present().restart()
    bank = _active_endpoint_bank(present)
    if len(bank) != 17:
        raise AssertionError(f"unexpected generation-3 endpoint bank size: {len(bank)}")
    if _active_repair_rule(present) is None:
        raise AssertionError("generation-3 present lost promoted endpoint repair rule")
    return present


def _generation_ledger(generation:int) -> tuple[Ledger,str]:
    if generation==2:
        return generation2_ledger()
    if generation==3:
        return generation3_ledger()
    raise ValueError(f"unsupported endpoint generation: {generation}")


def _generation_present(generation:int):
    if generation==2:
        return generation2_present()
    if generation==3:
        return generation3_present()
    raise ValueError(f"unsupported endpoint generation: {generation}")


def export_bank_payload(*, generation:int=3) -> dict[str, object]:
    present = _generation_present(generation)
    bank = _active_endpoint_bank(present)
    return {
        "version": "collatz-endpoint-bank-v1",
        "compiled_present_digest": present.digest,
        "bank_digest": endpoint_bank_digest(bank),
        "endpoints": {str(k): v for k, v in sorted(bank.items())},
    }


@dataclass(frozen=True)
class ControllerReport:
    worker_shards: int
    source_lo: int
    source_hi: int
    prior_bank_size: int
    live_hits: int
    unique_live_endpoints: int
    warm_reuse_hits: int
    warm_verifier_calls: int
    cold_verifier_calls: int
    new_unique_endpoints: int
    unresolved: int
    promoted_capability_id: str
    restarted_bank_size: int
    ablation_restores_new_identity: bool
    prior_compiled_present_digest: str
    restarted_compiled_present_digest: str

    def payload(self) -> dict[str, object]:
        return asdict(self)


def _load_worker_results(directory: str) -> list[dict[str, object]]:
    files = sorted(Path(directory).glob("*.json"))
    if not files:
        raise ValueError("no worker JSON results found")
    rows = []
    for path in files:
        payload = json.loads(path.read_text())
        if payload.get("version") != "collatz-qckn-worker-result-v1":
            raise ValueError(f"unsupported worker result: {path}")
        rows.append(payload)
    return rows


def _odd_bounds(lo:int,hi:int)->tuple[int,int] | None:
    first=lo if lo%2 else lo+1
    last=hi if hi%2 else hi-1
    if first>last:
        return None
    return first,last


def _ranges_are_disjoint(
    results: list[dict[str, object]],
    *,
    expect_lo:int|None=None,
    expect_hi:int|None=None,
) -> tuple[int, int]:
    ranges = sorted(tuple(int(x) for x in row["source_range"]) for row in results)
    for (lo1, hi1), (lo2, hi2) in zip(ranges, ranges[1:]):
        if hi1 >= lo2:
            raise ValueError(f"overlapping worker ranges: {(lo1,hi1)} {(lo2,hi2)}")

    if (expect_lo is None)!=(expect_hi is None):
        raise ValueError("expected range requires both bounds")
    if expect_lo is not None:
        effective=[]
        for lo,hi in ranges:
            b=_odd_bounds(lo,hi)
            if b is not None:
                effective.append(b)
        if not effective:
            raise ValueError("no odd worker coverage")
        expected=_odd_bounds(int(expect_lo),int(expect_hi))
        if expected is None:
            raise ValueError("expected interval contains no odd sources")
        if effective[0][0]!=expected[0] or effective[-1][1]!=expected[1]:
            raise ValueError(
                f"worker coverage boundary mismatch: {effective[0]}..{effective[-1]} expected {expected}"
            )
        for left,right in zip(effective,effective[1:]):
            if right[0]!=left[1]+2:
                raise ValueError(f"odd-source coverage gap: {left} -> {right}")
    return ranges[0][0], ranges[-1][1]


def consume_worker_results(
    directory: str,
    *,
    expect_lo:int|None=None,
    expect_hi:int|None=None,
    generation:int=3,
) -> tuple[ControllerReport, Ledger]:
    present = _generation_present(generation)
    prior_bank = _active_endpoint_bank(present)
    prior_digest = endpoint_bank_digest(prior_bank)
    repair_rule = _active_repair_rule(present)
    if repair_rule is None:
        raise AssertionError("candidate promotion requires active endpoint repair rule")

    results = _load_worker_results(directory)
    source_lo, source_hi = _ranges_are_disjoint(
        results,
        expect_lo=expect_lo,
        expect_hi=expect_hi,
    )

    live_counts: Counter[int] = Counter()
    candidates: dict[int, int] = {}
    unresolved = []

    for row in results:
        if row["bank_digest"] != prior_digest:
            raise ValueError("worker bank digest does not match QCKN compiled present")
        if int(row["bank_size"]) != len(prior_bank):
            raise ValueError("worker bank size does not match QCKN compiled present")

        for endpoint, count in row.get("live_endpoint_counts", {}).items():
            live_counts[int(endpoint)] += int(count)

        for candidate in row.get("candidate_acquisitions", ()):
            endpoint = int(candidate["endpoint"])
            steps = int(candidate["steps_to_one"])
            prior = candidates.get(endpoint)
            if prior is not None and prior != steps:
                raise ValueError(f"conflicting candidate evidence for endpoint {endpoint}")
            candidates[endpoint] = steps

        unresolved.extend(row.get("unresolved", ()))

    if unresolved:
        raise ValueError(f"worker returned unresolved endpoint obligations: {unresolved[:3]}")

    new_endpoints = sorted(set(live_counts) - set(prior_bank))
    if set(new_endpoints) != set(candidates):
        raise ValueError(
            "candidate set does not equal live endpoints absent from compiled present"
        )

    for endpoint in new_endpoints:
        steps = candidates[endpoint]
        if not verify_tail_to_one(endpoint, steps):
            raise ValueError(f"controller verification failed for endpoint {endpoint}")

    warm_reuse_hits = sum(
        count for endpoint, count in live_counts.items()
        if endpoint in prior_bank
    )
    warm_verifier_calls = len(new_endpoints)
    cold_verifier_calls = len(live_counts)

    ledger, _gen2_event = generation2_ledger()
    promoted_capability_id = ""
    if new_endpoints:
        rows = tuple((endpoint, candidates[endpoint]) for endpoint in new_endpoints)
        promoted_capability_id = (
            "collatz-qckn-fresh-endpoints-"
            + hashlib.sha256(canonical_json(rows).encode()).hexdigest()[:16]
        )
        capability = endpoint_bank_capability(
            rows,
            capability_id=promoted_capability_id,
            provenance_ids=(
                f"worker-bank:{prior_digest}",
                f"source-range:{source_lo}-{source_hi}",
            ),
        )
        ledger.append_promote_capability(
            capability,
            KERNEL,
            parents=ledger.heads,
        )

    restarted = ledger.materialize_compiled_present().restart()
    restarted_bank = _active_endpoint_bank(restarted)

    for endpoint in live_counts:
        if endpoint not in restarted_bank:
            raise AssertionError(f"promoted present cannot close live endpoint {endpoint}")

    ablation_restores = True
    if promoted_capability_id:
        ablated = Ledger(ledger.events.values())
        ablated.append_revoke_capability(
            promoted_capability_id,
            KERNEL,
            reason="fresh-band acquisition ablation",
        )
        ablated_present = ablated.materialize_compiled_present().restart()
        ablated_bank = _active_endpoint_bank(ablated_present)
        ablation_restores = (
            all(endpoint not in ablated_bank for endpoint in new_endpoints)
            and all(endpoint in ablated_bank for endpoint in prior_bank)
        )
        if not ablation_restores:
            raise AssertionError("fresh capability ablation did not restore prior identity boundary")

    report = ControllerReport(
        worker_shards=len(results),
        source_lo=source_lo,
        source_hi=source_hi,
        prior_bank_size=len(prior_bank),
        live_hits=sum(live_counts.values()),
        unique_live_endpoints=len(live_counts),
        warm_reuse_hits=warm_reuse_hits,
        warm_verifier_calls=warm_verifier_calls,
        cold_verifier_calls=cold_verifier_calls,
        new_unique_endpoints=len(new_endpoints),
        unresolved=0,
        promoted_capability_id=promoted_capability_id,
        restarted_bank_size=len(restarted_bank),
        ablation_restores_new_identity=ablation_restores,
        prior_compiled_present_digest=present.digest,
        restarted_compiled_present_digest=restarted.digest,
    )
    return report, ledger


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--export-bank")
    ap.add_argument("--consume-dir")
    ap.add_argument("--report-json")
    ap.add_argument("--expect-lo",type=int)
    ap.add_argument("--expect-hi",type=int)
    ap.add_argument("--generation",type=int,default=3)
    args = ap.parse_args()

    if args.export_bank:
        payload = export_bank_payload(generation=args.generation)
        Path(args.export_bank).write_text(canonical_json(payload) + "\n")
        print("EXPORTED_BANK_SIZE", len(payload["endpoints"]))
        print("EXPORTED_BANK_DIGEST", payload["bank_digest"])
        print("COMPILED_PRESENT_DIGEST", payload["compiled_present_digest"])
        print("PASS_QCKN_BANK_EXPORT")
        return

    if args.consume_dir:
        report, _ledger = consume_worker_results(
            args.consume_dir,
            expect_lo=args.expect_lo,
            expect_hi=args.expect_hi,
            generation=args.generation,
        )
        payload = {
            "version": "collatz-qckn-controller-report-v1",
            **report.payload(),
        }
        if args.report_json:
            Path(args.report_json).write_text(canonical_json(payload) + "\n")
        print("CONTROLLER_REPORT", canonical_json(payload))
        print("PASS_QCKN_FRESH_BAND_PROMOTION")
        return

    raise SystemExit("choose --export-bank or --consume-dir")


if __name__ == "__main__":
    main()
