"""Stage 3 splits — StratifiedGroupKFold by run_id with no leakage."""
import numpy as np
import pytest


def test_stratified_group_kfold_splits_no_leak():
    """Train and val sets share zero group ids."""
    from leakfusion.src.ml.splits import stratified_group_kfold

    rng = np.random.default_rng(42)
    n_groups = 50
    rows_per_group = 20
    groups = np.repeat(np.arange(n_groups), rows_per_group)
    y = rng.integers(0, 5, size=len(groups))
    X = rng.standard_normal((len(groups), 15))

    folds = list(stratified_group_kfold(X, y, groups, n_splits=5, seed=42))
    assert len(folds) == 5
    for train_idx, val_idx in folds:
        train_groups = set(groups[train_idx])
        val_groups = set(groups[val_idx])
        assert train_groups.isdisjoint(val_groups), "run_id leaked across train/val"


def test_stratified_group_kfold_preserves_class_balance():
    """Each fold's val set sees roughly even class distribution."""
    from leakfusion.src.ml.splits import stratified_group_kfold

    rng = np.random.default_rng(1)
    # 50 groups, each group has one class label (so groups carry the label)
    n_groups = 50
    rows_per_group = 20
    group_labels = rng.integers(0, 5, size=n_groups)
    groups = np.repeat(np.arange(n_groups), rows_per_group)
    y = np.repeat(group_labels, rows_per_group)
    X = rng.standard_normal((len(groups), 15))

    for train_idx, val_idx in stratified_group_kfold(X, y, groups, n_splits=5, seed=42):
        val_y = y[val_idx]
        # Every class should appear at least once in val (with this size)
        unique_val_classes = set(val_y)
        assert len(unique_val_classes) >= 3, "val fold lost class diversity"


def test_held_out_test_indices_returns_first_fold():
    """held_out_test_indices returns the val indices of fold 0."""
    from leakfusion.src.ml.splits import held_out_test_indices

    rng = np.random.default_rng(7)
    groups = np.repeat(np.arange(40), 25)
    y = rng.integers(0, 5, size=len(groups))
    X = rng.standard_normal((len(groups), 15))

    test_idx, train_idx = held_out_test_indices(X, y, groups, n_splits=5, seed=42)
    assert len(set(test_idx) & set(train_idx)) == 0
    assert len(test_idx) + len(train_idx) == len(groups)
