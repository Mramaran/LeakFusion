"""Stage 3 — StratifiedGroupKFold splits keyed on run_id."""
from __future__ import annotations
import numpy as np
from sklearn.model_selection import StratifiedGroupKFold


def stratified_group_kfold(X, y, groups, *, n_splits: int = 5, seed: int = 42):
    """Yield (train_idx, val_idx) for each of n_splits folds.

    Wraps sklearn's StratifiedGroupKFold with deterministic shuffling.
    """
    skf = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    for train_idx, val_idx in skf.split(X, y, groups=groups):
        yield np.asarray(train_idx), np.asarray(val_idx)


def held_out_test_indices(X, y, groups, *, n_splits: int = 5, seed: int = 42):
    """Hold out fold 0 once. Returns (test_idx, train_idx) where train_idx is folds 1..n-1."""
    folds = list(stratified_group_kfold(X, y, groups, n_splits=n_splits, seed=seed))
    test_idx = folds[0][1]
    train_idx = np.concatenate([np.concatenate([f[0], f[1]]) for f in folds[1:]])
    train_idx = np.unique(train_idx)
    train_idx = train_idx[~np.isin(train_idx, test_idx)]
    return test_idx, train_idx
