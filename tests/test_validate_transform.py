import json
import logging

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from src.extract import extract_data
from src.validate_transform import (
    assess_data_quality,
    clean_data,
    transform_data,
    validate_and_transform,
    validate_schema,
)


@pytest.fixture
def raw():
    row = {
        "Invoice": "000123",
        "StockCode": "0007A",
        "Description": " GLASS  MUG ",
        "Quantity": 3,
        "InvoiceDate": "2009-12-01 07:45:00",
        "Price": 2.5,
        "Customer ID": 13085.0,
        "Country": " United Kingdom ",
    }
    return pd.DataFrame([row])


def test_valid_structure_accepts_reordered_columns(raw, caplog):
    with caplog.at_level(logging.INFO):
        validate_schema(raw[raw.columns[::-1]])
    assert "Required columns verified for 1 rows" in caplog.text


@pytest.mark.parametrize(
    ("invalid", "error", "message"),
    [
        (lambda raw: raw.to_dict(), TypeError, "Expected a pandas DataFrame"),
        (lambda raw: raw.iloc[:0], ValueError, "Raw DataFrame is empty"),
        (lambda raw: raw.drop(columns="Price"), ValueError, "missing=.*Price"),
        (lambda raw: raw.assign(Extra=1), ValueError, "unexpected=.*Extra"),
        (
            lambda raw: raw.rename(columns={"Price": "Quantity"}),
            ValueError,
            "duplicate column names",
        ),
    ],
    ids=["wrong-type", "empty", "missing-column", "unexpected-column", "duplicate-label"],
)
def test_fatal_schema_errors(raw, invalid, error, message):
    with pytest.raises(error, match=message):
        validate_and_transform(invalid(raw))


@pytest.mark.parametrize(
    ("column", "value", "reason"),
    [
        ("Quantity", "three", "invalid_or_missing_quantity"),
        ("Quantity", "0.9999999999999999999", "invalid_or_missing_quantity"),
        ("Quantity", str(2**63), "invalid_or_missing_quantity"),
        ("Quantity", None, "invalid_or_missing_quantity"),
        ("Price", "free", "invalid_or_missing_price"),
        ("Price", float("inf"), "invalid_or_missing_price"),
        ("Price", True, "invalid_or_missing_price"),
        ("InvoiceDate", "2009-02-30 07:45:00", "invalid_or_missing_invoice_date"),
        ("InvoiceDate", "01/12/2009 07:45", "invalid_or_missing_invoice_date"),
        ("InvoiceDate", "2009-12-01T07:45:00Z", "invalid_or_missing_invoice_date"),
        ("Invoice", " ", "missing_Invoice"),
        ("StockCode", None, "missing_StockCode"),
        ("Country", " ", "missing_Country"),
        ("Price", -0.01, "negative_price"),
        ("Price", 1e308, "non_finite_total"),
    ],
)
def test_recoverable_invalid_row(raw, column, value, reason):
    bad = raw.assign(**{column: pd.Series([value], index=raw.index, dtype=object)})
    batch = pd.concat([raw, bad])
    audit = assess_data_quality(batch)

    assert audit["filter_reasons"][reason] == 1
    assert audit["rows_rejected"] == 1
    assert_frame_equal(validate_and_transform(batch), validate_and_transform(raw))


def test_all_rows_rejected_raises(raw):
    with pytest.raises(ValueError, match="No valid transactions remain.*negative_price"):
        validate_and_transform(raw.assign(Price=-1))


def test_optional_fields_remain_nullable(raw):
    batch = pd.concat(
        [
            raw.assign(Description=None, **{"Customer ID": None}),
            raw.assign(Description=" ", **{"Customer ID": "invalid"}),
            raw.assign(**{"Customer ID": " 00123.00 "}),
        ],
        ignore_index=True,
    )
    audit = assess_data_quality(batch)
    result = validate_and_transform(batch)

    assert len(result) == 3
    assert result["description"].isna().tolist() == [True, True, False]
    assert result["customer_id"].isna().tolist() == [True, True, False]
    assert result.at[2, "customer_id"] == "00123"
    assert audit["missing"]["Customer ID"]["count"] == 1
    assert audit["invalid_conversions"]["Customer ID"] == 1
    assert audit["optional_nulls_after_normalization"] == {"Customer ID": 2, "Description": 2}


def test_full_row_duplicates_are_retained_and_audited(raw):
    batch = pd.concat([raw, raw, raw.assign(Price=-1), raw.assign(Price=-1)])
    audit = assess_data_quality(batch)
    result = validate_and_transform(batch)

    assert audit["duplicate_rows"] == 2
    assert audit["duplicate_ratio"] == 0.5
    assert audit["duplicate_rows_retained"] == 1
    assert result.duplicated().sum() == 1
    assert len(result) == 2


def test_cancellation_return_and_zero_values(raw):
    batch = pd.concat(
        [
            raw.assign(Invoice=" c001 ", Quantity=-2),
            raw.assign(Invoice="C002"),
            raw.assign(Invoice="003", Quantity=-1),
            raw.assign(Invoice="004", Price=0),
            raw.assign(Invoice="005", Quantity=0),
        ]
    )
    result = validate_and_transform(batch)
    assert result["is_cancelled"].tolist() == [True, True, False, False, False]
    assert result["is_return"].tolist() == [True, False, True, False, False]
    assert result["invoice_no"].tolist() == ["c001", "C002", "003", "004", "005"]
    assert result["total_amount"].tolist() == [-5.0, 7.5, -2.5, 0.0, 0.0]


def test_quality_report_is_serializable_and_counts_overlapping_issues(raw):
    batch = pd.concat(
        [
            raw,
            raw.assign(Invoice="C1", Quantity="-1"),
            raw.assign(Quantity="invalid", InvoiceDate="invalid", Price=-1),
            raw.assign(Quantity="0", Price=0),
            raw.assign(Quantity=None, Price=None),
        ]
    )
    before = batch.copy(deep=True)
    audit = json.loads(json.dumps(assess_data_quality(batch)))

    assert audit["rows"] == 5
    assert audit["column_count"] == 8
    assert audit["columns"] == list(raw.columns)
    assert audit["dtypes"] == batch.dtypes.astype(str).to_dict()
    assert audit["missing"]["Quantity"] == {"count": 1, "percent": 20.0}
    assert audit["invalid_conversions"] == {
        "Quantity": 1, "Price": 0, "InvoiceDate": 1, "Customer ID": 0
    }
    assert audit["quantity"] == {"negative": 1, "zero": 1, "positive": 1}
    assert audit["price"] == {"negative": 1, "zero": 1, "positive": 2}
    assert audit["cancellation_rows"] == audit["negative_quantity_cancellation_rows"] == 1
    assert sum(audit["filter_reasons"].values()) == 5
    assert audit["rows_rejected"] == 2
    assert audit["rows_retained"] == 3
    assert_frame_equal(batch, before)


def test_output_schema_values_and_types(raw):
    result = validate_and_transform(raw[raw.columns[::-1]])
    assert list(result.dtypes.astype(str).items()) == [
        ("invoice_no", "string"),
        ("stock_code", "string"),
        ("description", "string"),
        ("quantity", "int64"),
        ("invoice_date", "datetime64[us]"),
        ("unit_price", "float64"),
        ("customer_id", "string"),
        ("country", "string"),
        ("total_amount", "float64"),
        ("is_cancelled", "bool"),
        ("is_return", "bool"),
    ]
    assert result.iloc[0].to_dict() == {
        "invoice_no": "000123",
        "stock_code": "0007A",
        "description": "GLASS  MUG",
        "quantity": 3,
        "invoice_date": pd.Timestamp("2009-12-01 07:45:00"),
        "unit_price": 2.5,
        "customer_id": "13085",
        "country": "United Kingdom",
        "total_amount": 7.5,
        "is_cancelled": False,
        "is_return": False,
    }


@pytest.mark.parametrize("typed", [False, True], ids=["iso-text", "datetime"])
def test_invoice_date_preserves_microseconds(raw, typed):
    value = "2009-12-01T07:45:00.123456"
    result = validate_and_transform(raw.assign(InvoiceDate=pd.Timestamp(value) if typed else value))
    assert result.at[0, "invoice_date"] == pd.Timestamp(value)


@pytest.mark.parametrize("unsigned", [False, True], ids=["mixed-text", "uint64"])
def test_exact_quantity_near_bigint_limit(raw, unsigned):
    batch = pd.concat([raw, raw], ignore_index=True)
    quantities = [2**63 - 1, 2**63]
    if unsigned:
        batch["Quantity"] = pd.Series(quantities, dtype="uint64")
    else:
        batch["Quantity"] = [str(value) for value in quantities]
    result = validate_and_transform(batch)
    assert result["quantity"].tolist() == [2**63 - 1]


def test_pipeline_is_repeatable_and_leaves_input_unchanged(raw):
    before = raw.copy(deep=True)
    first = validate_and_transform(raw)
    assert_frame_equal(first, validate_and_transform(raw))
    assert_frame_equal(first, transform_data(clean_data(raw)))
    assert_frame_equal(raw, before)
    with pytest.raises(ValueError, match="Raw schema mismatch"):
        validate_and_transform(first)


def test_pipeline_logs_counts_and_reasons(raw, caplog):
    with caplog.at_level(logging.INFO):
        validate_and_transform(pd.concat([raw, raw.assign(Price=-1)]))

    for message in (
        "[VALIDATE] Required columns verified",
        "[QUALITY] Missing values",
        "[QUALITY] Duplicate records: 0",
        "[CLEAN] Applying cleaning rules to 2 rows",
        "[CLEAN] Rows after cleaning: 1; removed: 1",
        "'negative_price': 1",
        "[TRANSFORM] Calculating total_amount",
        "[TRANSFORM] Output schema verified",
        "[PIPELINE] Validate & Transform completed with 1 rows",
    ):
        assert message in caplog.text


def test_extract_pickle_handoff(raw, tmp_path):
    csv_path = tmp_path / "retail.csv"
    raw.to_csv(csv_path, index=False)
    raw_path = extract_data(path=csv_path, output_path=tmp_path / "retail_raw.pkl")

    assert isinstance(raw_path, str)
    result = validate_and_transform(pd.read_pickle(raw_path))
    assert_frame_equal(result, validate_and_transform(raw))
