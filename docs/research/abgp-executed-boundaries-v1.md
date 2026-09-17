# ABGP executed boundaries: implementation receipt

Status: **executed DEV mechanism tests; scientific freeze remains blocked**.

This change replaces same-process restart demonstrations with a separate invocation image and turns several unsupported positive checks into falsifiable execution tests. It does not amend the normative preregistration, thresholds, hypotheses, sample sizes or confirmation authorization.

## Executed P boundary

`executed_p.py` launches a fresh `python -I -S` process for each phase, in a newly created directory containing only its fixed worker image and bootstrap. Acquisition, structural invocation, and posterior-only invocation have different worker images. The structural invocation image has no acquisition implementation, source-example API, or candidate-language search. Its only operations are fixed lookup, targeted deletion and access-control probes.

The Linux seccomp allowlist is loaded before the experiment payload is read. The default action denies syscalls not explicitly admitted. Open/read-by-path, network sockets, child creation, exec, cross-process memory and io_uring are not admitted. Inherited descriptors are closed and the environment is reduced to fixed locale/timezone settings. Lack of Linux/libseccomp or a failed filter is an error, never a fallback. This is a boundary for the fixed declarative interpreter, not a claim of a universal sandbox for arbitrary native code.

Actual probes attempt file reads, file writes, raw libc open, socket creation, fork, exec and inherited-descriptor reads. Separate tests attack extra source/cache/target fields, corrupt object bytes and a missing sandbox library. The source object is removed by an executed lineage-deletion operation; the returned state is passed to a new invocation process. Reacquisition re-enters a separate acquisition image. Outcomes are scored in the parent against the original truth, not against the retained object's own declarations.

The source-policy model is deliberately the existing finite family of 24 permutations and four fixed contexts. Exhaustive execution gives: retained 24/24, cold 1/24, deleted 1/24, reacquired 24/24. The same-information exact posterior ALSO gives 24/24. Posterior weights, not a structural capability object, cross that control's restart. It optimizes all-four success; choosing the same tied marginal action four times would incorrectly give zero whole-episode success.

**Interpretation:** process isolation, invocation, deletion and reacquisition are now executed. This entire small family is explained by ordinary posterior retention; it is not positive evidence for the stronger P claim or for source-distinct transfer.

## Ancestry

`ancestry.py` records fixed objects, actual draw events and executed derived operations, with explicit parent edges and digests. It detects shared stochastic grandparents hidden beneath different seed values, cross-role reuse, mutation, and foreign or missing dependencies. Equal values from distinct draws are not incorrectly treated as one ancestor.

An eight-episode DEV batch performs actual uniform draws over the 24-policy family and records the executed descendants. Its four contexts remain FIXED; they are not advertised as independently sampled source-distinct futures. The ledger establishes properties of the declared dependency graph. Sampling independence and absence of arbitrary untracked global state are separate obligations; `statistical_independence_proved` remains false. Legacy seed-field inventories no longer claim full ancestry.

## B: a real ordinary-explanation separator

The parity-blinded comparator has been replaced by exact conditioning on the source representation actually supplied. It accepts a grammar and an observation, not the hidden target world. Under the current four-state answer codecs, the source observation identifies the protected order, so the correct ordinary control matches treatment on every scored intervention. The canonical digest now normalizes sets instead of hashing unstable set repr output.

The current codecs are not promoted to independent grammar-learning mechanisms. The registered grammar-independence and bisimulation requirements remain unestablished, and runtime eligibility fails closed. No control is deliberately deprived of source evidence to manufacture an advantage.

## G: actual reevaluation and a non-tautological law audit

`executed_g.py` actually changes cell values, calls a supplied protected evaluator, and computes whether its ordering changed. Relevance is exhaustively audited over a declared finite single-cell intervention alphabet, rather than copied from annotation bits. Against the legacy world's stored target-label semantics, all 20 cells are irrelevant: two checked worlds each require 121 evaluator calls and expose a mismatch with the ten pre-assigned relevant labels. A real cell-based protected evaluator is still needed for the scientific generator.

`exchangeability.py` checks exact rational probability mass for complete paired vectors, including supplied generation/selection/stopping contexts. It rejects a concrete distribution with equal dose marginals but nonexchangeable joint outcomes. The old duplicate-output null example has been removed. A complete schedule or sorted pair identity does not certify the actual G null law; the runtime audit reports NOT_ESTABLISHED and blocks its use as scientific evidence.

## Reporting and remaining boundary

The fixture CLI now prints `ABGP_HARNESS_QUALIFIED`, not `ABGP_QUALIFIED`. Its artifact explicitly contains `implementation_qualified=false` and `complete_pass_power_qualified=false`. The old cheap P budget is labeled as serialization roundtrips with zero executed hard restarts. The legacy A/B/G/P demonstration matrix is INVALID as an executed scientific experiment; this does not retroactively alter the statistical-fixture tests.

Run:

```sh
python -m unittest discover -s tests -v
python abgp_executed_boundaries.py
```

The dedicated CI workflow uploads raw worker receipts and source hashes. It succeeds only when access-control attacks are blocked, the independently scored finite control outcomes match, and legacy demonstrations are refused scientific eligibility. A green job is not an ABGP hypothesis result.

Still required before freeze: executed A acquisition under the agreed information boundary; source-distinct P capabilities not explained by the retained-posterior control; genuinely independent B grammar generators and their scoped exact controls; a cell-based G evaluator with a justified actual null sampling law; normative-text reconciliation and reviewed complete-PASS power assumptions. These are not replaced by status flags or treatment-favouring fixtures.
