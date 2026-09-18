# QCKN V2 — Multi-Hop Flash Closure V1 Result

**Status:** PASS — bounded cascading Flash qualification  
**Branch:** \`qckn-v2-multihop-flash-v1\`  
**Qualification run:** \`35406252521\`  
**Result:** GREEN  
**Evidence artifact:** \`qckn-v2-multihop-flash-v1-evidence\` (artifact ID \`10573480309\`)

## Result

The bounded multi-hop Flash thesis passes.

One verified source capability reclosed an already-live bridge obligation. That changed bridge then produced a separately verified second-hop capability, which reclosed four already-live obligations in a different output family during the next consequence wave.

The measured closure trace was:

\[
\boxed{(1,4,0)}
\]

meaning:

1. Wave 1: one bridge obligation changed;
2. the bridge emitted one new independently re-certified capability;
3. Wave 2: four downstream token obligations changed;
4. Wave 3: no further consequential changes remained.

This is the first bounded cascade in the QCKN line rather than a one-hop broadcast reuse result.

## Search result

Global acquisition-search calls:

| Arm | Search |
| --- | ---: |
| ISOLATED | 63 |
| RAW_SHARED | 63 |
| FLASH | **28** |
| SHAM_FLASH | 63 |
| ABLATION | 63 |

Thus Flash removed:

\[
63-28=35
\]

candidate-search calls.

The reduction decomposes exactly into:

- 7 calls avoided on the Wave-1 bridge;
- 28 calls avoided across four Wave-2 downstream obligations.

The bridge-local decoder acquisition remained a genuine cost in every arm:

\[
3.
\]

So the cascade did not obtain its second hop for free by silently preloading the decoder.

## Source compounding preserved

The inherited serial V2 source sequence remained:

\[
10>3>0
\]

with independent authority checks:

\[
4,\;7,\;8.
\]

Source capability:

\`g3-standalone-parity-label-v2\`

Source certificate:

\`cert:g3-standalone-exhaustive-v2\`

No frozen V1 branch was modified.

## Wave 1

The source capability:

\[
C_1:\text{Pair}\to\text{Label}
\]

was transported to the disjoint bridge carrier.

The bridge target ordinarily costs 7 candidate searches.

Under FLASH:

\[
\text{bridge search}=0.
\]

The same capability was also proposed to the AND-label semantic control and rejected by the unchanged authority.

## Bridge-local development

Only after bridge resolution did the adapter open the local decoder problem:

\[
D:\text{Label}\to\text{Token}.
\]

The target decoder remained third in the complete frozen four-map portfolio:

\[
\text{decoder search}=3.
\]

The promoted decoder identity received its own independent authority check.

The verified bridge capability and decoder were composed through the existing V1 capability algebra.

The dependency-bearing composition remained dependency-bearing until independent exhaustive checking.

Only then was a new standalone second-hop identity created:

\`multihop-standalone-pair-token-v1\`

with new certificate:

\`cert:multihop-standalone-pair-token-v1\`.

The evidence records:

\`c2_created_after_bridge = true\`.

Therefore the second hop was causally downstream of the Wave-1 bridge change, not preloaded before closure.

## Wave 2

The new standalone capability:

\[
C_2:\text{Pair}_B\to\text{Token}
\]

entered the shared present.

Four already-live token targets that each cost 7 cold searches were then resolved with zero search in Wave 2.

Measured downstream search:

- ISOLATED: 28
- RAW_SHARED: 28
- FLASH: **0**
- SHAM_FLASH: 28
- ABLATION: 28

## Semantic controls

Three controls remained cold:

- AND_LABEL_CONTROL: 2
- AND_TOKEN_CONTROL: 2
- OR_TOKEN_CONTROL: 8

The exact rejected Flash edges were:

- \`g3-standalone-parity-label-v2 -> AND_LABEL_CONTROL\`
- \`multihop-standalone-pair-token-v1 -> AND_TOKEN_CONTROL\`
- \`multihop-standalone-pair-token-v1 -> OR_TOKEN_CONTROL\`

This shows that the cascade is verifier-gated at both hops.

## Weaker explanations rejected

### RAW_SHARED

Raw causal history did not reproduce the cascade.

\[
63.
\]

### SHAM_FLASH

A type-compatible but semantically wrong source capability did not reproduce the cascade.

\[
63.
\]

### ABLATION

Removing the valid source capability before closure prevented Wave 1, therefore prevented Wave 2.

\[
63.
\]

This restores the isolated frontier exactly.

## Endpoint equality

All arms ended at identical protected verified semantics.

The canonical evidence reports:

\`endpoint_digests_equal = true\`.

Therefore the improvement is search removal, not a weaker endpoint.

## Restart

The shared active present remained exactly restartable before and after second-hop promotion.

The final Flash present digest was:

\`3693273b0b9ebc9e6e2888ea80e9403fad376d2bac29c88494ef96d804ff01b1\`.

\`restart_exact = true\`.

## Authority accounting

Search and verification were reported separately.

Hosted authority checks:

| Arm | Checks |
| --- | ---: |
| ISOLATED | 166 |
| RAW_SHARED | 166 |
| FLASH | 104 |
| SHAM_FLASH | 172 |
| ABLATION | 166 |

No combined work scalar was substituted for the predeclared search metric.

## Regression protection

The hosted workflow ran:

- focused multi-hop Flash tests;
- one-hop Flash regression tests;
- serial V2 compounding tests;
- the inherited full RealityGraph suite;
- canonical evidence generation;
- evidence artifact upload.

Hosted result:

\[
\boxed{191/191\ \text{tests green}}
\]

## Exact gates

All multi-hop gates passed:

- TEN_LIVE_OBLIGATIONS
- SERIAL_SOURCE_COSTS_PRESERVED
- ISOLATED_GLOBAL_SEARCH_63
- FLASH_GLOBAL_SEARCH_28
- FLASH_AVOIDS_35_SEARCH_CALLS
- FLASH_CASCADE_1_4_0
- ONE_SECOND_HOP_PROMOTION
- C2_CREATED_ONLY_AFTER_BRIDGE
- DECODER_SEARCH_EXACTLY_3
- FOUR_DOWNSTREAM_ZERO_SEARCH_AFTER_C2
- SEMANTIC_CONTROLS_STAY_COLD
- RAW_SHARED_STAYS_ISOLATED
- SHAM_FLASH_STAYS_ISOLATED
- ABLATION_RESTORES_ISOLATED
- ALL_ENDPOINTS_IDENTICAL_AND_VERIFIED
- FLASH_RESTART_EXACT
- SECOND_HOP_HAS_NEW_CERTIFICATE

## Warranted claim

This experiment establishes the following bounded statement:

> Within the declared finite capability family, a verified capability can reclose one already-live obligation, that changed obligation can then emit a separately verified new capability, and that new capability can reclose a different already-live obligation family in a later consequence wave. Raw shared history, sham capability, semantic controls, and exact source-capability ablation do not reproduce the cascade.

The developmental graph therefore demonstrated a genuine bounded chain:

\[
\boxed{
\text{verified event}
\to
\text{live-state change}
\to
\text{new verified capability}
\to
\text{second live-state change}
\to
\text{fixed point}
}
\]

## Claim boundary

This does **not** establish:

- arbitrary heterogeneous cross-domain cascades;
- asynchronous distributed consistency;
- universal consequence closure;
- automatic discovery of every bridge decoder;
- unbounded cascade depth;
- autonomous authority generation;
- open-ended self-development.

The next useful falsification target is not a third synthetic hop. It is to export the same two-wave closure law into a genuinely different domain adapter while leaving the Flash controller unchanged.
