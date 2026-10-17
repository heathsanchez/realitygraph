# CLC finite transport → Lean 4.24 kernel → FLASH admission: independently qualified V3

**Status: WARRANTED_BOUNDED_LEAN_CERTIFIED_FINITE_TRANSPORT_AND_FLASH_ADMISSION.** Not a full CLC soundness theorem, not general FLASH batch equivalence, and not production-certified provenance.

## Frozen inputs and original authorities

- Original RealityGraph source/CI qualification: source base `4f509e462388e551c5791bd210e8f99b8ee764cb`, [V2 GREEN #39073175707](https://github.com/heathsanchez/realitygraph/actions/runs/39073175707), older RED V1 finding cheapest-capability preference mismatch.
- **V3 protocol frozen before any implementation or result:** [commit f15074e5](https://github.com/heathsanchez/realitygraph/commit/f15074e5b3ee591d12b783e71320a7cb11c32cba).
- [Qualified Lean+native CI #39079945123](https://github.com/heathsanchez/realitygraph/actions/runs/39079945123) at [commit 7d876da9](https://github.com/heathsanchez/realitygraph/commit/7d876da93a007933e3ff9c4894e01cb00e77ff9b), one full Green job.
- [CI artifact #12118626846](https://github.com/heathsanchez/realitygraph/actions/runs/39079945123/artifacts/12118626846), SHA-256 `892a82ce56bee37be78682added2876b3038a4bf42cb9925faf785d28847d10c`, independently downloaded, hash verified, opened, five V3 positive/falsifier test groups and V2 evidence inspected.
- Toolchain: official Lean 4.24.0, Linux x86_64, commit `797c613eb9b6d4ec95db23e3e00af9ac6657f24b`, installed by elan in CI.
- Original Python source reused: `realitygraph.flash` and `realitygraph.developmental_core`. V2 source modifications preserved with opt-in CLC proof gate; the un-gated historic path retains its prior default and regression.
- Source SHA-256 from actual CI runner:
  - `FiniteTransport.lean` `c664e164d815097ba01051e8489f214e508bcf5f5d3e2ab4484bfcbfd9ec443c`.
  - `realitygraph/clc_lean.py` `6c01fd573caabfb64d44c8285530288eb47558096cb2475d3f305fe17c68d0c3`.
  - `realitygraph/flash.py` `cdfa9c0fcc7398ca218ddba9634eb88838c1e7a697ad24d6c5531913e7d98028`.
  - `tests/test_clc_lean_admission_v3.py` `4dcdf8421a9f4f0cf5afc6414bcfb27d38739f6debe3e76eeec36e5f2b608990`.

## What Lean proves

The source [FiniteTransport.lean](../../research/clc_lean_v3/FiniteTransport.lean) defines the CLC V1 finite state/test *transport semantics* relative to declared evaluators and protected predicates:
- Flat verdict order `unknown ≤ eq` and `unknown ≤ dist`, with the two decisive outcomes incomparable; reflexivity and transitivity.
- A transported state map `forward`, contravariant test map `pull` and protected-test lift `lift`.
- `Valid A B r` is *all three* obligations:
  1. `∀ x d, Refines (A.eval x (r.pull d)) (B.eval (r.forward x) d)`.
  2. `∀ d, B.isProtected d = true → A.isProtected (r.pull d) = true`.
  3. `∀ p, A.isProtected p = true → B.isProtected (r.lift p) = true ∧ r.pull (r.lift p) = p`.
- Generic theorems `refines_trans`, `refines_decisive`, `preserve_decisive`, `valid_compose`, `valid_identity`, and `strict_is_valid` are accepted by the pinned Lean kernel. In particular, `valid_compose` composes the forward map, reverses `pull` and composes the protected `lift`; it is not a test-only assertion.
- Actual two-state/two-test strict and UNKNOWN→decisive transports are constructed from finite source/target evaluation tables; generated `clcChecked` theorems are kernel-proved by decidability of finite `Fin` quantification after explicit unfolding. The source admits no `sorry`/custom `axiom`/unsafe escape in generated proofs.

## What the FLASH boundary checks

The optional `LeanCLCChecker` is installed in existing `FlashClosure`. No privileged upgrade is applied to old ungated deployments. When enabled:
- Every direct `CapabilityAdmissionEvent` must include a typed `FiniteCLCTransport`, or it fails closed *before modifying the ledger or active state*.
- The Python serialization/binding TCB checks the source state set, complete finite oracle, target set, exact forward semantics, authority, verifier identity and protected nondegenerate output probes against the same actual `FiniteCapability` that FLASH checks with its original exhaustive native finite verifier.
- The checker reads the pinned Lean library by SHA-256, checks exact Lean 4.24.0 version, generates exact finite proof source and **runs Lean at admission**, requiring exit 0 and a digest-bound printed marker. A submitted hash/Boolean alone is insufficient. It records a `CLCProofReceipt` with claim/proof/library/stdout digests and toolchain version.
- When `f` and `g` enable `h=f;g`, the source/target intermediate CLC form and authority must agree; the composed pull/lift maps are checked with the generic transport obligations and a second concrete Lean proof **before generated `h` is admitted**. Preflight rejects an uncomposable new parent without mutating the graph.
- On ancestor revocation, the dependent `h` loses active warrant, while immutable prior certificate receipts remain historical data and independent active `alt` support preserves the protected obligation. New roles use different IDs, not resurrection of revoked tokens.

## Exact bounded replay

| Gate | Result |
|---|---|
| Generic source Lean proof compilation | PASS |
| Strict, developmental and composed concrete proofs | PASS |
| Deliberate invalid forward / pull / lift / protected / evaluation mutations fail Lean | PASS |
| Forged/missing transport, mismatched authority/contract, bad oracle, identity collisions | PASS |
| Derived h from f;g executes after compiled-present restart | PASS |
| Ancestor f ablation reopens both protected obligations without alt | PASS |
| Independently certified alternative alt survives f ablation | PASS |
| Incompatible intermediate CLC form rejected before FLASH admission | PASS |
| 5 V3 unittest test groups | 5/5 PASS |
| 11 source-native inherited tests (FLASH event/future/developmental/V2 preference) | 11/11 PASS |
| Original V2 30 × 5 capability-event prefixes vs independent batch oracle | 150/150 PASS |
| Original V2 90 × 6 protected-future prefixes vs independent batch oracle | 540/540 PASS |
| V2 protected batch / cost preference status | PASS / PASS |

## Failure lineage, retained

- [39079596403](https://github.com/heathsanchez/realitygraph/actions/runs/39079596403) RED: reserved Lean `protected` identifier.
- [39079686878](https://github.com/heathsanchez/realitygraph/actions/runs/39079686878) RED: generic Lean library passed, concrete finite `Decidable (Strict...)` not synthesized.
- [39079854901](https://github.com/heathsanchez/realitygraph/actions/runs/39079854901) RED: shallow Git fetch omitted original freeze ancestry.
- [39079883964](https://github.com/heathsanchez/realitygraph/actions/runs/39079883964) RED: concrete finite `decide` remained folded, no finite decidability elaboration.
- [39079945123](https://github.com/heathsanchez/realitygraph/actions/runs/39079945123) GREEN: native Lean `Init.Data.Nat.Lemmas` finite quantification + concrete proposition unfolding + full-source ancestry.
These are proof/harness development failures, not evidence against the mathematical validity of CLC.

## Critical boundaries and next work

1. The evaluator tables and claim-to-executable binding are in the **Python/source-adapter trusted computing base**. Lean verifies the stated finite tables; it does not authenticate independent reality or prevent a dishonest external oracle from defining a misleading target.
2. The tested finite transports are not full CLC category semantics across arbitrary forms/port hypergraphs. The generic *transport composition* theorem is Lean checked; general CLC soundness, query-preserving quotient paths, complete mediation, and whole-system FLASH insertion/revocation = batch equivalence remain unproved.
3. The proof receipts are currently stored in the in-memory `FlashClosure.clc_receipts` ledger-adjacent table. `CompiledPresent.restart()` checks capability execution, **not** replay of Lean proof receipts after a process restart. Durable, authority-bound reauthentication of the evidence store is the next precise integration gate before calling the runtime end-to-end certificate-carrying.
4. Lean binary/executable trust, exact Python serialization, source pinning and toolchain integrity remain explicit assumptions; the hashes are audit identities, not an independent cryptographic attestation or portable signed proof.
5. This is a bounded finite-source integration result; no new autonomous discovery, cross-repository transfer, performance superiority, production merge, or public security claim was tested.

**WARRANTED_BOUNDED:** finite CLC transport kernel checked, actual FLASH admission gated on Lean execution, composed transport checked, frozen native causal tests and original batch oracle green. **UNKNOWN/OPEN:** durable proof-carrying re-admission on cold restart, full CLC kernel soundness relative to external truths, general FLASH exactness, prospective novel acquisition and matched-agent advantage.

**Next cheapest experiment:** implement immutable certificate storage plus cold-restart re-verification against pinned Lean/authority, then run explicitly adversarial stale-scope and revoked-proof tests on the same finite source. No new architecture.
