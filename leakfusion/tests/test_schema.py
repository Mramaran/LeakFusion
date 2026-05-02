"""Schema sanity: required vs optional vs syn-filled column sets are disjoint and complete."""
from leakfusion.src import schema


def test_required_columns_are_17():
    assert len(schema.REQUIRED_COLUMNS) == 17


def test_syn_filled_columns_are_two():
    assert schema.SYN_FILLED_COLUMNS == {"turbo_speed", "t_aftertreatment_inlet"}


def test_syn_filled_is_subset_of_required():
    assert schema.SYN_FILLED_COLUMNS.issubset(schema.REQUIRED_COLUMNS)


def test_required_optional_disjoint():
    assert schema.REQUIRED_COLUMNS.isdisjoint(schema.OPTIONAL_COLUMNS)


def test_label_columns_only_in_leak_dataset():
    assert schema.LABEL_COLUMNS == {"leak_zone", "leak_severity", "load_fraction"}


def test_all_columns_are_lowercase_with_underscores():
    all_cols = schema.REQUIRED_COLUMNS | schema.OPTIONAL_COLUMNS | schema.LABEL_COLUMNS
    for c in all_cols:
        assert c == c.lower(), f"{c} is not lowercase"
        assert " " not in c, f"{c} contains whitespace"
