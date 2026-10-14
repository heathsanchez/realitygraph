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


## Receiver-owned native requalification at the observed head

The same read-only workflow now passes the exact observed Mathlib head from
its live-source admission job into a **separate receiver-owned Lean 4.35 job**.
That job does not trust or import MathGraph's producer Python code. It checks
out the exact observed source revision, resolves the current dependencies
through Lake, derives the first scoped theorem name from the original source,
and compiles its own proof wrapper and deliberately false-attribution control
with the native Lean kernel.

At [CI #38494606080](https://github.com/heathsanchez/realitygraph/actions/runs/38494606080),
both original declarations were successfully checked at Mathlib head
`f9254e257357eb9fce947e3ac01d428e4ba11d6a` with two independently
valid false-attribution controls rejected as intended. The receiver's
[exact native artifact](https://github.com/heathsanchez/realitygraph/actions/runs/38494606080/artifacts/11863292983)
has ZIP SHA-256
`dfbd4c28f077e3f3e558ff26b860b3087cca96d35fe6b6267d3247b04159afa4`;
all 13 command logs and expected exit statuses were independently checked.
The separate [live observation artifact](https://github.com/heathsanchez/realitygraph/actions/runs/38494606080/artifacts/11863532324)
is SHA-256 `27699db7eb9ff85c40a8b7db92fa7257c26b7b330f7d92873dfa42c3f407e16e`.

**Immutable correctness and branch freshness are different statuses.**
An earlier run [#38494129918](https://github.com/heathsanchez/realitygraph/actions/runs/38494129918)
compiled both theorems and their negative controls successfully at `d20f010d…`,
but reported `UNKNOWN` because upstream `master` moved while CI was running.
Its logs are retained and SHA-audited. The corrected receiver retains an
exact-commit native snapshot when Lean checks pass and separately reports
`CHECKED_AT_LATEST_OBSERVED_HEAD_ONLY` if the first and final branch
observations agree. If the branch advances, the source-pinned proof remains
historically bounded, while current applicability becomes
`UNKNOWN_BRANCH_HEAD_ADVANCED_DURING_OR_BEFORE_REPLAY`. Missing live
observations likewise cannot promote freshness.

This remains **same-owner, independently implemented native Lean replay**,
not a proof checked by a second kernel or outside organization. No
unrestricted source parser, theorem invention, natural-language fidelity,
publisher-signature verification, whole-dependency *equivalence across
versions*, or permanent correctness warrant for a moving branch is implied.
No production authorization or public catalogue mutation occurs.
