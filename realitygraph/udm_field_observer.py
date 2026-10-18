"""Generic test-side observer for failed mapping comparisons.

Never alters the expected or actual native operands or the assertion result.
Observes equality only when both operands are mappings.
"""
from __future__ import annotations
import json, os
from collections.abc import Mapping

def primitive(v):
    return v is None or type(v) in (bool, int, float, str)

def describe(left, right):
    if not isinstance(left, Mapping) or not isinstance(right, Mapping):
        return None
    if not all(type(k) is str for k in left) or not all(type(k) is str for k in right):
        return None
    left_keys=set(left)
    right_keys=set(right)
    unequal=sorted(str(k) for k in left_keys & right_keys if left[k] != right[k])
    return {
        "left_only":sorted(left_keys-right_keys),
        "right_only":sorted(right_keys-left_keys),
        "unequal":unequal,
        "left_values":{k:left[k] for k in sorted(left_keys-right_keys) if primitive(left[k])},
        "right_values":{k:right[k] for k in sorted(right_keys-left_keys) if primitive(right[k])},
    }

def pytest_assertrepr_compare(config, op, left, right):
    if op != "==":
        return None
    row=describe(left,right)
    if row is not None:
        path=os.environ.get("UDM_FIELD_OBSERVATIONS")
        if path:
            with open(path,"a",encoding="utf8") as f:
                f.write(json.dumps(row,sort_keys=True)+"\n")
    return None
