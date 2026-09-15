from realitygraph.predictive import (
    PredictiveSplit,
    certify_predictive_batch,
    field_from_matrix,
)


def stable_world():
    values = []
    labels = []
    groups = []
    for group in range(8):
        for j in range(24):
            label = 1 if j >= 12 else 0
            signal = (2 * label - 1) * 2.0 + ((j + group) % 5) * 0.03
            distractor = ((j * 17 + group * 3) % 19) / 19.0
            duplicate = signal
            values.append((signal, duplicate, distractor))
            labels.append(label)
            groups.append(f"g{group}")
    split = PredictiveSplit(
        tuple(i for i, g in enumerate(groups) if g in {"g0", "g1", "g2", "g3"}),
        tuple(i for i, g in enumerate(groups) if g in {"g4", "g5"}),
        tuple(i for i, g in enumerate(groups) if g in {"g6", "g7"}),
        "stable",
    )
    return field_from_matrix(("stable", "duplicate", "noise"), values, labels, groups), split


def trap_world():
    values = []
    labels = []
    groups = []
    train = {"g0", "g1", "g2"}
    cal = {"g3"}
    test = {"g4", "g5"}
    for group in ["g0", "g1", "g2", "g3", "g4", "g5"]:
        for j in range(20):
            label = 1 if j >= 10 else 0
            trap = label if group in train | cal else 1 - label
            values.append((float(trap),))
            labels.append(label)
            groups.append(group)
    split = PredictiveSplit(
        tuple(i for i, g in enumerate(groups) if g in train),
        tuple(i for i, g in enumerate(groups) if g in cal),
        tuple(i for i, g in enumerate(groups) if g in test),
        "trap",
    )
    return field_from_matrix(("site-trap",), values, labels, groups), split


def report(name, certificate):
    print(name)
    print("  retained", [rule.probe_name for rule in certificate.plan.rules])
    print("  calibration LL", f"{certificate.plan.calibration_metrics.log_loss:.5f}")
    print("  sealed baseline LL", f"{certificate.sealed_baseline_metrics.log_loss:.5f}")
    print("  sealed candidate LL", f"{certificate.sealed_metrics.log_loss:.5f}")
    print("  sealed AUC", f"{certificate.sealed_metrics.auc:.5f}")
    print("  accepted", certificate.accepted)
    print("  ablation", certificate.plan.ablation_log_loss_delta)


def main():
    print("REALITYGRAPH / PREDICTIVE CONSEQUENCE FIELD")
    print("-------------------------------------------")
    print("policy: compute probes once -> discover on train -> collide on calibration")
    print("        -> backward-delete -> touch sealed groups once")
    print()

    field, split = stable_world()
    stable = certify_predictive_batch(
        field,
        split,
        max_probes=4,
        min_calibration_gain=1e-3,
        min_sealed_gain=1e-3,
    )
    report("STABLE CONSEQUENCE", stable)
    if not stable.accepted:
        raise AssertionError("stable separator should survive sealed consequence")

    print()
    field, split = trap_world()
    trap = certify_predictive_batch(
        field,
        split,
        max_probes=1,
        min_calibration_gain=1e-3,
        min_sealed_gain=1e-3,
    )
    report("CALIBRATION-PERFECT TRAP", trap)
    if trap.accepted:
        raise AssertionError("sealed future must reject the site trap")

    print()
    print("VERDICT")
    print("PREDICTIVE_FIELD_SEALED_VERIFIER_GREEN")


if __name__ == "__main__":
    main()
