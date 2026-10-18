# Prospective cross-source applicability V1 — frozen before source inspection

Date: 2026-10-19 (NZ). Predecessor: RealityGraph `c9244415172857d09132fefb30f42fb07ddacaea`.

## New external native source

Repository: `python-attrs/cattrs`; PR **#788**. Selection was based on PR metadata only, before inspecting code or tests.

- Base commit: `b3fb197563bd784adcbe7a385bf7d414a9c82829`
- Author head: `ff4682ad7a6d180feed4a527f8e5059afeb02432`
- Metadata title: Inherit omit_if_default when generating dict unstructure hooks
- Existing training authority: `python-attrs/attrs#1593`, acquired observation run #39096734354.
- Previously exposed failed future: `tox-dev/tox#4168`, excluded from this new prospective experiment.

## Precommitted determination

1. From base vs author head, select lexicographically first modified/added `test_*.py` or `*_test.py`. Derive changed test nodes by AST comparison. If no changed test file/nodes, status UNKNOWN_NOT_ADMITTED, not a substitute.
2. Overlay *only* the exact author-head selected test into a checkout of the original base. Execute native pytest on the mechanically derived changed node(s). Nonempty tests, at least one assertion failure, and zero collection errors are required.
3. **Applicability must be independently warranted:** changed native test presents a direct one-argument Boolean classifier assertion on parametrized cases, production callable resolves into base-source production, and unchanged primitive one-step projection grammar from attrs yields a nonempty licensed consequence class. No imported source-specific attribute names.
4. If licensed, produce exactly one minimal repair through the unchanged constructor. Run protected nodes twice, full selected author-test file, physical withdrawal and byte-exact restoration.
5. Only a native repair success earns a new source-bound applicability witness; then independently check typed finite CLC transport and FLASH durable replay. Otherwise preserve negative or UNKNOWN; **do not transfer attrs finite case identifiers** to cattrs.
6. No new candidate family, alternate PR, target-specific grammar, post-outcome freeze alteration, unrecorded retries, or claimed G2.
7. Retain a machine-readable result, git identities, execution logs and raw counts. Never treat a green workflow alone as positive scientific evidence.

## Qualification boundary

This experiment is permitted to return UNKNOWN or qualified negative. It is **not** a preregistered proof that a Boolean-classifier method applies to cattrs; metadata suggests a different functional mechanism, and that is scientifically valuable.

`WARRANTED_BOUNDED_CROSS_SOURCE_G2` requires the full unchanged native causal repair and independently checked applicability. A CLC finite proof alone cannot promote it.
