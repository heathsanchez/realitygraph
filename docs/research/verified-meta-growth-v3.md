# Verified meta-growth V3 — bounded evidence record

## Status

`verified-meta-growth-v3` qualifies a bounded meta-developmental layer above the V2 generic developmental executor.

The exact sealed CI run for the code-complete V3 mechanism is:

- workflow run: `35152347303`
- job: `104983465117`
- tested commit: `c5e0b3526acfa84a62fc7b9960db8c0272dbbe40`
- full regression suite: `134/134` tests passed
- verdict: `PASS_VERIFIED_META_GROWTH_V3`
- closure: `CLOSED_BOUNDED_META_GROWTH_V3`
- closure certificate: `8424f0a7b4924126486e69d45a45501fb4908e927b5fd27c7e33c5912a9e5f12`
- evidence artifact: `10469810700`

The artifact contains the canonical JSON qualification summary and the standalone qualification log.

## What V3 adds over V2

V2 established that one generic executor can grow a bounded chain of object-level capabilities when the current language is completely characterized and independently certified insufficient.

V3 asks a different question:

> Can the system learn which *kind of developmental repair* is warranted by a structural obstruction, independently requalify that developmental rule, persist it, and later reuse it without searching the competing repair families again?

The answer is yes for the declared finite qualification.

The generic meta transition is:

    complete current language
        -> exact obstruction fingerprint
        -> promoted repair-rule lookup
        -> otherwise evaluate the frozen applicable repair portfolio
        -> object-level V2 executor verifies/adopts the selected repair
        -> attack + sealed future evidence
        -> candidate meta-rule
        -> independent calibration
        -> promoted meta-rule
        -> exact restart
        -> later rule hit or cold fallback

The meta executor does not import the V3 qualification fixture and contains no dispatch on strategy IDs or fixture names.

## Exact obstruction identity

V3 introduces a canonical finite obstruction fingerprint. The fingerprint is invariant to surface relabeling while preserving incidence multiplicity and distinguishing non-isomorphic obstruction structures. Authority and verifier identity are included in the boundary, so evidence cannot silently migrate across a changed verifier or authority.

The V3 qualification uses two structurally different obstruction families:

- **C — observation collision:** the winning repair family is `add_observable`.
- **T — temporal collision:** the winning repair family is `add_finite_memory_2`.

Acquisition, independent calibration, and untouched future episodes use disjoint surface carriers inside each family but recover the same exact obstruction fingerprint. The two families have different fingerprints and therefore learn different developmental moves.

## Frozen repair portfolio

The qualification fixes a finite portfolio before evaluation. The meta executor evaluates applicable repairs from the identical immutable parent state on the cold path. Portfolio ordering is not authority: identity is explicit and the portfolio digest is order independent.

For the temporal family, the qualification characterizes finite-state alternatives rather than providing a hand-picked witness:

- complete two-state Moore-machine repair space: `64` machines
- complete three-state Moore-machine repair space: `5,832` machines

Both the two-state and three-state families can produce a valid repair in the temporal fixture. The two-state repair is selected because it is the cheaper successful structural move under the declared frozen cost ordering, not because of strategy name or enumeration order.

Equal-ranked successful repairs remain `UNKNOWN_CHOICE`.

## Meta-rule lifecycle

A single successful acquisition episode does not create an active reusable rule.

The lifecycle is:

    acquisition success
        -> CANDIDATE repair rule
        -> independent calibration success under the same exact boundary
        -> PROMOTED repair rule
        -> future applicability or later REVOCATION

Calibration disagreement blocks promotion. Revocation disables active reuse but preserves lineage evidence.

The sealed qualification promotes exactly two distinct repair rules:

- `repair-rule-17c21a92b987e8d54542 -> add_observable`
- `repair-rule-3a81e97bd18404c0f729 -> add_finite_memory_2`

## Prospective reuse

After promotion and an exact cold restart, untouched future episodes hit the retained repair rules directly.

For C:

    future strategy                 add_observable
    repair-rule hit                 yes
    repair-portfolio search calls   0
    competitor strategy calls       0
    object future grammar search    0

For T:

    future strategy                 add_finite_memory_2
    repair-rule hit                 yes
    repair-portfolio search calls   0
    competitor strategy calls       0
    object future grammar search    0

The future object-level capability IDs differ from their acquisition capability IDs. V3 therefore does not simply copy the old task solution: it reuses the developmental strategy and synthesizes a new independently verified object capability for the new episode.

Each future capability survives its frozen object-level attack and sealed future check.

## Exact persistence and causal ablation

`MetaSnapshot` serializes the object-level `DevelopmentalState` and the meta-level `MetaMemory` together with authority and portfolio identity. Restart reconstructs both byte-exactly without needing fixture or strategy objects.

Targeted repair-rule ablation is causal:

- removing the C repair rule restores cold portfolio search on the C future and rediscovers `add_observable`;
- removing the T repair rule restores cold portfolio search on the T future and rediscovers `add_finite_memory_2`.

Thus the zero-search future behavior is caused by the retained meta-rule rather than by hidden task state or an altered fixture.

## Negative controls

The sealed qualification requires all of the following to fail closed:

- wrong obstruction fingerprint cannot reuse a promoted rule;
- stale authority cannot reuse a promoted rule;
- stale verifier cannot reuse a promoted rule;
- wrong portfolio identity cannot reuse a promoted rule;
- incomplete current-language search yields `UNKNOWN_SEARCH` and no repair calls;
- partial repair-portfolio evaluation yields `UNKNOWN_SEARCH` rather than selecting the best checked candidate;
- tied successful repairs yield `UNKNOWN_CHOICE` with no structural mutation;
- inherited V2 recursive language-growth qualification remains green.

These controls are part of the standalone V3 summary and are asserted by CI.

## Warranted claim

The warranted claim is deliberately bounded:

> **Within the declared finite worlds, exact obstruction representation, frozen repair portfolio, verifier/authority boundary, calibration protocol, attacks, and resource envelope, RealityGraph can learn a structural mapping from an obstruction class to a repair family, independently requalify and persist that mapping, exactly restart it, and reuse it on untouched structurally equivalent future episodes with zero repair-portfolio search while still constructing and independently verifying new task-specific capabilities.**

This can reasonably be called **bounded verified meta-growth** or **verified learning of how to grow**.

## Explicit non-claims

V3 does **not** establish:

- open-ended meta-growth;
- autonomous invention of arbitrary substrate families from no declared primitives;
- representation-independent or universal obstruction identity;
- universal repair optimality;
- universal cross-domain transfer;
- learned verifier authority or terminal values;
- unbounded recursive self-development.

A failed or incomplete boundary remains typed `UNKNOWN` or a named bounded obstruction rather than being promoted into a stronger claim.
