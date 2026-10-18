# UDM Factory prospective V2 — broadened metadata-only role freeze
Date: 2026-10-19 NZ.
Parent unchanged generalized method: commit c5bfc48a7213e47357240522bf3f51a6f99ea552, method research/udm_factory_prospective_v1/METHOD_FREEZE.md.
V1 selection negative: 36a4278cec7ffaf032a057ac4318b98846dadf5f (0/100 in jsonschema); no native outcome.
This file must be committed before ANY V2 metadata query.

## Fixed candidate universe and order
Search each of these three unrelated repositories in **the order given**:
1. `pydantic/pydantic`
2. `marshmallow-code/marshmallow`
3. `encode/httpx`
For each, fetch the first 100 closed PRs in GitHub's API updated-descending order, using `/repos/{owner}/{repo}/pulls?state=closed&sort=updated&direction=desc&per_page=100`.
Only merge-completed human-authored PRs qualify. Filter out author login containing bot or dependabot. Require title OR label to contain case-insensitive whole-word `default`, `factory`, or `inherit`. No PR body, code diff, changed file path, test contents, patches, files, comments, or issue bodies may be opened before selection.
Among all eligible candidates sort by descending merged_at; ties by ascending fixed repository index then ascending numeric PR number. The first candidate wins. If none, UNKNOWN_NO_METADATA_ROLE; no substitution.

Freeze selected repo, PR, base SHA, author head SHA, number, title, merge time and immutable selection evidence before retrieving any source.
The old factory method is unchanged. Following selection, original base production plus exact author-head mechanically changed tests must produce a nonempty native assertion failure without errors. Its original AST role match must license the frozen single sentinel-inheritance repair; absence means REJECTED_METHOD_INAPPLICABLE. Only then one patch and native double protected/full selected tests/withdrawal/restoration. No method revision or replacement task after outcomes.
No claims of G2 without independent authentic native success and causal checks. If the API exposes fewer than 100 PRs, record actual count; any API failure means UNKNOWN_SELECTION_ENVIRONMENT. Preserve all negatives and lineage.
