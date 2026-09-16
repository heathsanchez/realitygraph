from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from acc_open_ms_transfer import _load_open_ms


FREEZE_VERSION = "acc-developmental-freeze-v1"


def policy_sha256(policy_text: str) -> str:
    return hashlib.sha256(policy_text.encode("utf-8")).hexdigest()


def write_freeze_marker(
    path: Path,
    policy_text: str,
    *,
    split_digest: str,
) -> dict[str, Any]:
    payload = {
        "version": FREEZE_VERSION,
        "policy_sha256": policy_sha256(policy_text),
        "split_digest": str(split_digest),
        "open_rows_loaded": False,
    }
    path.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def _validated_freeze_marker(
    marker_path: Path,
    *,
    expected_policy_sha256: str,
) -> dict[str, Any]:
    if not marker_path.exists():
        raise RuntimeError("open ACC rows require a frozen policy marker")
    try:
        payload = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("open ACC rows require a valid frozen policy marker") from exc
    if payload.get("version") != FREEZE_VERSION:
        raise RuntimeError("open ACC rows require a frozen policy marker")
    actual = str(payload.get("policy_sha256", ""))
    if actual != str(expected_policy_sha256):
        raise RuntimeError("frozen policy hash mismatch before open ACC row access")
    if payload.get("open_rows_loaded") is not False:
        raise RuntimeError("freeze marker was already mutated before open-row access")
    if not payload.get("split_digest"):
        raise RuntimeError("frozen policy marker is missing the sealed split digest")
    return payload


def load_open_rows(
    metadata_path: Path,
    freeze_marker_path: Path,
    *,
    expected_policy_sha256: str,
) -> list[dict[str, Any]]:
    _validated_freeze_marker(
        freeze_marker_path,
        expected_policy_sha256=expected_policy_sha256,
    )
    return _load_open_ms(metadata_path)
