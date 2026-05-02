"""Stage 3 explainability — permutation importance + SHAP summary."""
import numpy as np
import pytest


def test_permutation_importance_returns_dict_with_feature_names():
    from leakfusion.src.ml.explain import permutation_importance_dict
    from sklearn.ensemble import RandomForestClassifier

    rng = np.random.default_rng(0)
    X = rng.standard_normal((200, 5))
    y = (X[:, 0] > 0).astype(int).astype(str)  # depends only on feature 0
    clf = RandomForestClassifier(n_estimators=20, random_state=0).fit(X, y)
    out = permutation_importance_dict(clf, X, y, feature_names=["a", "b", "c", "d", "e"], n_repeats=3, seed=0)
    assert set(out.keys()) == {"a", "b", "c", "d", "e"}
    assert out["a"] > out["e"]  # feature 0 (named 'a') should be most important


def test_shap_summary_emits_n_predictions(tmp_path):
    from leakfusion.src.ml.explain import shap_summary
    from sklearn.ensemble import RandomForestClassifier

    rng = np.random.default_rng(0)
    X = rng.standard_normal((200, 4))
    y = (X[:, 0] > 0).astype(int).astype(str)
    clf = RandomForestClassifier(n_estimators=20, random_state=0).fit(X, y)
    summary = shap_summary(clf, X[:5], feature_names=["a", "b", "c", "d"])
    assert "predictions" in summary
    assert len(summary["predictions"]) == 5
    for entry in summary["predictions"]:
        assert "feature_contributions" in entry
        assert set(entry["feature_contributions"].keys()) == {"a", "b", "c", "d"}
