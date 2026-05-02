"""Smoke test: demo module is importable."""

def test_demo_module_imports():
    from leakfusion.src import demo
    assert hasattr(demo, "__name__")


def test_samples_registry():
    from leakfusion.src.demo.samples import SAMPLE_BUTTONS
    assert len(SAMPLE_BUTTONS) == 4
    keys = {b["key"] for b in SAMPLE_BUTTONS}
    assert keys == {"healthy_run", "zone1_intake_leak",
                    "zone3a_exhaust_leak", "zone4_testcell_leak"}
    for b in SAMPLE_BUTTONS:
        assert {"key", "label", "icon", "filename"} <= set(b.keys())
