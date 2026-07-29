import pandas as pd

from app.ml.feature_engineering.helpers import left_merge, safe_rate, to_dt


def test_to_dt_converts_valid_date_strings():
    df = pd.DataFrame({"created_at": ["2026-01-01", "2026-02-01"]})
    result = to_dt(df, ["created_at"])
    assert pd.api.types.is_datetime64_any_dtype(result["created_at"])


def test_to_dt_coerces_invalid_dates_to_nat():
    df = pd.DataFrame({"created_at": ["not-a-date"]})
    result = to_dt(df, ["created_at"])
    assert pd.isna(result["created_at"].iloc[0])


def test_to_dt_ignores_missing_columns():
    df = pd.DataFrame({"other_col": [1, 2]})
    result = to_dt(df, ["created_at"])
    assert "created_at" not in result.columns


def test_safe_rate_with_series_avoids_division_by_zero():
    num = pd.Series([10, 20])
    den = pd.Series([0, 4])
    result = safe_rate(num, den)
    assert pd.isna(result.iloc[0])
    assert result.iloc[1] == 5.0


def test_safe_rate_with_scalar_zero_denominator():
    assert safe_rate(10, 0) == 0


def test_safe_rate_with_scalar_nonzero_denominator():
    assert safe_rate(10, 2) == 5.0


def test_left_merge_returns_base_when_right_is_none():
    base = pd.DataFrame({"supplier_code": ["A"], "x": [1]})
    result = left_merge(base, None)
    assert result.equals(base)


def test_left_merge_returns_base_when_right_is_empty():
    base = pd.DataFrame({"supplier_code": ["A"], "x": [1]})
    right = pd.DataFrame(columns=["supplier_code", "y"])
    result = left_merge(base, right)
    assert result.equals(base)


def test_left_merge_joins_on_supplier_code():
    base = pd.DataFrame({"supplier_code": ["A", "B"], "x": [1, 2]})
    right = pd.DataFrame({"supplier_code": ["A", "B"], "y": [10, 20]})
    result = left_merge(base, right)
    assert list(result["y"]) == [10, 20]