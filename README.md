# RealityGraph

**Turn verified consequence into reusable intelligence.**

RealityGraph is deliberately small:

    raw world -> local kernels / hypothesis field -> verifier/consequence
                                  |                       |
                                  v                       v
                             causal ledger -> compressed .mg

The kernel is:

    MOVE -> COLLIDE -> SHIFT -> KEEP -> REPEAT

- **Move**: make the cheapest useful construction or action.
- **Collide**: meet independently grounded consequence.
- **Shift**: change only what that collision warrants.
- **Keep**: retain only what changes future reach; preserve unresolved alternatives.
- **Repeat**: begin from the changed present.

## Predictive consequence fields

Run:

    python predictive_field_demo.py

RealityGraph can now apply the same consequence-first discipline to noisy binary prediction rather than only exact finite identification.

A predictive field is computed once:

    rows x candidate probes -> cached probe field

The learner then:

    discover thresholds on train groups
        -> collide with independent calibration groups
        -> preserve the best surviving alternatives
        -> backward-delete probes that no longer earn their place
        -> compile a tiny signature decoder
        -> touch sealed groups once

The objective is consequence-specific rather than environmental identity. Candidate probes may be arbitrary measurable properties: local image regions, morphology, threshold persistence, symmetry, template residuals, ratios, or any other deterministic observation.

Selection is driven by held-out log loss; AUC, worst-group log loss, and maximum group harm are reported as diagnostics. A caller may also provide an existing baseline probability for every row. Unsupported compiled signatures then fall back to that present rather than manufacturing certainty.

The sealed certificate is intentionally allowed to reject a model that looked perfect during discovery and calibration. The demo includes a site-specific trap that is calibration-perfect but reverses on sealed groups; RealityGraph marks it `accepted=False`.

For the Parkinson imaging use case that motivated this path:

    scan                           -> empirical state
    image property                 -> probe
    property value                 -> observation
    pathologic / normal            -> consequence
    hospital / acquisition regime  -> group

The purpose is not to guess comma length, posterior uptake, or a neural architecture in advance. Generate a broad lawful probe field, let positive/negative consequence nominate the separators, and retain only distinctions that survive independent environments.

## Real measured datasets

Run:

    python real_data_demo.py

RealityGraph now audits **8 live measured UCI datasets** spanning biology, chemistry, transport, aerodynamics, radar, sonar, and hydrodynamics:

- Iris measurements
- Wine chemistry
- Auto MPG
- NASA Airfoil Self-Noise
- Abalone physical measurements
- Ionosphere radar
- Sonar returns
- Yacht hydrodynamics

All eight sources are CC BY 4.0 UCI datasets. Their exact upstream bytes are SHA-256 pinned in `realitygraph/empirical_sources.py`; an upstream change is therefore a hard verification failure, not a silent experiment change.

On the frozen green run:

    datasets                         8
    measured rows                 7,273
    declared features               137
    observational classes          7,269
    identity UNKNOWN rows              7
    identity field predictions    72,847
    retained identity probes          26
    target field predictions      72,893
    retained target probes            21
    target correct                7,273
    target UNKNOWN                    0
    target wrong                      0

The empirical kernel does not use row IDs to manufacture distinctions. It first forms the observational quotient

    records / equality-on-measured-features

so exact duplicate measurements remain the same empirical state. On Iris and Ionosphere this produces **7 records that cannot be uniquely identified from the declared measurements**; RealityGraph returns `UNKNOWN` for those identity queries instead of inventing a distinction.

It then asks a second, weaker question:

    what is the smallest irreducible feature set that preserves
    the dataset's declared target consequence exactly?

This directly compares full environmental identity with consequence-specific state. Across these eight finite datasets, 137 declared features compress to **26 retained identity probes** and **21 retained target probes**, with **zero wrong target verdicts** on the complete frozen datasets.

This is a finite-dataset certificate, not a claim of out-of-sample predictive generalization. A target rule is retained only when exact consequence over the frozen dataset justifies it; unresolved ambiguity remains `UNKNOWN`.

## Real-world mechanism stress suite

Run:

    python real_world_demo.py

RealityGraph now includes **45 exact mechanism-grounded worlds** across **12 application categories** and **16 mechanism classes**. These are finite models of real engineering mechanisms—sensing/calibration, control, safety interlocks, energy monitoring, signal mixing, timing/phase, communications, networking, coding/parity, hardware routing, maintenance logic, and imaging correction. They are not presented as empirical field measurements.

The same generic learner handles every family. There is no thermometer-specific, relay-specific, packet-specific, wiring-specific, or controller-specific experiment selector.

On the frozen CI run:

    families                                45
    categories                              12
    mechanism classes                       16
    cold consequence predictions       180,544
    cold compile extra predictions           0
    candidate actions                     1,128
    retained separating actions             244
    action compression                     4.62x
    fresh hidden worlds solved               360
    warm experiment-design predictions         0
    warm hypothesis-scan predictions           0
    restart decoder predictions           43,315
    restart vs cold field                  4.17x
    ledger events                              45
    retained .mg bytes                     3,794

Cold compilation now reuses the already-computed consequence field directly:

    consequence field
        -> quotient candidate actions
        -> choose separating batch
        -> backward-delete redundant probes
        -> build signature decoder

so a cold compile performs **zero additional model predictions** after experiment design.

Every retained batch is also checked for irreducibility: removing any retained probe must merge at least two previously distinguishable worlds. The 45 families include gain/offset calibration, polynomial sensor curves, multi-channel linear mixers, thresholds, operating windows, cyclic phase shifts, affine symbol maps, lane rotations, wiring permutations, Boolean controller tables, binary/ternary finite controllers, and parity/LFSR-style feedback.

Eight fresh hidden parameterizations are then drawn per family after freeze, for **360 fresh worlds**. They are solved exactly from compiled signature decoders with no experiment search and no hypothesis scan.

The measured lesson is:

> **Compute each counterfactual consequence once, retain only an irreducible separating experiment, and turn the resulting distinction into direct future capability.**

## Blind meta-world transfer

Run:

    python meta_world_demo.py

This is the strongest current experiment.

The learner receives only finite hypotheses, available actions, and predicted consequences. The generic experiment designer has no family-specific branch for lookup tables, binary affine laws, modular affine laws, local cellular dynamics, or the held-out quadratic family.

Before touching the hidden world it computes the full counterfactual consequence field **once**:

    hypotheses x actions -> predicted consequences

Every hypothesis/action consequence is paid for at most once. All later refinement is quotienting over that shared field; the predictor is not called again for the same counterfactual just because the frontier has been refined.

From that field RealityGraph designs a **joint separating batch**. The whole batch is then applied in one interaction round rather than paying for a linear observe/reason/observe loop.

Current frozen families:

    family                    hypotheses   actions   discovered batch
    opaque lookup/12              4096        12          12
    binary affine/7                256       128           8
    modular affine/17              289        17           2
    cyclic local dynamics/8        256       256           1

For those four families, the complete cold counterfactual field is:

    152,369 predictions

Once a separating batch has been exhaustively verified, RealityGraph compiles it into two layers:

    .mg source       = tiny retained separating batch
    runtime decoder  = derived signature -> hypothesis primitive

Fresh worlds in the same verified model family then require:

    experiment-design predictions = 0
    hypothesis-scan predictions   = 0
    interaction rounds            = 1

The demo solves 64 fresh hidden worlds this way.

A restart that discards the derived decoder but retains only .mg can rebuild the decoder from the retained batch without repeating experiment search. For the four training families the rebuild requires 52,034 predictions rather than reconstructing the whole 152,369-prediction consequence field: **2.93x less work** before the first new observation.

Ablating retained capability restores the cold design path.

### Held-out-after-freeze control

The fifth family is absent from memory when the test begins:

    modular quadratic/7
    343 possible laws
    7 candidate actions

The same generic machinery computes its entire 2,401-entry counterfactual field once, discovers a 3-action separating batch, identifies the hidden law in one batch round, verifies it across the full finite action set, and retains the batch.

The next hidden world from that newly encountered family starts from compiled capability:

    experiment-design predictions = 0
    hypothesis-scan predictions   = 0
    interaction rounds            = 1

In CI, hidden laws are generated from:

    github.sha + github.run_id

so the concrete hidden worlds are chosen only after the tested commit already exists.

This is still a bounded finite experiment. It does **not** establish universal system identification or autonomous ontology invention. It establishes a narrower, testable claim:

> **Compute the consequence field once. Move model discrimination off the linear interaction path. Verify the smallest separating experiment. Compile it. Never pay for that discrimination again unless consequence forces it.**

## Compounding field demo

Run:

    python field_demo.py

World A starts with all 256 elementary binary radius-1 world-laws as live hypotheses. The learner is not told which rule is true.

It evaluates every 8-cell experiment against every possible rule:

    256 candidate experiments
    x 256 possible world-laws
    = 65,536 internal predictions

The generic field discovers a perfect separator. One real observation collapses 256 lawful worlds to one. The separating probe is verified against the entire declared family and compiled into .mg.

A different World B inherits the probe instead of searching again:

    cold identification = 65,792 internal predictions
    inherited           = 256 internal predictions
    reduction           = 257x

## Ledger and .mg

    Ledger = immutable causal evidence
    .mg     = compressed consequential present

Every consequential change is an event in a content-addressed causal DAG. Concurrent edits are preserved rather than resolved by last-write-wins. Revocation removes only versions it causally observed.

The live .mg remains small because history is not cognition:

    event DAG -> merge -> verify -> compress -> .mg

## Trust boundary

A proposer may be symbolic search, an LLM, a human, another kernel, or another .mg. It is not trusted.

    proposal != truth
    verified consequence -> earned structure

## Verified language-growth closure v1

Run:

    python verified_language_growth_closure_v1.py

The `verified-language-growth-closure-v1` branch qualifies a **bounded recursive developmental loop** over exact finite fixtures.

The old representational language is not allowed to grow merely because search failed. Expansion is licensed only by typed `UnknownExpressivity` evidence carrying both a completeness certificate for the declared old language and an independently replayable no-resolution certificate. `UnknownSearch` cannot expand the grammar, and `UnknownChoice` remains unresolved unless later evidence orders the alternatives.

Generation 1 exhausts the four Boolean functions available to the old `x`-only observer language, certifies that parity is not expressible there, and then searches a declared lower NAND substrate. It admits the smallest verified extension found by compositional depth, `nand-d3-0110`, restarts it exactly, reuses it on sealed future inputs with zero new grammar search, survives exhaustive finite attack, composes with another retained capability, and loses the earned reach again under ablation.

Generation 2 begins from the changed present. It exhausts all 16 stateless Boolean denotations of the current pair, certifies that the required history-sensitive distinction is absent, and then admits a verified two-state Moore-machine observer whose constructor and compiled capability explicitly depend on the Generation-1 capability. Ablating G1 transitively invalidates G2; ablating only G2 preserves G1.

The dedicated CI gate also rejects stale certificates, extensionally duplicate sham growth, unresolved search masquerading as expressivity failure, and unsupported closure. A green qualification emits:

    PASS_VERIFIED_LANGUAGE_GROWTH_CLOSURE_V1
    CLOSED_BOUNDED

This claim is deliberately narrow. It establishes recursive verified language growth for the declared finite grammars, substrates, carriers, verifiers, attacks, and two-generation qualification. It does **not** establish open-ended autonomous ontology invention, universal adequacy, unbounded self-improvement, or that every future expressive obstruction can be diagnosed or repaired.

The frozen evidence record and exact claim boundary are in `docs/research/verified-language-growth-closure-v1.md`.

## Verify

    python -m unittest discover -s tests -v
    python demo.py
    python field_demo.py
    python meta_world_demo.py
    python predictive_field_demo.py
    python verified_language_growth_closure_v1.py

CI runs the unit suite and frozen demos on every push.
