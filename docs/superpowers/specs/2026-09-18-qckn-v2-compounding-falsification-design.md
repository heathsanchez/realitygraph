# QCKN V2 Compounding Falsification Design

**Status:** Approved V2 experiment design  
**Base:** `qckn-v1-frozen` at `527cb7df1d931be53a61b1523abeaae20501af27`  
**Development branch:** `qckn-v2-compounding-falsification-v1`

## Purpose

Test the smallest exact proposition that distinguishes verified capability
accumulation from developmental compounding:

> Can two independently acquired finite capabilities be composed, independently
> re-certified as one self-contained capability, compiled into the active
> present, and reused on unseen surface instances with less search and less
> active structure, while matched ablation restores the cold cost?

The experiment is a falsification probe, not a new QCK architecture. It uses the
frozen V1 capability algebra, causal ledger, MG2, and `CompiledPresent`. It does
not modify the frozen QCK theorem surface or any frozen V1 branch.

## Constitutional constraints

The experiment preserves the V1 documents at:

- `heathsanchez/Minimal-Sufficient-Interface`, documentation commit
  `baef39cd7b32c860e2d7aa80a95f3826b8a52738`;
- `heathsanchez/realitygraph`, documentation commit
  `7bd2030165d158f5656cfa4dbd57fd2ab8fce619`.

In particular:

1. QCK semantic meanings are unchanged.
2. Proposal is not promotion.
3. A dependency-bearing composite remains dependent until a separate authority
   check certifies a self-contained materialization.
4. Dependencies must not be cleared merely to make re-minimisation pass.
5. Causal ancestry remains in the ledger and provenance after contraction.
6. Provenance is not recoverability.
7. Anything required for declared future recovery must be retained as RESERVE,
   not mislabeled as provenance.
8. Incomplete search remains `UNKNOWN_SEARCH`.
9. The same authority and protected consequences apply to every experimental
   arm.

## Exact hypothesis

Let:

- `A : Pair -> Bit` be a capability found by finite search;
- `B : Bit -> Label` be an independently found capability;
- `C = B ∘ A : Pair -> Label` be the typed composition.

The primary hypothesis is:

\[
\operatorname{search}(G_1)
>
\operatorname{search}(G_2)
>
\operatorname{search}(G_3),
\]

with the frozen target values:

\[
10>3>0.
\]

Here:

- G1 searches the existing bounded NAND candidate space for parity;
- G2 searches a frozen finite decoder portfolio;
- G3 constructs the typed composition without acquisition search, then pays an
  independently reported exhaustive verification cost.

The re-minimisation hypothesis is:

\[
\text{active capabilities }3\to1
\]

without changing any protected `Pair -> Label` consequence.

The transfer hypothesis is:

\[
\operatorname{search}_{\mathrm{warm}}
<
\operatorname{search}_{\mathrm{cold}},
\]

and exact composite ablation restores the cold search cost.

## Frozen finite experiment

### G1: acquire parity

Reuse the declared Boolean observer search from
`realitygraph.fixtures.boolean_observer_growth`.

The old language contains the complete four functions of `x`. The lower
substrate is `{0,1,x,y}` with canonical NAND composition through depth three.
The admitted result must be the exhaustively verified parity capability.

Expected acquisition search calls: `10`.

### G2: acquire decoder

Freeze a complete ordered portfolio of the four total maps from:

```text
Bit = {0,1}
```

to:

```text
Label = {EVEN,ODD}
```

The target is the parity-label decoder:

```text
0 -> EVEN
1 -> ODD
```

The frozen enumeration places the target third. Authority checks every tested
candidate extensionally over the complete two-element carrier.

Expected acquisition search calls: `3`.

### G3: compose and re-certify

Construct `C = B ∘ A` only through `compose_capabilities`.

The initial composite must retain V1 dependency edges to A and B. It is a
candidate, not yet a standalone replacement.

An independent exhaustive authority then checks the complete four-element Pair
carrier against the protected parity-label oracle. Only after that check
survives may the experiment create a new capability identity representing the
materialized standalone composite.

The standalone promotion must have:

- a new capability identity;
- a new certificate identity tied to the exhaustive composite check;
- no active execution dependencies;
- provenance pointers to A, B, the dependent composite, and their certificates;
- the same declared authority/verifier boundary;
- a cost profile that distinguishes acquisition search, verification work, and
  active execution/representation cost.

Expected acquisition search calls: `0`.

## Re-minimisation

Before contraction, the active graph contains A, B, and the independently
verified standalone composite.

The re-minimisation gate challenges A and B separately and together against the
protected `Pair -> Label` consequence set.

A and B may leave ACTIVE only if:

1. the standalone composite remains active;
2. complete protected-consequence replay is unchanged;
3. exact restart preserves that behavior;
4. neither capability is justified as maintained reserve under the experiment's
   declared future contract.

The experiment declares no future obligation requiring independent recovery of
`Pair -> Bit` or `Bit -> Label`. Therefore A and B are PROVENANCE-only for this
bounded contract after standalone promotion. Their causal records remain in the
ledger; they are omitted from the compiled active present.

This is not a general reserve policy. A separate negative control declares
independent future use of B; in that contract B must remain RESERVE and removing
it must produce `RecoveryUnavailable` or the experiment's exact equivalent.

## Unseen transfer surface

Source acquisition uses the canonical pair surface:

```text
00, 01, 10, 11
```

Transfer uses a disjoint relabeled surface frozen before execution:

```text
aa, ab, ba, bb
```

The adapter supplies only the declared structural isomorphism between the two
carriers. It supplies no output labels, candidate ranking, or verifier result.

Cold execution searches the complete frozen `Pair' -> Label` candidate space.
Warm execution starts only from the restarted compiled present and transports
the verified composite through the declared isomorphism.

Both paths are checked by the same exhaustive target authority.

This establishes bounded structurally related transfer, not universal transfer
or autonomous ontology invention.

## Experimental arms

All arms use the same target surface, authority, verifier, candidate universe,
and protected consequence contract.

### COLD

No retained capability or history. Search the frozen target candidate space.

### WARM

Start only from the restarted re-minimised `CompiledPresent` containing the
standalone composite.

### RAW_HISTORY

Receive causal provenance/history without an active compiled composite. This
must not receive the warm shortcut.

### SHAM

Receive a type-compatible, similarly sized capability with the wrong exact
semantics/certificate boundary. It must be rejected and fall back to cold
search.

### ANCESTOR_ABLATION

Ablate the standalone composite from the compiled present. Search cost must
return exactly to the cold value.

The earlier source capabilities are provenance, not active ancestors, after
successful standalone promotion. Ablating provenance alone must not silently
alter active execution.

## Metrics

Record separately:

- acquisition search calls per generation;
- authority verification checks per generation;
- target search calls per arm;
- active capability count;
- active capability declared cost;
- compiled-present byte length;
- ledger event count;
- provenance pointer count;
- reserve item count;
- exact restart text/digest equality;
- protected consequence replay digest;
- authority/verifier identities;
- ablation outcome.

Search cost and verification cost must not be merged into one flattering
number.

## Pass gates

The probe passes only if every condition holds:

1. G1 search is exactly `10`.
2. G2 search is exactly `3`.
3. G3 acquisition search is exactly `0`.
4. A, B, the dependent composite, and the standalone composite are each checked
   under the declared finite authority where applicable.
5. Re-minimisation reduces ACTIVE from three items to one.
6. Protected source consequences are unchanged after contraction.
7. Restart from the contracted present is exact and history-free.
8. WARM target search is strictly below COLD.
9. WARM and COLD reach the same exhaustively verified target semantics.
10. RAW_HISTORY and SHAM do not receive the warm shortcut.
11. Standalone-composite ablation restores the exact cold search cost.
12. The reserve negative control prevents deletion when independent future
    decoder recovery is declared.
13. Frozen V1 regression tests remain green.

## Failure and named obstruction

The experiment fails closed.

If independent re-certification cannot justify a standalone composite, emit a
named obstruction identifying the failed authority or consequence check.

If contraction changes a protected consequence, emit a re-minimisation
obstruction with the smallest separating input.

If WARM does not beat COLD, classify the outcome as accumulation-only and record
the exact cost equality or regression.

If RAW_HISTORY or SHAM matches WARM, reject the causal compounding claim.

If ablation does not restore cold cost, reject causal attribution to the
compiled composite.

No failing gate may be weakened after observing the result.

## Implementation boundary

The first slice adds only:

- one focused experimental module;
- one focused test module;
- one GitHub Actions workflow;
- one evidence record generated after measurement.

It does not add a generalized V2 runtime role framework, alter QCK, alter V1
promotion semantics, modify frozen branches, or build the Lean/ARC adapters.

If the probe passes, the next slice may extract the minimal general runtime
transition for independently re-certified composition and automatic
re-minimisation. If it fails, the named obstruction determines the next move.

## Claim boundary

A passing experiment warrants only:

> Within the declared finite capability spaces, exact structural transport,
> authority boundary, and controls, independently acquired verified
> capabilities can be composed and independently re-certified into a smaller
> compiled active present that reduces acquisition search on unseen relabeled
> instances; matched sham, raw-history, and ablation controls preserve causal
> attribution.

It does not establish universal transfer, open-ended self-improvement,
automatic ontology invention, universal composition optimality, or a complete
runtime realization of QCK maintained reserve.
