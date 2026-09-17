import importlib.util
import unittest
from realitygraph.abgp.dev_world import make_dev_world


class ExecutedGTests(unittest.TestCase):
    def api(self):
        name = 'realitygraph.abgp.executed_g'
        self.assertIsNotNone(importlib.util.find_spec(name), 'corruption needs actual reevaluation')
        return __import__(name, fromlist=['*'])

    def test_flip_is_computed_from_changed_evaluator_outputs(self):
        api = self.api()
        world = make_dev_world('G', 0, 'abgp-g-dev-v1')
        seen = []
        def evaluator(w):
            seen.append(w.comparative_cells[0].value)
            ids = tuple(a.action_id for a in w.actions)
            return ids if w.comparative_cells[0].value % 2 else tuple(reversed(ids))
        initial = world.comparative_cells[0].value
        result = api.evaluate_corruption(world, evaluator, {world.comparative_cells[0].cell_id: (initial + 1) % 2})
        self.assertEqual(result['flip'], 1)
        self.assertEqual(len(seen), 2)
        self.assertNotEqual(result['before'], result['after'])

    def test_relevance_is_evaluated_not_copied_from_cell_annotation(self):
        api = self.api()
        world = make_dev_world('G', 0, 'abgp-g-dev-v1')
        def evaluator(w):
            ids = tuple(a.action_id for a in w.actions)
            return ids if w.comparative_cells[-1].value % 2 else tuple(reversed(ids))
        result = api.audit_relevance(world, evaluator, range(7))
        self.assertEqual(result['actual_relevant_cell_ids'], [world.comparative_cells[-1].cell_id])
        self.assertFalse(result['declared_relevance_matches'])

    def test_existing_world_truth_has_no_cell_causal_dependence(self):
        api = self.api()
        world = make_dev_world('G', 1, 'abgp-g-dev-v1')
        audit = api.audit_relevance(world, api.legacy_world_order, range(7))
        self.assertEqual(len(audit['declared_relevant_cell_ids']), 10)
        self.assertEqual(audit['actual_relevant_cell_ids'], [])
        self.assertFalse(audit['eligible_matched_corruption_design'])
        self.assertGreater(audit['evaluations'], 100)

    def test_unknown_cell_is_rejected_instead_of_ignored(self):
        api = self.api()
        world = make_dev_world('G', 0, 'abgp-g-dev-v1')
        with self.assertRaises(ValueError):
            api.evaluate_corruption(world, api.legacy_world_order, {'nonexistent': 1})


if __name__ == '__main__':
    unittest.main()
