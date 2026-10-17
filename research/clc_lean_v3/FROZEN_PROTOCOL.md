# CLC–FLASH V3 — frozen finite Lean transport soundness and admission interface

**Date:** 2026-10-18, New Zealand. **Baseline:** source-exact RealityGraph V2 commit `4f509e462388e551c5791bd210e8f99b8ee764cb`, qualified [CI #39073175707](https://github.com/heathsanchez/realitygraph/actions/runs/39073175707). No existing source/test deleted; new isolated branch.

## The formal claim (precisely scoped)

Mechanize in Lean 4 **the finite core of the user's Certified Lineage Calculus V1**: a form has finite states, finite tests, protected tests and verdicts `UNKNOWN/EQ/DIST`; a transport provides (i) forward state map, (ii) contravariant backward test map, and (iii) protected-test lift. Refine judgment must satisfy:
- all source evaluations of pulled-back target tests are below or equal to the corresponding target evaluations in the flat information order (UNKNOWN may refine to EQ or DIST, never swap EQ/DIST);
- every protected target test has a protected source preimage;
- every protected source test lifts to a protected target test with exact round-trip `pull(lift(p))=p`.

Prove in Lean generic *decisive verdict preservation* and *composition of valid transports*, including contravariant pullback and composable protected-test lift. Instantiate **finite two-state/two-test strict and developmental transports** and require the actual Lean kernel to check `by decide` proofs on complete finite tables. Mutate forward mapping, backward mapping, protected lift, protected flags/evaluations; each intended falsifier must produce nonzero Lean exit and no FLASH admission. Demonstrate type mismatch / missing backward transformer fail closed.

## Proof-carrying FLASH gate

Reuse original `realitygraph.flash.FlashClosure` and `FlashEventRuntime`; opt-in frozen `LeanCLCChecker` in constructor, which fail-closes any capability admission without a typed `FiniteCLCClaim`. The witness's source/target state labels, forward map, authority snapshot, verifier ID and full oracle must bind to **the exact `FiniteCapability` that the existing original FLASH verifier independently checks**. The Python bridge generates a Lean file from canonical exact claim bytes, invokes a separately installed and version-declared Lean binary with a timeout, requires kernel success and a pinned verdict theorem. It records SHA-256 digests of original CLC Lean library, concrete Lean theorem file and entire claim plus toolchain version.

A supplied string/hash/flag alone never authorizes admission: **the FLASH gate must execute Lean** on those exact bytes at admission. On generated FLASH composition h=f;g, the gate must form and check a composed transport claim; reject if source/target forms do not connect or the transport fails. Preserve conjunctive parent supports and stale/revoked control. Repeated exact event IDs remain idempotent.

**Trust boundary:** This proves finitary transport obligations about pinned concrete state/test tables under a trusted Lean binary and correctly bound Python serialization and input authority. It does *not* authenticate external-world state, verify arbitrary CLC category semantics, turn untrusted CLC tables into independent facts, prove Lean executable integrity merely from stdout, or certify the entire FLASH or MDA runtime. The Python bridge and binary are named TCB. A source/hash receipt is audit evidence, not a cryptographic signature or a free-standing portable proof.

## Frozen finite tests

1. Strict transport X two-state to Y two-state, protected both tests, exact EQ/DIST tables, expected Lean PASS.
2. Developmental refinement from UNKNOWN to two decisive target outputs, expected Lean PASS.
3. Mutate forward state mapping, backward test mapping, source/target protected lift mapping, target protected preimage, or source decisive EQ-to-DIST; each must produce a Lean rejection; verify the claimed template actually fails, not just Python prevalidation where applicable.
4. Source/target authority mismatch; mutant oracle and capability semantics; absent transport; inconsistent target state table; same event id/different witness; all reject **without changing FLASH active state or event count**.
5. Original independent V2 finite protected/batch census stays green: 150/150 capability-event and 540/540 future-quotient prefixes; independent batch oracle unchanged; regression cases remain PASS.
6. Certified FLASH causal episode: f:X->Y and g:Y->Z admitted only after their exact separate finite transport Lean checks, h=f;g created with composed protected pull/lift certificate; 2 obligations become solved; compiled present restarts and h executes. Revoke f => h inactive + obligations OPEN, then fresh certified alternate X->Z => restored; independent alt survives a later f revocation. No silent reuse of revoked certificate token.
7. Deliberately corrupt a parent transport and require both the original admission and downstream h to be rejected. External validity not claimed.
8. Run GitHub native Lean 4.24.0 and inherited source-owned Python regression on original pinned code; artifact includes full Lean library, source generator, tests, exact payload and recorded stdout/digests. A broken Lean installation or compiler gives `UNKNOWN_ENVIRONMENT`, not mathematical rejection.
9. If executable Lean theorem or bridge cannot be independently qualified, status RED/UNKNOWN and preserve failure. Do not label a green static lint as a new theorem.

No cross-repo merge, external publication, outreach, production change, or claims about broad mathematical novelty or prospective general-intelligence superiority. Source is intentionally limited to an isolated research branch.
