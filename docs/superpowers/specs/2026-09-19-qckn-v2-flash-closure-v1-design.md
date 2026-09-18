# QCKN V2 — Flash Closure V1 Falsification Design

**Status:** executable bounded falsification probe  
**Base:** \`qckn-v2-compounding-falsification-v1\` at \`a78cb2b83ca792225df1b7cfe1a1f3b62a8f136c\`  
**Branch:** \`qckn-v2-flash-closure-v1\`

## Question

Does a verified result acquired in one live obligation immediately reduce the remaining search of other compatible live obligations when all obligations share one consequence-governed compiled present?

This is not a parallelism benchmark. It tests **lateral propagation**.

The serial V2 probe already established longitudinal compounding:

\[
10>3>0
\]

with independently re-certified composition and ACTIVE contraction. Flash Closure asks whether the resulting verified capability can alter several unfinished obligations before those obligations pay their planned cold search cost.

## Hypothesis

Let ten obligations be live simultaneously:

- one parity-acquisition source obligation;
- one decoder-acquisition source obligation;
- six unseen relabelled parity-label target obligations;
- two structurally nearby but semantically incompatible controls.

The two source obligations acquire the same independently verified G1/G2 capabilities from the serial V2 probe. Once both exist, the existing V1 capability algebra composes them. The composition is independently re-certified and compiled into the re-minimised present exactly as in the passed V2 falsification probe.

The Flash arm then immediately re-closes every still-live target obligation against that compiled present before any target begins cold search.

The primary hypothesis is:

\[
C_{\mathrm{FLASH}}<C_{\mathrm{ISOLATED}}
\]

under one frozen acquisition-search unit.

The expected bounded values are:

\[
C_{\mathrm{ISOLATED}}=65,\qquad
C_{\mathrm{FLASH}}=23.
\]

The exact saving is therefore:

\[
42
\]

candidate-search calls, all from six live obligations whose seven-call cold searches are cancelled by one verified composite promotion.

## Frozen obligations

### Source obligations

- G1 parity acquisition: 10 acquisition-search calls.
- G2 decoder acquisition: 3 acquisition-search calls.
- G3 composition: 0 acquisition-search calls; verification is reported separately.

The source search contribution is therefore 13 in every arm.

### Compatible live targets

Six disjoint four-element surface carriers are frozen. Each is structurally mapped to the source pair carrier but uses distinct literal tokens.

Every compatible target protects the parity-label consequence:

\[
(EVEN,ODD,ODD,EVEN).
\]

Under the complete frozen enumeration of all 16 total \`Pair' -> Label\` tables, this target appears seventh. Hence each cold compatible target costs 7 search calls.

### Semantic controls

Two additional disjoint four-element carriers use the same interface shape but different protected consequences:

- AND-label: \((EVEN,EVEN,EVEN,ODD)\), cold cost 2;
- OR-label: \((EVEN,ODD,ODD,ODD)\), cold cost 8.

The Flash composite is still proposed to these controls. The unchanged exhaustive authority must reject it, after which they fall back to their ordinary cold searches.

This tests that Flash propagation is verifier-gated rather than type-shape broadcasting.

## Experimental arms

All arms have the same ten obligations, target candidate universe, source acquisition costs, target authority, and protected consequences.

### ISOLATED

No shared compiled capability reaches unfinished target obligations. All eight targets search cold.

Expected total search:

\[
10+3+6(7)+2+8=65.
\]

### RAW_SHARED

The source causal history is visible, but no executable compiled composite is inserted into the target active present.

Expected search: 65.

### FLASH

The independently re-certified standalone composite is inserted into the shared compiled present and the graph is re-closed before target cold search.

Expected behavior:

- six compatible targets resolve with zero search;
- two controls reject the transported composite and remain cold;
- total search:

\[
10+3+0+2+8=23.
\]

### SHAM_FLASH

A type-compatible but semantically wrong compiled capability is propagated. Authority must reject it and every target proceeds cold.

Expected search: 65.

### ABLATION

The valid standalone composite is removed before global reclosure.

Expected search: 65.

## Flash closure algorithm

The experiment maintains a live unresolved set and a set of already-tested capability/game edges.

For each closure round:

1. restart the current CompiledPresent exactly;
2. for every unresolved game, test each previously untested active capability;
3. transport the capability only through the frozen structural carrier map;
4. run the unchanged exhaustive target authority;
5. if the transported capability survives, mark that live obligation resolved and cancel its planned cold search;
6. if it fails, retain the counterexample and leave the obligation unresolved;
7. repeat until a round produces no new resolved obligations.

The first valid composite promotion should produce closure changes:

\[
(6,0)
\]

meaning six obligations change in the first propagation round and the second round is the fixed-point check.

## Controls against weaker explanations

The probe rejects the Flash claim if any of the following occurs:

1. RAW_SHARED receives the same shortcut as FLASH.
2. SHAM_FLASH receives the same shortcut as FLASH.
3. ABLATION does not restore the isolated global search cost.
4. The valid composite solves either incompatible semantic control.
5. FLASH and ISOLATED do not reach the same exhaustively verified endpoint on every obligation.
6. Restart changes the compiled present.
7. The frozen serial V2 compounding tests regress.
8. Any frozen V1 regression fails.

## Metrics

Record separately:

- total live obligations;
- source acquisition-search calls;
- target search calls by arm;
- global search calls by arm;
- authority checks by arm;
- number of games resolved by Flash before search;
- search calls cancelled;
- closure-round change counts;
- fixed-point round count;
- incompatible-capability rejections;
- per-game cold and final search costs;
- exact endpoint digest;
- CompiledPresent digest and exact restart equality;
- active capability count after source re-minimisation;
- serial V2 provenance/ledger identity.

Search and authority work remain separate. No aggregate “work” scalar is substituted after observing the result.

## Pass gates

The bounded Flash thesis passes only if:

1. ten obligations are live;
2. source acquisition remains exactly 10 + 3, with G3 search 0;
3. ISOLATED global search is exactly 65;
4. FLASH global search is exactly 23;
5. FLASH therefore avoids exactly 42 acquisition-search calls;
6. exactly six unfinished compatible games are resolved before cold search;
7. closure change counts are exactly \((6,0)\);
8. both semantic controls reject the propagated composite and retain cold search;
9. RAW_SHARED = 65;
10. SHAM_FLASH = 65;
11. ABLATION = 65;
12. all arms end at the same protected verified semantics;
13. the Flash active present restarts exactly;
14. serial V2 and all inherited V1 tests remain green.

## Claim boundary

A pass warrants only:

> Within this declared finite capability family, one independently verified composite promotion can be propagated through a shared compiled consequence state and immediately discharge multiple already-live compatible obligations before they pay their independent search costs; raw shared history, sham capability, semantic controls, and exact ablation do not reproduce the effect.

It does not establish arbitrary cross-domain transfer, unbounded propagation, asynchronous distributed consistency, universal graph closure, or open-ended self-development.
