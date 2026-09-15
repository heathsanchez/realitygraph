from __future__ import annotations

import unittest

from realitygraph.grouped_empirical import GroupedBinaryDataset
from verified_developmental_tournament import frontier_layers, split_groups


class DevelopmentalTournamentTests(unittest.TestCase):
    def test_frontier_layers_expand_without_overlap(self):
        groups = tuple(f"g{i}" for i in range(15))
        layers = frontier_layers(groups)
        self.assertEqual([len(x) for x in layers], [1, 2, 4, 8])
        flattened = tuple(group for layer in layers for group in layer)
        self.assertEqual(flattened, groups)

    def test_split_is_deterministic_and_sealed(self):
        groups = tuple(f"g{i}" for i in range(20))
        dataset = GroupedBinaryDataset(
            name="toy",
            doi="toy",
            license="test",
            probe_names=("x",),
            values=tuple((float(i),) for i in range(20)),
            labels=tuple(i % 2 for i in range(20)),
            groups=groups,
            source_hashes=(("toy://source", "abc"),),
        )
        left = split_groups(dataset, "seed")
        right = split_groups(dataset, "seed")
        self.assertEqual(left, right)
        boot, future, _ = left
        self.assertFalse(set(boot) & set(future))
        self.assertEqual(set(boot) | set(future), set(groups))
        self.assertGreaterEqual(len(future), 7)


if __name__ == "__main__":
    unittest.main()
