"""Tests for type inference module."""

import pandas as pd

from backend.services.type_inference import ColumnType, infer_column_type


class TestInferColumnType:
    """Tests for infer_column_type function."""

    def test_integer_column(self):
        series = pd.Series([1, 2, 3, 4, 5])
        assert infer_column_type(series) == ColumnType.INTEGER

    def test_float_column(self):
        series = pd.Series([1.1, 2.2, 3.3, 4.4, 5.5])
        assert infer_column_type(series) == ColumnType.FLOAT

    def test_string_integers(self):
        series = pd.Series(["1", "2", "3", "4", "5"])
        assert infer_column_type(series) == ColumnType.INTEGER

    def test_string_floats(self):
        series = pd.Series(["1.1", "2.2", "3.3"])
        assert infer_column_type(series) == ColumnType.FLOAT

    def test_boolean_column(self):
        series = pd.Series([True, False, True, False])
        assert infer_column_type(series) == ColumnType.BOOLEAN

    def test_boolean_strings(self):
        series = pd.Series(["yes", "no", "yes", "no"])
        assert infer_column_type(series) == ColumnType.BOOLEAN

    def test_boolean_01(self):
        series = pd.Series(["1", "0", "1", "0", "1"])
        assert infer_column_type(series) == ColumnType.BOOLEAN

    def test_date_iso(self):
        series = pd.Series(["2024-01-01", "2024-02-15", "2024-03-30"])
        assert infer_column_type(series) == ColumnType.DATE

    def test_date_slash_dmy(self):
        series = pd.Series(["01/01/2024", "15/02/2024", "30/03/2024"])
        assert infer_column_type(series) == ColumnType.DATE

    def test_datetime_column(self):
        series = pd.to_datetime(["2024-01-01", "2024-02-15"])
        assert infer_column_type(series) == ColumnType.DATE

    def test_currency_dollar(self):
        series = pd.Series(["$100.00", "$250.50", "$1,000.00"])
        assert infer_column_type(series) == ColumnType.CURRENCY

    def test_currency_euro(self):
        series = pd.Series(["€100.00", "€250.50", "€1000.00"])
        assert infer_column_type(series) == ColumnType.CURRENCY

    def test_currency_pound(self):
        series = pd.Series(["£100.00", "£250.50", "£1000.00"])
        assert infer_column_type(series) == ColumnType.CURRENCY

    def test_percentage(self):
        series = pd.Series(["50%", "75%", "100%", "25.5%"])
        assert infer_column_type(series) == ColumnType.PERCENTAGE

    def test_categorical_low_cardinality(self):
        series = pd.Series(["red", "blue", "green"] * 100)
        assert infer_column_type(series) == ColumnType.CATEGORICAL

    def test_text_high_cardinality(self):
        series = pd.Series([f"unique_value_{i}" for i in range(100)])
        assert infer_column_type(series) == ColumnType.TEXT

    def test_empty_series(self):
        series = pd.Series([], dtype=object)
        assert infer_column_type(series) == ColumnType.TEXT

    def test_all_null_series(self):
        series = pd.Series([None, None, None])
        assert infer_column_type(series) == ColumnType.TEXT

    def test_mixed_with_nulls(self):
        series = pd.Series([1, 2, None, 4, 5])
        assert infer_column_type(series) == ColumnType.FLOAT  # pandas coerces to float with NaN
