from __future__ import annotations

import csv
import json
from pathlib import Path

from acc_prospective_transfer import reconstruct_ms_state


def rotations(word):
    word = tuple(word)
    if not word:
        return ((),)
    return tuple(word[i:] + word[:i] for i in range(len(word)))


def inverse(word):
    return tuple(-x for x in reversed(word))


def word_orbit(word):
    word = tuple(word)
    return set(rotations(word)) | set(rotations(inverse(word)))


def presentation_key(state):
    a, b = state
    return tuple(sorted((min(word_orbit(a)), min(word_orbit(b)))))


def load_open(path):
    rows = []
    with Path(path).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["status_at_freeze"] == "open":
                w = tuple(int(x) for x in row["w_vector"].split()) if row["w_vector"].strip() else ()
                rows.append((int(row["seq"]), reconstruct_ms_state(int(row["n"]), w)))
    return rows


def main():
    manifest = json.loads(Path("official/competition/tools/verifier/data/manifest.json").read_text())
    ac = [c for c in manifest["challenges"] if c["move_spec_version"] == "ac-r2-v1"]
    exact = {tuple(tuple(x for x in w) for w in c["initial_relators"]): c["challenge_id"] for c in ac}
    orbit = {}
    duplicates = 0
    for c in ac:
        state = tuple(tuple(x for x in w) for w in c["initial_relators"])
        key = presentation_key(state)
        if key in orbit:
            duplicates += 1
        orbit[key] = c["challenge_id"]

    rows = load_open("official/competition/tools/verifier/data/ms1190_metadata.csv")
    exact_hits = sum(state in exact for _, state in rows)
    orbit_hits = sum(presentation_key(state) in orbit for _, state in rows)
    print(json.dumps({
        "open_rows": len(rows),
        "exact_hits": exact_hits,
        "orbit_hits": orbit_hits,
        "orbit_duplicate_keys": duplicates,
    }, sort_keys=True))
    if orbit_hits != len(rows):
        missing = [seq for seq, state in rows if presentation_key(state) not in orbit]
        print("first_missing", missing[:20])
        raise SystemExit(2)


if __name__ == "__main__":
    main()
