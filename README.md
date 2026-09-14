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

A restart that discards the derived decoder but retains only .mg can rebuild the decoder from the retained batch without repeating experiment search. For the four training families the rebuild requires 52,034 predictions rather than reconstructing the whole 152,369-prediction consequence field.

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

World A starts with all 256 elementary binary radius-1 world-laws as live hypotheses. The learner is not told which law is true.

It evaluates every 8-cell experiment against every possible law:

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

## Verify

    python -m unittest discover -s tests -v
    python demo.py
    python field_demo.py
    python meta_world_demo.py

CI runs all four on every push.
