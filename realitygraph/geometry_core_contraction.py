from __future__ import annotations


def greedy_contract(features, score_fn, *, tolerance=0.0):
    """Delete distinctions while preserving the protected score within tolerance.

    ``score_fn`` must return a loss, so lower is better. Starting from ``features``,
    repeatedly delete the single feature whose removal gives the lowest loss, but
    only when that loss is no worse than the current loss plus ``tolerance``.
    Ties are resolved by feature order for deterministic replay.
    """
    current = tuple(features)
    if not current:
        raise ValueError('features must be non-empty')
    tolerance = float(tolerance)
    if tolerance < 0.0:
        raise ValueError('tolerance must be non-negative')

    current_loss = float(score_fn(current))
    removed = []

    while len(current) > 1:
        candidates = []
        for pos, feature in enumerate(current):
            subset = current[:pos] + current[pos + 1 :]
            loss = float(score_fn(subset))
            candidates.append((loss, pos, feature, subset))
        loss, _, feature, subset = min(candidates, key=lambda row: (row[0], row[1]))
        if loss > current_loss + tolerance:
            break
        removed.append(feature)
        current = subset
        current_loss = loss

    return {
        'features': current,
        'loss': current_loss,
        'removed': tuple(removed),
    }


def removal_ablation(features, score_fn):
    """Measure how much protected loss worsens when each retained feature is deleted."""
    features = tuple(features)
    if len(features) < 2:
        return []
    full_loss = float(score_fn(features))
    rows = []
    for pos, feature in enumerate(features):
        subset = features[:pos] + features[pos + 1 :]
        loss = float(score_fn(subset))
        rows.append({
            'feature': feature,
            'loss_without': loss,
            'harm': loss - full_loss,
        })
    rows.sort(key=lambda row: (-row['harm'], features.index(row['feature'])))
    return rows
