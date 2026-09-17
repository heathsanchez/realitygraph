# ABGP Test Qualification — Normative Clarifications

Date: 2026-09-17
Branch: `abgp-preregistration-freeze-v1`
Applies to: `docs/superpowers/specs/2026-09-17-abgp-test-qualification-design.md`
Status: **REVIEW_PENDING; normative if the qualification design is approved**

These clarifications resolve ambiguities found during self-review of the pre-freeze qualification design.

## 1. `INVALID` is protocol invalidity, not hypothesis failure

A validity gate asks whether the observation can be scientifically interpreted under the frozen protocol. A scientific gate asks whether the hypothesized effect occurred.

Therefore:

- verifier/target-label leakage, namespace misuse, broken restart isolation, prohibited grammar sharing, missing required intervention cells, post-hoc relevance labels, malformed control construction, unbound priors/tie-breaks, and inferential-unit violations are `INVALID`;
- failure to beat Bayes/bisimulation controls, failure of causal ablation despite a correctly executed targeted deletion, failure to transfer, failure to recover after a correctly executed reacquisition, absent dose response, and effect/significance failures are scientific `FAIL` or `PARTIAL` according to the frozen decision rule.

In particular, a correctly executed P deletion that leaves treatment advantage intact is **not** `INVALID`; it is evidence against the causal persistence claim and therefore a scientific `FAIL`.

## 2. Every qualification fixture freezes an exact expected result

Before fixture implementation is accepted, a qualification manifest must declare for every fixture:

- `fixture_id`;
- `arm`;
- `fixture_class` = `PLANTED_POSITIVE`, `ORDINARY_EXPLANATION`, or `BROKEN_MECHANICS`;
- `expected_verdict`;
- `expected_reason_code` or exact allowed reason-code set;
- causal property planted or protocol defect injected;
- namespace/generator version.

`QUALIFIED` requires exact agreement with those frozen expectations. “Any non-PASS” is not sufficient once the fixture manifest is frozen.

Ordinary-explanation fixtures should be designed so the named explanation produces a deterministic scientific `FAIL` wherever feasible, rather than relying on accidental underpowering to yield `PARTIAL`.

## 3. Fixture identity is invisible to scientific execution

The scientific generator output, runner, arm implementations, and analysis code may not branch on fixture class, expected verdict, or expected reason.

The expected result lives only in the external qualification wrapper that compares the ordinary raw scientific result against the frozen qualification manifest after execution.

No field such as `is_planted_positive`, `expected_pass`, `broken_mechanics`, or equivalent may enter the scientific arm record or analysis path.

Where a broken-mechanics fixture injects a defect, it does so through the same public configuration/input boundary that a real protocol defect would traverse; the analyzer detects the violated invariant from emitted evidence rather than from a fixture label.

## 4. Exact type-I implementation rule

For every exhaustively enumerable small null configuration used to qualify an exact test, the implemented rejection probability at nominal level `alpha` must satisfy

`P(reject | H0) <= alpha + 1e-12`.

The `1e-12` term is numerical tolerance only, not statistical slack.

For exact McNemar/binomial, Holm, and small-state G randomization references, exhaustive comparison is required wherever the frozen reference bound is tractable.

Large DEV-only simulations may be reported as secondary diagnostics, but they do not replace the exhaustive small-state implementation check and may not be used to relax the exact rule.

## 5. Qualification-code separation

Qualification fixture generators and the qualification wrapper are methodological code and must be hash-separated from the scientific A/B/G/P generator/runner/analysis modules.

The final qualification artifact must report both code maps separately. The final scientific lock binds both, but only the scientific code map is executable on a confirmatory namespace.

A confirmatory runner must reject any attempt to load qualification fixture modules or a qualification namespace.

## 6. Final qualification condition

The methodological verdict is `QUALIFIED` only if the parent qualification design **and** all clarifications above are satisfied. Any mismatch yields `NOT_QUALIFIED` and blocks final freeze/confirmatory execution.