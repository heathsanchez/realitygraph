"""Finite CLC transport certificates bound to RealityGraph FLASH admissions.

The Lean kernel checks all declared finite transport laws. Python input binding,
finite table serialization, toolchain identity, and external oracle authority
remain named trusted-computing-base assumptions, NOT consequences of Lean.

No receipt is accepted merely by containing a hash or boolean; check_transport
runs the installed Lean binary on a generated, exact-claim proof at admission.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .capability import FiniteCapability


VERDICTS = frozenset(("UNKNOWN", "EQ", "DIST"))
LEAN_LIBRARY_SHA256 = "70b3eceeed69a08437d1d8da687c645ff6928d682f2930f29e559041e3f37730"
EXPECTED_LEAN_VERSION = "4.24.0"
LEAN_LIBRARY = Path(__file__).resolve().parents[1] / "research" / "clc_lean_v3" / "FiniteTransport.lean"


def canonical_bytes(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def sha(obj: object) -> str:
    return hashlib.sha256(canonical_bytes(obj)).hexdigest()


def exact_map(rows: tuple[tuple[str, str], ...], domain: tuple[str, ...],
              codomain: tuple[str, ...], label: str) -> dict[str, str]:
    if len(rows) != len(domain) or len({a for a, _ in rows}) != len(rows):
        raise ValueError(f"{label}: mapping must be total and single-valued")
    table = dict(rows)
    if set(table) != set(domain) or not set(table.values()).issubset(set(codomain)):
        raise ValueError(f"{label}: mapping does not respect the declared finite interface")
    return table


@dataclass(frozen=True)
class FiniteCLCForm:
    states: tuple[str, ...]
    tests: tuple[str, ...]
    protected: tuple[str, ...]
    outcomes: tuple[tuple[str, str, str], ...]

    def __post_init__(self) -> None:
        if not self.states or not self.tests or not self.protected:
            raise ValueError("CLC finite forms require nonempty state/test/protected carriers")
        if (len(set(self.states)) != len(self.states)
                or len(set(self.tests)) != len(self.tests)
                or len(set(self.protected)) != len(self.protected)):
            raise ValueError("CLC state/test/protected identifiers must be unique")
        if not set(self.protected).issubset(self.tests):
            raise ValueError("protected tests outside the declared test interface")
        cells = [(s, t) for s, t, _ in self.outcomes]
        if (len(cells) != len(self.states) * len(self.tests)
                or len(set(cells)) != len(cells)
                or set(cells) != {(s, t) for s in self.states for t in self.tests}):
            raise ValueError("CLC form has incomplete or duplicated evaluation table")
        if any(v not in VERDICTS for _, _, v in self.outcomes):
            raise ValueError("CLC form has an invalid verdict")

    def eval_table(self) -> dict[tuple[str, str], str]:
        return {(s, t): v for s, t, v in self.outcomes}

    def payload(self) -> dict[str, object]:
        return {"states": list(self.states), "tests": list(self.tests),
                "protected": list(self.protected),
                "outcomes": [list(v) for v in self.outcomes]}


@dataclass(frozen=True)
class FiniteCLCTransport:
    source: FiniteCLCForm
    target: FiniteCLCForm
    forward: tuple[tuple[str, str], ...]
    pull: tuple[tuple[str, str], ...]
    lift: tuple[tuple[str, str], ...]
    authority_snapshot: str
    verifier_id: str
    input_type: str
    output_type: str
    strict: bool = False

    def __post_init__(self) -> None:
        if not all((self.authority_snapshot, self.verifier_id,
                    self.input_type, self.output_type)):
            raise ValueError("CLC transport requires authority and source/target types")
        exact_map(self.forward, self.source.states, self.target.states, "forward")
        exact_map(self.pull, self.target.tests, self.source.tests, "pull")
        # total lift is a convenient finite encoding of the protected-test lift;
        # only protected source inputs have semantic obligations.
        exact_map(self.lift, self.source.tests, self.target.tests, "lift")

    def payload(self) -> dict[str, object]:
        return {"source": self.source.payload(), "target": self.target.payload(),
                "forward": [list(v) for v in self.forward],
                "pull": [list(v) for v in self.pull],
                "lift": [list(v) for v in self.lift],
                "authority_snapshot": self.authority_snapshot,
                "verifier_id": self.verifier_id,
                "input_type": self.input_type, "output_type": self.output_type,
                "strict": self.strict}

    @property
    def digest(self) -> str:
        return sha(self.payload())


def _output_index(name: str, targets: tuple[str, ...]) -> int:
    return targets.index(name)


def canonical_transport(capability: "FiniteCapability", *,
                        developmental: bool = False) -> FiniteCLCTransport:
    """Exact finite output-discrimination interface from the declared capability.

    For two finite outputs, probes are indexed consistently across X/Y/Z forms.
    Developmental mode starts with UNKNOWN source judgments; no new decisive
    target consequence is inferred without the independent FLASH native oracle.
    """
    source_states = tuple(sorted(capability.guarded_inputs))
    target_states = tuple(sorted(set(capability.execute(x) for x in source_states)))
    tests = tuple(f"probe:{i}" for i in range(len(target_states)))
    sem = {x: capability.execute(x) for x in source_states}
    outcomes_source = tuple(
        (x, t, "UNKNOWN" if developmental else
         ("EQ" if sem[x] == target_states[i] else "DIST"))
        for x in source_states for i, t in enumerate(tests)
    )
    outcomes_target = tuple(
        (y, t, "EQ" if y == target_states[i] else "DIST")
        for y in target_states for i, t in enumerate(tests)
    )
    a = FiniteCLCForm(source_states, tests, tests, outcomes_source)
    b = FiniteCLCForm(target_states, tests, tests, outcomes_target)
    return FiniteCLCTransport(
        a, b, tuple((x, sem[x]) for x in source_states),
        tuple((t, t) for t in tests), tuple((t, t) for t in tests),
        capability.authority_snapshot, capability.verifier_id,
        capability.input_type, capability.output_type,
        strict=not developmental,
    )


def compose_transports(a: FiniteCLCTransport,
                       b: FiniteCLCTransport) -> FiniteCLCTransport:
    """Construct the CLC pullback/lift composition, never silently identify forms."""
    if (a.target != b.source or a.output_type != b.input_type
            or a.authority_snapshot != b.authority_snapshot
            or a.verifier_id != b.verifier_id):
        raise ValueError("CLC transport composition requires identical intermediate form/authority")
    af, bf = dict(a.forward), dict(b.forward)
    ap, bp = dict(a.pull), dict(b.pull)
    al, bl = dict(a.lift), dict(b.lift)
    return FiniteCLCTransport(
        source=a.source, target=b.target,
        forward=tuple((s, bf[af[s]]) for s in a.source.states),
        pull=tuple((t, ap[bp[t]]) for t in b.target.tests),
        lift=tuple((t, bl[al[t]]) for t in a.source.tests),
        authority_snapshot=a.authority_snapshot, verifier_id=a.verifier_id,
        input_type=a.input_type, output_type=b.output_type,
        strict=a.strict and b.strict,
    )


def bind_transport(cap: "FiniteCapability", oracle: tuple[tuple[str, str], ...],
                   claim: FiniteCLCTransport) -> None:
    """Small, explicit Python TCB: the Lean theorem must describe this capability."""
    if (claim.authority_snapshot != cap.authority_snapshot
            or claim.verifier_id != cap.verifier_id
            or claim.input_type != cap.input_type
            or claim.output_type != cap.output_type):
        raise ValueError("CLC witness authority/verifier/type differs from admitted capability")
    guarded = tuple(sorted(cap.guarded_inputs))
    actual = {x: cap.execute(x) for x in guarded}
    if (set(claim.source.states) != set(guarded)
            or set(claim.target.states) != set(actual.values())
            or dict(claim.forward) != actual):
        raise ValueError("CLC witness state/forward map differs from executable capability")
    if (len(oracle) != len(guarded)
            or dict(oracle) != actual
            or len({x for x, _ in oracle}) != len(oracle)):
        raise ValueError("CLC witness source oracle is not the exact exhaustive capability oracle")
    # The protected target tests are fixed, non-vacuous, output-identity probes.
    # Claimants cannot change these tests to mask an incorrect target evaluation.
    targets = claim.target.states
    tests = tuple(f"probe:{i}" for i in range(len(targets)))
    expected = {(y, t): ("EQ" if y == targets[i] else "DIST")
                for y in targets for i, t in enumerate(tests)}
    if (claim.target.tests != tests or claim.target.protected != tests
            or claim.target.eval_table() != expected
            or len(tests) < 2):
        raise ValueError("CLC target test interface is not protected output-discriminating oracle")
    if claim.source.tests != tests:
        raise ValueError("CLC source test interface must preserve the frozen named probe language")


def _case_nat_map(name: str, inputs: tuple[str, ...],
                  outputs: tuple[str, ...], rows: tuple[tuple[str, str], ...]) -> str:
    vals = dict(rows)
    expressions = []
    for i, key in enumerate(inputs):
        j = outputs.index(vals[key])
        expressions.append(f"  | {i} => ⟨ {j}, by decide⟩")
    expressions.append(f"  | _ => ⟨ 0, by decide⟩")
    return (f"def {name} (v : Fin {len(inputs)}) : Fin {len(outputs)} :=\n"
            f"  match v.val with\n" + "\n".join(expressions))


def _form_source(name: str, form: FiniteCLCForm) -> str:
    entries = form.eval_table()
    lines = [f"def {name} : FiniteCLC.Form (Fin {len(form.states)}) (Fin {len(form.tests)}) :=",
             "  { eval := fun s t =>", "      match s.val, t.val with"]
    for i, s in enumerate(form.states):
        for j, t in enumerate(form.tests):
            lines.append(f"      | {i}, {j} => .{entries[(s,t)].lower()}")
    lines.extend(["      | _, _ => .unknown", "    isProtected := fun t =>", "      match t.val with"])
    for j, t in enumerate(form.tests):
        lines.append(f"      | {j} => {'true' if t in form.protected else 'false'}")
    lines.extend(["      | _ => false", "  }"])
    return "\n".join(lines)


def generated_lean_source(claim: FiniteCLCTransport,
                          library_contents: str) -> str:
    src = [_form_source("clcSource", claim.source),
           _form_source("clcTarget", claim.target),
           _case_nat_map("clcForward", claim.source.states, claim.target.states,
                         claim.forward),
           _case_nat_map("clcPull", claim.target.tests, claim.source.tests,
                         claim.pull),
           _case_nat_map("clcLift", claim.source.tests, claim.target.tests,
                         claim.lift),
           "def clcWitness : FiniteCLC.Transport clcSource clcTarget :=\n"
           "  { forward := clcForward, pull := clcPull, lift := clcLift }",
           ("theorem clcChecked : FiniteCLC.Strict clcSource clcTarget clcWitness := by decide"
            if claim.strict else
            "theorem clcChecked : FiniteCLC.Valid clcSource clcTarget clcWitness := by decide"),
           'theorem clcPreservesDecisive (x : Fin ' + str(len(claim.source.states)) +
           ') (d : Fin ' + str(len(claim.target.tests)) +
           ') (h : clcSource.eval x (clcPull d) ≠ .unknown) :' +
           ' clcSource.eval x (clcPull d) = clcTarget.eval (clcForward x) d := by\n'
           '  exact FiniteCLC.preserve_decisive ' +
           ('clcChecked.1' if claim.strict else 'clcChecked') + ' x d h',
           f'#eval IO.println "CLC_FINITE_TRANSPORT_CHECKED:{claim.digest}"',
           '#print axioms clcChecked',
           '#print axioms FiniteCLC.valid_compose']
    return library_contents + "\n\n" + "\n\n".join(src) + "\n"


@dataclass(frozen=True)
class CLCProofReceipt:
    claim_sha256: str
    generated_proof_sha256: str
    library_sha256: str
    lean_version: str
    stdout_sha256: str


class LeanCLCChecker:
    def __init__(self, lean_executable: str = "lean", *, timeout: int = 45):
        if timeout < 1:
            raise ValueError("Lean transport checker requires positive timeout")
        self.lean_executable = lean_executable
        self.timeout = timeout
        self._cache: dict[str, CLCProofReceipt] = {}

    def _version(self) -> str:
        try:
            version = subprocess.run([self.lean_executable, "--version"],
                                     capture_output=True, text=True, timeout=10, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ValueError("CLC Lean kernel unavailable: UNKNOWN_ENVIRONMENT") from exc
        if (version.returncode != 0
                or not re.search(r"\bLean\s+\(version\s+" + re.escape(EXPECTED_LEAN_VERSION),
                                 version.stdout)):
            raise ValueError("CLC Lean version mismatch: UNKNOWN_ENVIRONMENT")
        return version.stdout.strip()

    def check_transport(self, cap: "FiniteCapability",
                        oracle: tuple[tuple[str, str], ...],
                        claim: FiniteCLCTransport) -> CLCProofReceipt:
        bind_transport(cap, oracle, claim)
        version = self._version()
        try:
            library_bytes = LEAN_LIBRARY.read_bytes()
        except OSError as exc:
            raise ValueError("CLC pinned Lean theory missing") from exc
        library_sha = hashlib.sha256(library_bytes).hexdigest()
        if library_sha != LEAN_LIBRARY_SHA256:
            raise ValueError("CLC Lean theory has changed from its pinned audit identity")
        key = sha({"claim": claim.payload(), "source": library_sha,
                   "lean_version": version, "executable": self.lean_executable})
        if key in self._cache:
            return self._cache[key]
        generated = generated_lean_source(claim, library_bytes.decode("utf-8"))
        if "sorry" in generated or "axiom " in generated or "unsafe " in generated:
            raise ValueError("CLC transport proof contains an unauthorized trust escape")
        with tempfile.TemporaryDirectory(prefix="clc-lean-") as temp:
            path = Path(temp) / "ConcreteTransport.lean"
            path.write_text(generated, encoding="utf-8")
            try:
                result = subprocess.run([self.lean_executable, str(path)],
                                        capture_output=True, text=True,
                                        timeout=self.timeout, check=False)
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise ValueError("CLC Lean transport checker did not finish: UNKNOWN_ENVIRONMENT") from exc
        marker = f"CLC_FINITE_TRANSPORT_CHECKED:{claim.digest}"
        if result.returncode != 0 or marker not in result.stdout:
            raise ValueError("CLC transport failed Lean kernel proof: REJECTED_OR_ENVIRONMENT")
        if ("sorryAx" in result.stdout or "sorry" in result.stderr
                or "error:" in result.stderr.lower()):
            raise ValueError("CLC transport proof contains invalid or unsound Lean diagnostics")
        receipt = CLCProofReceipt(
            claim_sha256=claim.digest,
            generated_proof_sha256=hashlib.sha256(generated.encode()).hexdigest(),
            library_sha256=library_sha,
            lean_version=version,
            stdout_sha256=hashlib.sha256(result.stdout.encode()).hexdigest(),
        )
        self._cache[key] = receipt
        return receipt
