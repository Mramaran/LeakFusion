"""Smoke test: ml module is importable."""

def test_ml_module_imports():
    from leakfusion.src import ml
    assert hasattr(ml, "__name__")
