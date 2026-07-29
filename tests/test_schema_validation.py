import pandas as pd
import pytest

from app.ml.schema_validation import validate_table_schema


def test_validate_table_schema_passes_when_columns_present():
    df = pd.DataFrame({"code": ["A1"], "name": ["Supplier A"]})
    validate_table_schema("suppliers", df)


def test_validate_table_schema_raises_when_column_missing():
    df = pd.DataFrame({"code": ["A1"]})
    with pytest.raises(ValueError, match="Missing required columns"):
        validate_table_schema("suppliers", df)


def test_validate_table_schema_unknown_table_has_no_required_columns():
    df = pd.DataFrame({"anything": [1]})
    validate_table_schema("some_unknown_table", df)


def test_validate_table_schema_reports_all_missing_columns():
    df = pd.DataFrame({"id": [1]})
    with pytest.raises(ValueError, match="status"):
        validate_table_schema("bookings", df)