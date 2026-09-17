# ABGP Test Qualification V1 — Evidence Record

Status: **DEV/QUAL HARNESS QUALIFIED / END-TO-END IMPLEMENTATION QUALIFICATION PENDING / NOT CONFIRMATORY EVIDENCE**

> Scope correction, 17 September 2026: earlier wording used `QUALIFIED` too broadly. The qualification run below validates the statistical/synthetic-fixture harness, replay, exact-reference checks, and namespace firewall. It does **not** establish that every scientific arm is implemented end to end, and it does not establish power for every complete arm-level PASS event.

This record binds the pre-freeze DEV/QUAL harness evidence on branch `abgp-preregistration-freeze-v1`. It does **not** report A/B/G/P confirmatory results. `ABGP-CONFIRM-v1` was not derived, inspected, or executed.

## Observed harness-qualification run

- Qualification/workflow head: `2ae1b0a96ebcff97f3f003d734cb991feaceddd3`
- GitHub Actions run: `35183954190`
- Job: `105081887960`
- Result: `SUCCESS`
- Full regression: **200/200 tests passed**
- Synthetic qualification fixtures: **21** total
  - planted positive: **4**
  - ordinary explanation: **13**
  - broken mechanics: **4**
- Every frozen fixture matched its expected analyzer/validity outcome.
- Independent statistical-reference audit: `PASS`
- `confirmatory_namespace_used=false`
- `confirmatory_namespace_accessed=false`

The CLI emitted `ABGP_QUALIFIED`. In this corrected record, that token is interpreted narrowly as **DEV/QUAL harness qualification** only.

## Qualification artifact

- Evidence artifact name: `abgp-dev-qual-v1-evidence`
- Artifact ID: `10481661109`
- Artifact ZIP SHA-256: `68177694b0eb6a03a393fdb6777a34d4979fa136a1fe03ce2e2fbfba6af52631`
- `abgp-qualification-summary.json` SHA-256: `4e69329d127381661cc6ce49fffdbecc5c84e621efe0ba7efdbbd43d81517bcf`
- Internal qualification digest: `e1e01c892e1006bc68b507865a429a733a168cb3156e57815ba57dac6c6a9206`

These hashes preserve the original evidence exactly. The correction changes its interpretation, not the recorded bytes.

## What the harness evidence supports

The DEV/QUAL suite supports the following narrower claims:

- exact paired-test and Holm analysis plumbing executes deterministically;
- the B 36-component IUT analysis path is exercised on synthetic/frozen fixture inputs;
- the world-blocked G statistic and exact DP agree with independent brute-force/reference calculations;
- planted-positive, ordinary-explanation, and INVALID fixtures are routed through the intended analyzers and produce their frozen expected outcomes;
- replay is deterministic;
- the confirmatory namespace remains inaccessible.

It does **not** by itself establish:

- that A's full information-matched Bayesian control is implemented end to end;
- that B genuinely recovers protected structure across independently generated grammars — the current DEV generator still contains mechanics placeholders for recovered order and posterior/bisimulation control outcomes;
- that G's joint within-world label exchange is design-level exchangeable under the intended null;
- that A/P candidate episodes are independent at their earliest shared stochastic ancestor;
- that P's complete ordinary-control and deletion/reacquisition path is qualified end to end;
- that the A/P reported power numbers equal the power of the complete multi-control plus hard-gate PASS events.

## Review-candidate inferential units and power calculations

These counts remain `REVIEW_PENDING`. The figures below are calculations under the current candidate models, not frozen sample-size decisions and not uniformly complete-arm PASS power.

| Arm | Candidate unit / dependence handling | Candidate n | Effect floor | Reported calculation | Correct interpretation |
|---|---|---:|---:|---:|---|
| A | proposed independent acquisition → separately seeded sealed-future episode | 4,096 | 0.05 | 0.8252540787 | Paired-test power across the declared discordance envelope; **not** yet complete-arm PASS power. Earliest-shared-ancestor independence still requires audit. |
| B | ordered acquisition→transfer world pair; 4 interventions nested; 12 directions × 3 controls = 36 IUT components | 1,015/direction = 12,180 | 0.15/component | 0.8005982642 | Dependence-agnostic lower bound for simultaneous rejection across the 36 IUT components. Recompute the complete PASS event after real recovery/control paths and all gates are in place. |
| G | independent world; one joint relevance-label exchange across all nonzero doses | 421 | 0.15 max-dose gap | 0.8012420003 | Conservative max-dose-only power under the proposed world-blocked paired model. Numerical reference checks pass; exchangeability justification remains open. |
| P | proposed independent acquisition → serialize → hard restart → fixed four-probe future episode; probes collapse to one binary outcome | 4,096 | 0.05 | 0.8252540787 | Paired-test power across the declared discordance envelope; **not** yet complete-arm PASS power. Earliest-shared-ancestor independence and complete control path still require audit. |

`α=.0125` is used as a conservative component threshold derived from the four-arm familywise procedure. It is **not** an extra multiplicity correction across B's 36 intersection–union components.

## Statistical reference qualification

The numerical implementations were cross-checked against independent finite references:

- exact McNemar/binomial reference cases: **45**
- Holm reference-grid cases: **625**
- legacy weighted-G exact-sign cases: **114**
- world-blocked G exhaustive-sign cases: **346**
- maximum absolute scientific/reference discrepancy: `2.7755575615628914e-17`

For G this establishes **calculation agreement only**. Freeze still requires a design-level argument that, under H0, the entire within-world outcome vector is invariant to the joint relevance-label exchange, including any generation, selection, or stopping steps.

## Outstanding pre-freeze requirements

1. **A/P earliest shared stochastic ancestor.** Trace each candidate inferential unit through all upstream sampled worlds, grammars, acquisition pools, constructors, and other random objects. Distinct future seeds or hard restarts alone are insufficient.
2. **A information-matched Bayesian baseline.** Verify end to end that the Bayesian-optimal baseline can condition on exactly the same permitted constructor-visible observations/messages as the verifier condition, with no hidden information advantage.
3. **B real recovery and ordinary-explanation controls.** Replace mechanics placeholders with actual cross-grammar recovery and posterior/bisimulation-control execution, preserving the agreed 12-direction structural-intervention design.
4. **B complete PASS power.** Once item 3 is real, recompute power for the complete declared B PASS event, including protected-order agreement, effect floors, and all hard gates.
5. **G exchangeability.** Supply and audit the joint within-world exchangeability argument under H0.
6. **P restart/deletion boundary.** Audit the retained object as the sole cross-restart state, label-free applicability, zero source/search/verifier/reconstruction pathways, deletion back to within 2 pp of cold, and reacquisition through the preregistered acquisition procedure.
7. **A/P complete PASS power.** Recompute power for the actual multi-control plus hard-gate decision rules after the final implementation is fixed.

## Current lock boundary

The design manifest and analysis plan remain `REVIEW_PENDING`, and `confirmatory_execution_enabled=false`. No result in this record authorizes a scientific freeze or confirmatory execution.

Do not mark the study `FROZEN` until every agreed requirement maps to a concrete implementation path and auditable evidence, the remaining methodological assumptions are justified, and power is recomputed for the actual complete PASS rules.

Any change to hypotheses, effect floors, source-distinctness, inferential units, or PASS criteria must return to joint scientific review rather than being treated as an implementation clarification. Any eventual post-freeze scientific change requires a new preregistration version and fresh confirmatory namespace.
