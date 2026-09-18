from __future__ import annotations

import unittest

from msi import Interface
from qckn import CertifiedSubstitution, NewContextDefect, assess_operation
from qckn.mda import Intervention, choose_intervention

from realitygraph.capability import FiniteCapability
from realitygraph.ledger import Ledger


class QCKNCrossRepoIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.states = (0, 1, 2)
        self.value = {0: 0, 1: 0, 2: 1}
        self.action_table = {0: 0, 1: 2, 2: 0}
        self.action = lambda x: self.action_table[x]

        def outcome(x, continuation):
            if continuation == "v":
                return self.value[x]
            if continuation == "v_after_action":
                return self.value[self.action(x)]
            raise KeyError(continuation)

        self.interface = Interface(
            self.states,
            ("v", "v_after_action"),
            outcome,
        )

    def test_qck_defect_mda_expand_then_certify_and_compile(self):
        before = assess_operation(
            self.interface,
            ("v",),
            self.action,
        )
        self.assertIsInstance(before, NewContextDefect)

        plan = choose_intervention(
            before,
            lambda intervention: {
                Intervention.EXPAND: 1,
                Intervention.SPLIT: 3,
                Intervention.RESTRUCTURE: 4,
                Intervention.CONSTRUCT: 5,
                Intervention.VERIFY: 6,
            }.get(intervention, 100),
        )
        self.assertEqual(plan.primary, Intervention.EXPAND)

        after = assess_operation(
            self.interface,
            ("v", "v_after_action"),
            self.action,
        )
        self.assertIsInstance(after, CertifiedSubstitution)

        compile_plan = choose_intervention(
            after,
            lambda intervention: 0,
        )
        self.assertEqual(compile_plan.primary, Intervention.COMPILE)
        self.assertEqual(
            compile_plan.admissible,
            (Intervention.COMPILE,),
        )

        capability = FiniteCapability(
            capability_id="qck-certified-action",
            input_type="state",
            output_type="state",
            semantics=tuple(
                (str(x), str(self.action(x)))
                for x in self.states
            ),
            guard_inputs=tuple(str(x) for x in self.states),
            certificate_id="qck-v1:certified-substitution",
            dependencies=(),
            authority_snapshot="qck-v1-frozen",
            verifier_id="qckn-cross-repo-v1",
            provenance_ids=(
                "qck:defect->expand->certified",
            ),
            cost=0,
        )

        ledger = Ledger()
        ledger.append_promote_capability(
            capability,
            "qckn-cross-repo-v1",
        )
        present = ledger.materialize_compiled_present().restart()

        self.assertEqual(
            present.capability_graph.active_ids(),
            ("qck-certified-action",),
        )
        restored = present.capability_graph.capability_map[
            "qck-certified-action"
        ]
        self.assertEqual(
            tuple(
                restored.execute(str(x))
                for x in self.states
            ),
            tuple(str(self.action(x)) for x in self.states),
        )


if __name__ == "__main__":
    unittest.main()
