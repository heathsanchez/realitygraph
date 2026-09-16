import json

import pytest

from acc_developmental_experiment import (
    FREEZE_VERSION,
    load_open_rows,
    policy_sha256,
    write_freeze_marker,
)


def _metadata(path):
    path.write_text(
        "seq,n,w_vector,status_at_freeze\n"
        "1,3,2 2,open\n"
        "2,4,1 -2,closed\n",
        encoding="utf-8",
    )


def test_open_rows_are_inaccessible_without_matching_frozen_policy(tmp_path):
    metadata = tmp_path / "ms.csv"
    marker = tmp_path / "freeze.json"
    _metadata(metadata)
    policy_text = '{"promoted":true,"version":"unit"}'
    digest = policy_sha256(policy_text)

    with pytest.raises(RuntimeError, match="frozen policy"):
        load_open_rows(metadata, marker, expected_policy_sha256=digest)

    marker.write_text(
        json.dumps(
            {
                "version": FREEZE_VERSION,
                "policy_sha256": "wrong",
                "split_digest": "split-unit",
                "open_rows_loaded": False,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="hash mismatch"):
        load_open_rows(metadata, marker, expected_policy_sha256=digest)


def test_matching_freeze_marker_unlocks_only_open_rows(tmp_path):
    metadata = tmp_path / "ms.csv"
    marker = tmp_path / "freeze.json"
    _metadata(metadata)
    policy_text = '{"promoted":true,"version":"unit"}'
    digest = policy_sha256(policy_text)
    write_freeze_marker(marker, policy_text, split_digest="split-unit")

    payload = json.loads(marker.read_text(encoding="utf-8"))
    assert payload["policy_sha256"] == digest
    assert payload["split_digest"] == "split-unit"
    assert payload["open_rows_loaded"] is False

    rows = load_open_rows(metadata, marker, expected_policy_sha256=digest)
    assert rows == [{"seq": 1, "n": 3, "w_vector": (2, 2)}]
