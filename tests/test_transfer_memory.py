import unittest

from realitygraph.mg import MG
from realitygraph.predictive import CompiledPredictiveModel, ThresholdRule
from realitygraph.transfer_memory import (
    law_to_model,
    model_from_memory,
    model_memory,
    model_to_law,
)


class TransferMemoryTests(unittest.TestCase):
    def test_round_trip_compiled_model_through_mg_text(self):
        model = CompiledPredictiveModel(
            (ThresholdRule(1, "Light", 100.5),),
            (((0,), 0.1, 20), ((1,), 0.9, 30)),
            0.4,
            min_support=4,
        )
        hashes = (("uci://occupancy", "abc123"),)
        law = model_to_law(hashes, model, provenance="sealed-16")
        text = model_memory(law).text()
        restarted = MG.parse(text)
        rebuilt = model_from_memory(
            restarted,
            hashes,
            ("Temperature", "Light", "CO2"),
        )

        self.assertEqual(rebuilt.rules[0].probe_name, "Light")
        self.assertEqual(rebuilt.rules[0].probe_index, 1)
        self.assertEqual(rebuilt.rules[0].threshold, 100.5)
        self.assertEqual(rebuilt.decoder, model.decoder)
        self.assertEqual(rebuilt.min_support, 4)

    def test_missing_future_probe_rejects_memory(self):
        model = CompiledPredictiveModel(
            (ThresholdRule(0, "Light", 10.0),),
            (((0,), 0.2, 10), ((1,), 0.8, 10)),
            0.5,
            min_support=1,
        )
        law = model_to_law((("x", "y"),), model, provenance="p")
        with self.assertRaises(ValueError):
            law_to_model(law, ("CO2",))


if __name__ == "__main__":
    unittest.main()
