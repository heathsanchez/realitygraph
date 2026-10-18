# Passing-control census result — 19 October 2026

## Qualification

- Frozen protocol commit: `57d6282d06ba5ff8c6e590944337126b94955e0e`
- Qualified code: `d2dce559d1f1462049bee4c68132dcbaf205a218`
- GitHub Actions: https://github.com/heathsanchez/realitygraph/actions/runs/39168712401
- Artifact 12151412698 (SHA-256 cb5159642fbd8c9c9fb58a902c665df977f19ac0a64d9e66faef538aa79d89a4)

Original cattrs production + exact author test: 2 pytest failures, 0 errors. Observation-only census retains 2 failing test nodes, 0 errors, and evaluates all 8 inner comparisons: 4 incorrect and 4 passing. Native failure was not rewritten into a success.

Exactly one observed candidate operator: remove the unexpected `renamed` key when its primitive value is `0`. Against the frozen eight observed map comparisons, this removes all four deviations and leaves each of the four originally passing outputs exactly unchanged.

**CANDIDATE_CONTROL_PRESERVED_REPAIR_UNSUPPORTED.** The source `src/cattrs/gen/__init__.py` defines `make_dict_unstructure_fn_from_attrs` as a *factory* which synthesizes functions from dynamic attribute/override policy. The frozen repair constructor requires an independently identified unique directly returned mapping into which the field operator may be inserted without altering other behavior. That gate is not established; no production repair was generated or executed. Native causal withdrawal/restoration UNKNOWN. The candidate does not establish that removal of `renamed: 0` is safe outside these exact eight observations.

G2 UNKNOWN. No held-out source selected or opened. The next experiment must be separately frozen if a factory-level policy inheritance constructor is proposed.
