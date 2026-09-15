from __future__ import annotations
import hashlib, math
import openml

def h(seed, value):
    return hashlib.sha256(f"{seed}|{value}".encode()).digest()

def load_world(meta):
    task = openml.tasks.get_task(int(meta["task_id"]), download_data=False)
    ds = openml.datasets.get_dataset(int(meta["data_id"]), download_data=True)
    X, y, _, _ = ds.get_data(dataset_format="dataframe", target=task.target_name)
    cols = []
    for col in X.columns:
        try:
            v = X[col].astype(float)
        except Exception:
            continue
        q = v.replace([math.inf, -math.inf], math.nan).dropna()
        if len(q) and q.nunique() > 1:
            cols.append(col)
    if len(cols) < 2:
        raise ValueError("too few numeric features")
    idx = list(range(len(X)))
    idx.sort(key=lambda i: h(f"v7|rows|{meta['task_id']}", str(i)))
    idx = sorted(idx[:1000])
    cols.sort(key=lambda c: h(f"v7|cols|{meta['task_id']}", str(c)))
    cols = cols[:32]
    rows = []
    for col in cols:
        v = X.loc[idx, col].astype(float).replace([math.inf, -math.inf], math.nan)
        med = float(v.median())
        if not math.isfinite(med):
            med = 0.0
        X.loc[idx, col] = v.fillna(med)
    for i in idx:
        rows.append([float(X.loc[i, c]) for c in cols])
    raw_labels = [str(y.loc[i]) for i in idx]
    levels = sorted(set(raw_labels))
    counts = {z: raw_labels.count(z) for z in levels}
    pos = min(levels, key=lambda z: (abs(counts[z] / len(raw_labels) - 0.5), z))
    labels = [int(z == pos) for z in raw_labels]
    if not any(labels) or all(labels):
        raise ValueError("collapsed target")
    payload = hashlib.sha256()
    for row, label in zip(rows, labels):
        payload.update(("|".join(f"{x:.17g}" for x in row)+f"|{label}\n").encode())
    return [f"f{i}" for i in range(len(cols))], rows, labels, payload.hexdigest()
