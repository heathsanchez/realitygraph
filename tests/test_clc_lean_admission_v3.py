"""Native FLASH proof-carrying admissions; exact finite CLC transport checks."""
from __future__ import annotations

import hashlib
import os
import subprocess
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from realitygraph.capability import FiniteCapability
from realitygraph.clc_lean import (
    FiniteCLCForm, FiniteCLCTransport, LeanCLCChecker, LEAN_LIBRARY,
    LEAN_LIBRARY_SHA256, bind_transport, canonical_transport,
    compose_transports, generated_lean_source,
)
from realitygraph.flash import (
    FlashClosure, FlashEventRuntime, FlashCompositionRule, LiveObligation,
    FlashContract, CapabilityAdmissionEvent, CapabilityRevocationEvent,
)

AUTH = "audit-omega-1"
VERIFIER = "audit-v1"
C = FlashContract(AUTH, VERIFIER)


def capability(name: str) -> FiniteCapability:
    types = {"f": ("X", "Y", (('x0','y0'),('x1','y1')), 2),
             "g": ("Y", "Z", (('y0','z0'),('y1','z1')), 2),
             "alt": ("X", "Z", (('x0','z0'),('x1','z1')), 9)}
    ti, to, sem, cost = types[name]
    return FiniteCapability(
        capability_id=name, input_type=ti, output_type=to,
        semantics=sem, guard_inputs=tuple(k for k, _ in sem),
        certificate_id="source:" + name,
        dependencies=(), authority_snapshot=AUTH, verifier_id=VERIFIER,
        provenance_ids=("external-source-" + name,), cost=cost)


def flash(checker: LeanCLCChecker) -> tuple[FlashClosure, FlashEventRuntime]:
    obligations = tuple(LiveObligation(
        obligation_id=f"p-{i}", input_type="Target",
        source_input_type="X", output_type="Z",
        oracle=(('t0','z0'),('t1','z1')),
        transport_to_source=(('t0','x0'),('t1','x1')),
        contract=C, candidate_fingerprints=("bad", "good"),
    ) for i in range(2))
    closure = FlashClosure(obligations,
        composition_rules=(FlashCompositionRule(
            'compose-f-g','f','g','h',
            (('x0','z0'),('x1','z1')),'cert-h'),),
        kernel='clc-lean-v3', clc_checker=checker)
    return closure, FlashEventRuntime(closure)


def admission(eid: str, name: str, *, claim: FiniteCLCTransport | None = None):
    cap = capability(name)
    return CapabilityAdmissionEvent(eid, cap, cap.semantics,
                                    transport_claim=claim)


class CLCLeanAdmissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.checker = LeanCLCChecker(os.environ.get("CLC_LEAN", "lean"))
        cls.version = cls.checker._version()
        assert hashlib.sha256(LEAN_LIBRARY.read_bytes()).hexdigest() == LEAN_LIBRARY_SHA256

    def lean_direct(self, claim: FiniteCLCTransport) -> subprocess.CompletedProcess:
        script = generated_lean_source(claim, LEAN_LIBRARY.read_text())
        with tempfile.TemporaryDirectory(prefix='clc-falsify-') as tmp:
            file = Path(tmp) / 'concrete.lean'
            file.write_text(script)
            return subprocess.run([self.checker.lean_executable, str(file)],
                                  capture_output=True, text=True, timeout=60)

    def test_strict_developmental_and_composed_kernel_proofs(self):
        f, g = capability('f'), capability('g')
        left, right = canonical_transport(f), canonical_transport(g)
        a = self.checker.check_transport(f, f.semantics, left)
        b = self.checker.check_transport(g, g.semantics, right)
        self.assertEqual(a.claim_sha256, left.digest)
        self.assertEqual(b.library_sha256, LEAN_LIBRARY_SHA256)
        developmental = canonical_transport(f, developmental=True)
        d = self.checker.check_transport(f, f.semantics, developmental)
        self.assertNotEqual(a.claim_sha256, d.claim_sha256)
        composed = compose_transports(left, right)
        from realitygraph.capability import compose_capabilities
        derived = compose_capabilities('h:dependent', f, g)
        standalone = replace(derived, capability_id='h', dependencies=(),
                             certificate_id='cert-h')
        receipt = self.checker.check_transport(standalone,
                             (('x0','z0'),('x1','z1')), composed)
        self.assertEqual(receipt.claim_sha256, composed.digest)
        self.assertTrue(left.strict and right.strict and composed.strict)

    def test_invalid_laws_cause_lean_kernel_failure(self):
        cap = capability('f')
        valid = canonical_transport(cap)
        valid_run = self.lean_direct(valid)
        self.assertEqual(valid_run.returncode, 0, msg=valid_run.stdout+valid_run.stderr)
        malformed = [
            replace(valid, forward=(('x0','y1'),('x1','y0'))),
            replace(valid, pull=(('probe:0','probe:1'),('probe:1','probe:0'))),
            replace(valid, lift=(('probe:0','probe:1'),('probe:1','probe:0'))),
            replace(valid, source=replace(valid.source, protected=('probe:0',))),
            replace(valid, source=replace(valid.source, outcomes=(
                ('x0','probe:0','DIST'),
                *tuple(x for x in valid.source.outcomes if x[:2]!=('x0','probe:0'))))),
        ]
        for mutant in malformed:
            with self.subTest(mutant=mutant.digest[:12]):
                result = self.lean_direct(mutant)
                self.assertNotEqual(result.returncode, 0,
                                    'mutated CLC law unexpectedly kernel-checked')
                self.assertNotIn('no axioms', result.stdout.lower() if result.returncode else '')

    def test_flash_refuses_unbound_and_forged_claims_without_mutation(self):
        closure, runtime = flash(self.checker)
        cap = capability('f')
        with self.assertRaisesRegex(ValueError, 'CLC-gated FLASH'):
            runtime.apply(admission('missing','f'))
        self.assertEqual(closure.event_count, 0)
        bad = replace(canonical_transport(cap),
                      forward=(('x0','y1'),('x1','y0')))
        with self.assertRaisesRegex(ValueError, 'CLC witness'):
            runtime.apply(admission('forged-forward','f',claim=bad))
        self.assertEqual(closure.event_count, 0)
        with self.assertRaisesRegex(ValueError, 'oracle'):
            self.checker.check_transport(cap, (('x0','wrong'),('x1','y1')),
                                         canonical_transport(cap))
        with self.assertRaisesRegex(ValueError, 'authority'):
            runtime.apply(admission('foreign','f',claim=replace(
                canonical_transport(cap), authority_snapshot='foreign')))
        self.assertFalse(closure.capabilities)
        self.assertFalse(runtime.event_ids())

    def test_flash_composition_restart_ablation_and_alternative_support(self):
        closure, runtime = flash(self.checker)
        self.assertEqual(closure.open_obligation_ids(), ('p-0','p-1'))
        for name in ('f','g'):
            runtime.apply(admission('admit-'+name, name,
                                    claim=canonical_transport(capability(name))))
        self.assertEqual(closure.discharged_obligation_ids(), ('p-0','p-1'))
        self.assertEqual(set(closure.clc_receipts), {'f','g','h'})
        self.assertEqual(closure.clc_receipts['h'].claim_sha256,
                         closure.clc_claims['h'].digest)
        retained = closure.compiled_present().restart()
        h = next(c for c in retained.capability_graph.capabilities
                 if c.capability_id == 'h')
        self.assertEqual((h.execute('x0'),h.execute('x1')),('z0','z1'))
        old = closure.event_count
        runtime.apply(admission('admit-g','g',claim=canonical_transport(capability('g'))))
        self.assertEqual(old, closure.event_count)
        with self.assertRaisesRegex(ValueError, 'event identity conflict'):
            runtime.apply(admission('admit-g','alt',claim=canonical_transport(capability('alt'))))
        runtime.apply(CapabilityRevocationEvent('revoke-f','f','exact ancestor ablation'))
        self.assertEqual(closure.open_obligation_ids(), ('p-0','p-1'))
        self.assertNotIn('h',closure.active_capability_ids())
        self.assertIn('h',closure.clc_receipts) # historical proof remains, not active warrant
        runtime.apply(admission('fresh-alt','alt',
                                claim=canonical_transport(capability('alt'))))
        self.assertEqual(closure.discharged_obligation_ids(), ('p-0','p-1'))
        self.assertEqual(closure.obligations['p-0'].solved_by, 'alt')
        self.assertNotIn('f',closure.active_capability_ids())

        other, run2 = flash(self.checker)
        for name in ('f','g','alt'):
            run2.apply(admission('add-'+name,name,
                                claim=canonical_transport(capability(name))))
        self.assertEqual(other.obligations['p-0'].solved_by, 'h')
        run2.apply(CapabilityRevocationEvent('remove-f','f','one support lost'))
        self.assertEqual(other.discharged_obligation_ids(), ('p-0','p-1'))
        self.assertTrue(all(o.solved_by=='alt' for o in other.obligations.values()))
        run2.apply(CapabilityRevocationEvent('remove-alt','alt','last support lost'))
        self.assertEqual(other.open_obligation_ids(), ('p-0','p-1'))

    def test_bad_composable_transport_fails_before_flash_mutation(self):
        c, runtime = flash(self.checker)
        runtime.apply(admission('admit-f','f',
                                claim=canonical_transport(capability('f'))))
        g = capability('g')
        good = canonical_transport(g)
        # Source does not have the same protected/intermediate evaluation as
        # f.target. It can still be a valid UNKNOWN-to-decisive development.
        modified = canonical_transport(g, developmental=True)
        self.checker.check_transport(g,g.semantics,modified)
        before = (c.event_count, tuple(c.capabilities), tuple(c.clc_receipts))
        with self.assertRaisesRegex(ValueError, 'identical intermediate form'):
            runtime.apply(admission('incompatible-g','g',claim=modified))
        after = (c.event_count, tuple(c.capabilities), tuple(c.clc_receipts))
        self.assertEqual(before,after)
        self.assertNotIn('g',c.capabilities)
        self.assertNotIn('h',c.capabilities)
        self.assertEqual(c.open_obligation_ids(), ('p-0','p-1'))
        runtime.apply(admission('compatible-g','g',claim=good))
        self.assertEqual(c.discharged_obligation_ids(), ('p-0','p-1'))


if __name__ == '__main__':
    unittest.main()
