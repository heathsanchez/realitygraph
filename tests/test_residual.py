import unittest

from realitygraph.predictive import PredictiveSplit, field_from_matrix
from realitygraph.residual import (
    certify_residual_batch,
    compile_residual_model,
)


class ResidualConsequenceTests(unittest.TestCase):
    def test_empty_rules_preserve_baseline_exactly(self):
        values=[(0.0,), (1.0,), (2.0,), (3.0,)]
        labels=[0,0,1,1]
        groups=["a","a","b","b"]
        baseline=[0.2,0.3,0.7,0.8]
        field=field_from_matrix(("x",),values,labels,groups)
        model=compile_residual_model(field,(),range(4),baseline)
        got=[model.predict_values(field.values[i],baseline[i]) for i in range(4)]
        self.assertEqual(got,baseline)

    def test_stable_residual_signal_can_improve_baseline(self):
        values=[]
        labels=[]
        groups=[]
        baseline=[]
        for g in range(6):
            for j in range(40):
                label=1 if j>=20 else 0
                x=float(label) + 0.01*(j%3)
                values.append((x,))
                labels.append(label)
                groups.append(f"g{g}")
                baseline.append(0.5)
        field=field_from_matrix(("signal",),values,labels,groups)
        split=PredictiveSplit(
            tuple(i for i,g in enumerate(groups) if g in {"g0","g1","g2"}),
            tuple(i for i,g in enumerate(groups) if g=="g3"),
            tuple(i for i,g in enumerate(groups) if g in {"g4","g5"}),
            "stable",
        )
        cert=certify_residual_batch(
            field,split,baseline,
            max_probes=1,
            min_calibration_gain=1e-3,
            min_sealed_gain=1e-3,
            min_support=4,
            ridge=1.0,
        )
        self.assertTrue(cert.accepted)
        self.assertEqual(len(cert.plan.rules),1)
        self.assertLess(cert.sealed_metrics.log_loss,cert.sealed_baseline_metrics.log_loss)

    def test_calibration_specific_residual_is_rejected_on_sealed_groups(self):
        values=[]
        labels=[]
        groups=[]
        baseline=[]
        train={"g0","g1","g2"}
        cal={"g3"}
        test={"g4","g5"}
        for g in ["g0","g1","g2","g3","g4","g5"]:
            for j in range(40):
                label=1 if j>=20 else 0
                signal=label if g in train|cal else 1-label
                values.append((float(signal),))
                labels.append(label)
                groups.append(g)
                baseline.append(0.5)
        field=field_from_matrix(("trap",),values,labels,groups)
        split=PredictiveSplit(
            tuple(i for i,g in enumerate(groups) if g in train),
            tuple(i for i,g in enumerate(groups) if g in cal),
            tuple(i for i,g in enumerate(groups) if g in test),
            "trap",
        )
        cert=certify_residual_batch(
            field,split,baseline,
            max_probes=1,
            min_calibration_gain=1e-3,
            min_sealed_gain=1e-3,
            min_support=4,
            ridge=1.0,
        )
        self.assertFalse(cert.accepted)
        self.assertGreater(cert.sealed_metrics.log_loss,cert.sealed_baseline_metrics.log_loss)


if __name__=="__main__":
    unittest.main()
