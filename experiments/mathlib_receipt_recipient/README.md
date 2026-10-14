# RealityGraph: independent historic Mathlib receipt recipient

**Purpose:** one bounded test of recipient-side evidence admission and selective retraction. The incoming proof *status* is never the authority. Before admitting any historical claim, the recipient independently validates its locally pinned trust-policy SHA, each exact upstream source Git blob, the authorized GitHub Actions artifact SHA-256, source-derived theorem identity, every command/log digest, expected verifier exits and positive/negative diagnostics. It imports **no MathGraph publisher code**.

This is the existing RealityGraph repository, not a new project or a modification of MathGraph Resolve v1's frozen record. The two exact artifacts are from an unchanged, successful producer workflow [#38490276564](https://github.com/metalogiclabs/mathgraph/actions/runs/38490276564); original sources are pinned Mathlib v4.35.0. CI reads byte-for-byte copies of the two original Actions ZIPs committed as SHA-pinned Base64 fixtures, independently downloads their original Mathlib source files at the frozen upstream commit, then runs the consumer offline. The fixture archives preserve exact original evidence after GitHub Actions artifact expiry; archive hashes are fixed by the receiver's separately pinned policy.

**Trust boundary:** the external policy hash must be supplied independently of any uploaded receipt (the workflow pins it); a different authorized policy is a separate decision. A self-hash does not establish source or author authenticity. Receipt admission here **does not re-run Lean**, reproduce the proof checking independently, demonstrate outside-owner organizational adoption, or establish present-day Mathlib applicability. It establishes same-owner, separate-repository and separately implemented *historical receipt transport/admission replay*, not an original proof requalification.

The suite deliberately rejects altered archive bytes, a forged producer success status, source changes, receipt/source swaps, a rehashed incorrect declaration name, and a rehashed log that omits the required source-mismatch diagnostic. A simulated, receiver-local withdrawal makes **only its dependent historical reuse stale**; the distinct Mathlib claim and historical proofs survive unchanged. A different supplied current revision makes current applicability **UNKNOWN**, not the original theorem false. Simulated withdrawal must not be reported as a real upstream event. No production mutation or authorization is performed.

The original GitHub Actions artifact links may expire; identical ZIP bytes are now committed in this isolated recipient branch and checked against the original artifact SHA-256 on every run. This is durable receiver-side retention, not an independently authenticated publisher signature or live freshness evidence.

## Observed upstream source files at Mathlib master

The recipient now also has a **separate live-source observation** step. After
qualifying the frozen historic artifacts, it independently reads the GitHub
repository and protected target branch name from its receiver configuration
(`leanprover-community/mathlib4`, default branch `master`), obtains the
current branch commit through GitHub's HTTPS repository API, and fetches the
two theorem files by that **exact commit SHA**. It verifies Git blob identities
from the API content bytes and rechecks the branch tip after observation.
The branch can advance; no claim that these observations remain current forever
is permitted.

At [CI #38493107784](https://github.com/heathsanchez/realitygraph/actions/runs/38493107784),
observed commit `d20f010dc809f2bb8f94969ccc8ed1691bad2531` was newer
than the historic `56a005855ea17e0b0958f73ec801ae140b0a1679` snapshot,
yet both exact file blobs matched. Ten additional adversarial tests passed
(**21/21** overall). The [exact observation artifact](https://github.com/heathsanchez/realitygraph/actions/runs/38493107784/artifacts/11862830795)
has ZIP SHA-256
`a468dd69ef3ce4b31b395940fc20aea8c2dcfafe3687ec5835effae128a6fd3b`.

The consumer reports `SOURCE_FILE_UNCHANGED_AT_OBSERVED_HEAD` for both files
and **`UNKNOWN_DEPENDENCY_CLOSURE_NOT_RECHECKED`** for each current theorem
warrant. A current-source file mismatch or disappearance affects only the
corresponding path; neither event proves the theorem false, nor constitutes
an authenticated publisher withdrawal. GitHub HTTPS repository authority
is not an independently verified cryptographic author signature.

Run the live observation after restoring the original offline fixtures:

```sh
python experiments/mathlib_receipt_recipient/current_source.py \
  --policy experiments/mathlib_receipt_recipient/policy.json \
  --policy-sha256 ba9313b4cf4225592dbae5bcd6bbca837d03be34d837e43267544923f3774426 \
  --artifacts experiments/mathlib_receipt_recipient/fixtures/artifacts \
  --sources experiments/mathlib_receipt_recipient/fixtures/sources \
  --output experiments/mathlib_receipt_recipient/current-source-report.json
```
