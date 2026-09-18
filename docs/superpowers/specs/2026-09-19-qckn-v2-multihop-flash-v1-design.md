# QCKN V2 — Multi-Hop Flash Closure V1 Falsification Design

**Status:** executable bounded falsification probe  
**Base:** \`qckn-v2-flash-closure-v1\` at \`a03310d7660ea98ac37cdeace4264e36f2a4b6ed\`  
**Branch:** \`qckn-v2-multihop-flash-v1\`

## Question

Can one verified event change a live obligation, cause that newly changed obligation to emit a separately verified capability, and then have that second capability change a different live obligation family in a later closure wave?

This is the smallest test that distinguishes:

- one-hop broadcast reuse; from
- genuine cascading consequence propagation.

## Starting point

The prior Flash Closure V1 result established:

\[
65\to23
\]

global acquisition-search calls across ten live obligations, with closure wave:

\[
(6,0).
\]

One verified standalone parity-label capability immediately discharged six already-live compatible obligations.

Multi-Hop Flash V1 keeps that exact source capability and asks for a second causal wave.

## Frozen causal chain

### Source capability C1

Reuse the independently re-certified V2 standalone capability:

\[
C_1:\text{Pair}\to\text{Label}
\]

with semantics:

\[
00\mapsto EVEN,\quad
01\mapsto ODD,\quad
10\mapsto ODD,\quad
11\mapsto EVEN.
\]

The serial source acquisition costs remain:

\[
10>3>0.
\]

### Wave-1 bridge obligation

A new disjoint four-element carrier \(\text{Pair}_B\) protects the same parity-label consequence as \(C_1\).

Cold search over the complete frozen 16-table \(\text{Pair}_B\to\text{Label}\) universe costs exactly:

\[
7.
\]

Under Flash, transported \(C_1\) must discharge this already-live bridge obligation with zero acquisition search.

### Bridge-local decoder acquisition

Only after the bridge obligation is resolved, the bridge adapter opens a second declared local capability problem:

\[
D:\text{Label}\to\text{Token}.
\]

The complete frozen portfolio contains four total maps from:

\[
\{EVEN,ODD\}
\to
\{LOW,HIGH\}.
\]

The target decoder is:

\[
EVEN\mapsto LOW,\qquad
ODD\mapsto HIGH.
\]

Its frozen enumeration places it third.

Therefore bridge-local decoder acquisition costs:

\[
3
\]

search calls in every arm.

The promoted decoder identity receives its own independent authority check.

### Newly verified hop capability C2

Once the bridge has:

1. a verified \(\text{Pair}_B\to\text{Label}\) capability; and
2. the independently verified \(\text{Label}\to\text{Token}\) decoder,

the experiment composes them using the existing V1 capability algebra:

\[
C_2^{dep}=D\circ C_{1,B}.
\]

The dependency-bearing composition is then independently attacked over the full four-element bridge carrier.

Only if it survives may a new standalone capability identity be minted:

\[
C_2:\text{Pair}_B\to\text{Token}.
\]

The standalone \(C_2\) is independently re-certified again before entering the shared active present.

Thus the second hop is not created merely because the first wave succeeded. It must earn a separate certificate.

### Wave-2 target family

Four new disjoint \(\text{Pair}'\) carriers protect the token consequence:

\[
(LOW,HIGH,HIGH,LOW).
\]

Their complete frozen 16-table \(\text{Pair}'\to\text{Token}\) candidate spaces place the correct target seventh.

Cold cost per target:

\[
7.
\]

The second-hop capability \(C_2\) must discharge all four with zero search in the next closure wave.

### Semantic controls

Three controls remain live:

1. a Wave-1 AND-label control;
2. a Wave-2 AND-token control;
3. a Wave-2 OR-token control.

Each has the same broad carrier shape but incompatible protected consequence.

The relevant propagated capability must be proposed and independently rejected under unchanged authority.

## Ten live obligations

The fixture contains:

- 2 source acquisition obligations;
- 1 Wave-1 bridge obligation;
- 4 Wave-2 downstream obligations;
- 3 semantic controls.

Total:

\[
10.
\]

## Experimental arms

### ISOLATED

The bridge and downstream games do not receive shared compiled capabilities.

Expected search:

- source: 13;
- bridge Pair→Label: 7;
- bridge local decoder: 3;
- four downstream Pair→Token: \(4\times7=28\);
- AND-label control: 2;
- AND-token control: 2;
- OR-token control: 8.

Total:

\[
13+7+3+28+2+2+8=63.
\]

### RAW_SHARED

Causal history is visible but no executable compiled capability propagates.

Expected total:

\[
63.
\]

### FLASH

Closure begins from the restarted re-minimised source present containing \(C_1\).

Expected waves:

\[
(1,4,0).
\]

Wave 1:

- bridge resolves with zero search via \(C_1\);
- Wave-1 semantic control rejects \(C_1\).

Bridge then acquires decoder D at search cost 3, composes, independently re-certifies standalone \(C_2\), and inserts \(C_2\) into the shared present.

Wave 2:

- four downstream token games resolve with zero search via \(C_2\);
- Wave-2 semantic controls reject \(C_2\).

Wave 3:

- no new consequential state change; fixed point.

Expected FLASH total:

\[
13+0+3+0+2+2+8=28.
\]

Expected avoided search:

\[
63-28=35.
\]

### SHAM_FLASH

A type-compatible but semantically wrong \(C_1\) is inserted.

It must not solve the bridge.

All obligations remain cold.

Expected total:

\[
63.
\]

### ABLATION

The valid source standalone composite is removed before closure.

The bridge cannot enter Wave 1 by shared capability, so the cascade never begins.

Expected total:

\[
63.
\]

## Important causal requirement

The second-hop capability \(C_2\) MUST NOT exist before the bridge is resolved.

It must be constructed only from:

- the bridge's verified Pair→Label capability;
- the separately verified local decoder.

The evidence must record the exact bridge event/certificate that enabled \(C_2\).

This prevents the experiment from degenerating into two independent preloaded capabilities.

## Closure algorithm

The bounded engine operates in rounds.

For each round:

1. exact-restart the current CompiledPresent;
2. test each untried active capability against each compatible unresolved obligation;
3. authority-check transported candidates;
4. resolve any obligations whose transported candidate survives;
5. process any newly triggered bridge-local acquisition;
6. independently verify any newly composed capability;
7. promote/recompile new standalone capabilities into the shared present;
8. begin the next closure round;
9. stop when no obligation resolves and no new capability is promoted.

Expected consequential changes by round:

\[
(1,4,0).
\]

## Metrics

Record separately:

- source acquisition search;
- bridge search;
- bridge-local decoder search;
- downstream search by game;
- global search by arm;
- authority checks by stage and arm;
- closure change counts;
- promoted capability count by round;
- exact capability lineage \(C_1\to C_{1,B}\to D\to C_2\);
- search calls avoided;
- semantic-control rejections;
- exact endpoint digest;
- exact restart;
- active capability IDs after each promotion;
- prior serial V2 and one-hop Flash regressions.

## Pass gates

The probe passes only if:

1. ten obligations are live;
2. inherited source acquisition remains \(10>3>0\);
3. ISOLATED total search is exactly 63;
4. FLASH total search is exactly 28;
5. FLASH avoids exactly 35 search calls;
6. closure change counts are exactly \((1,4,0)\);
7. \(C_2\) does not exist before Wave 1 bridge resolution;
8. bridge-local decoder acquisition costs exactly 3;
9. dependent \(C_2\) composition retains dependencies until independent re-certification;
10. standalone \(C_2\) receives its own certificate and authority check;
11. four Wave-2 targets resolve with zero search only after \(C_2\) promotion;
12. all three semantic controls reject inappropriate propagated capability;
13. RAW_SHARED = 63;
14. SHAM_FLASH = 63;
15. ABLATION = 63;
16. all arms end at identical protected verified semantics;
17. restart is exact;
18. inherited one-hop Flash and serial V2 tests remain green;
19. inherited V1 regression suite remains green.

## Claim boundary

A pass warrants only:

> Within the declared finite capability family, a verified capability can reclose one already-live obligation, that changed obligation can then emit a separately verified new capability, and the new capability can reclose a different already-live obligation family in a later propagation wave. Raw shared history, sham capability, semantic controls, and source-capability ablation do not reproduce the cascade.

It does not establish unrestricted heterogeneous graph propagation, asynchronous distributed closure, universal cross-domain transfer, autonomous generation of arbitrary capability types, or open-ended self-development.
