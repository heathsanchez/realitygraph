from acc_scientific_split import freeze_split


def _row(training_id, n, w):
    return {
        "training_id": training_id,
        "n": n,
        "w_vector": list(w),
        "moves": [],
        "states": [{"state": [[1], [2]]}],
    }


def test_recurring_family_orders_larger_n_into_later_stages_and_is_deterministic():
    rows = [
        _row("wA-n1", 1, (2,)),
        _row("wA-n2", 2, (2,)),
        _row("wA-n3", 3, (2,)),
        _row("single-b", 5, (1, -2)),
        _row("single-c", 7, (-1, 2, 1)),
    ]
    first = freeze_split(rows, "sealed-test-seed")
    second = freeze_split(list(reversed(rows)), "sealed-test-seed")
    assert first.canonical_json() == second.canonical_json()
    assert first.manifest_digest == second.manifest_digest

    assert "wA-n1" in first.acquisition_ids
    assert "wA-n2" in first.calibration_ids
    assert "wA-n3" in first.future_ids

    all_ids = set(first.acquisition_ids) | set(first.calibration_ids) | set(first.future_ids)
    assert all_ids == {row["training_id"] for row in rows}
    assert not (set(first.acquisition_ids) & set(first.calibration_ids))
    assert not (set(first.acquisition_ids) & set(first.future_ids))
    assert not (set(first.calibration_ids) & set(first.future_ids))


def test_future_rows_are_not_returned_as_learning_rows():
    rows = [
        _row("a1", 1, (2,)),
        _row("a2", 2, (2,)),
        _row("a3", 3, (2,)),
    ]
    split = freeze_split(rows, "sealed-test-seed")
    learning = set(split.acquisition_ids) | set(split.calibration_ids)
    assert learning.isdisjoint(split.future_ids)
