"""Validate, audit, and transform raw Online Retail II transactions."""

import logging
from decimal import Decimal, InvalidOperation

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

COLUMN_NAMES = {
    "Invoice": "invoice_no",
    "StockCode": "stock_code",
    "Description": "description",
    "Quantity": "quantity",
    "InvoiceDate": "invoice_date",
    "Price": "unit_price",
    "Customer ID": "customer_id",
    "Country": "country",
}
OUTPUT_DTYPES = {
    "invoice_no": "string",
    "stock_code": "string",
    "description": "string",
    "quantity": "int64",
    "invoice_date": "datetime64[us]",
    "unit_price": "float64",
    "customer_id": "string",
    "country": "string",
    "total_amount": "float64",
    "is_cancelled": "bool",
    "is_return": "bool",
}
TEXT_COLUMNS = ("Invoice", "StockCode", "Description", "Customer ID", "Country")
REQUIRED_TEXT = ("Invoice", "StockCode", "Country")
INT64_MIN, INT64_MAX = -(2**63), 2**63 - 1
DATE_PATTERN = r"[0-9]{4}-[0-9]{2}-[0-9]{2}[ T][0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?"


def validate_schema(df: pd.DataFrame) -> None:
    """Raise on structural errors in a raw Extract DataFrame."""
    logger.info("[VALIDATE] Checking input type and raw schema")
    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"Expected a pandas DataFrame, got {type(df).__name__}")
    if len(df) == 0:
        raise ValueError("Raw DataFrame is empty")
    if not df.columns.is_unique:
        raise ValueError("Raw DataFrame contains duplicate column names")

    missing = [column for column in COLUMN_NAMES if column not in df.columns]
    unexpected = [column for column in df.columns if column not in COLUMN_NAMES]
    if missing or unexpected:
        raise ValueError(f"Raw schema mismatch: missing={missing}, unexpected={unexpected}")
    logger.info("[VALIDATE] Required columns verified for %d rows", len(df))


def _trim_text(values: pd.Series) -> pd.Series:
    text = values.astype("string").str.strip()
    return text.mask(text.eq("") | text.str.contains("\x00", regex=False))


def _parse_integer(value: object) -> int | None:
    try:
        number = Decimal(value) if isinstance(value, float) else Decimal(str(value))
    except InvalidOperation:
        return None
    if number.is_finite() and INT64_MIN <= number <= INT64_MAX:
        if number == number.to_integral_value():
            return int(number)
    return None


def _parse_quantity(values: pd.Series) -> pd.Series:
    if pd.api.types.is_integer_dtype(values.dtype):
        within_range = values.le(INT64_MAX)
        return values.where(within_range, 0).astype("Int64").where(within_range)

    # Decimal keeps quantities near the bigint limit exact when parsing mixed input.
    integers = np.array([_parse_integer(value) for value in values], dtype=object)
    return pd.Series(integers, index=values.index, dtype="Int64")


def _parse_price(values: pd.Series) -> pd.Series:
    if not pd.api.types.is_any_real_numeric_dtype(values.dtype):
        values = _trim_text(values)
    price = pd.to_numeric(values, errors="coerce").astype("float64")
    return price.where(np.isfinite(price))


def _parse_invoice_date(values: pd.Series) -> pd.Series:
    if isinstance(values.dtype, pd.DatetimeTZDtype):
        return pd.Series(pd.NaT, index=values.index, dtype="datetime64[us]")
    if pd.api.types.is_datetime64_any_dtype(values.dtype):
        return values.where(values.dt.nanosecond.eq(0)).astype("datetime64[us]")

    text = _trim_text(values)
    text = text.where(text.str.fullmatch(DATE_PATTERN, na=False))
    return pd.to_datetime(text, format="ISO8601", errors="coerce").astype("datetime64[us]")


def _total_amount(quantity: pd.Series, price: pd.Series) -> pd.Series:
    with np.errstate(over="ignore"):
        return quantity.astype("float64") * price


def _prepare_rows(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    prepared = pd.DataFrame(index=df.index)
    for column in TEXT_COLUMNS:
        prepared[column] = _trim_text(df[column])

    customer = prepared["Customer ID"].str.replace(r"\.0+$", "", regex=True)
    valid_customer = customer.str.fullmatch(r"[0-9]*[1-9][0-9]*", na=False)
    prepared["Customer ID"] = customer.where(valid_customer)
    prepared["Quantity"] = _parse_quantity(df["Quantity"])
    prepared["Price"] = _parse_price(df["Price"])
    prepared["InvoiceDate"] = _parse_invoice_date(df["InvoiceDate"])

    quantity, price = prepared["Quantity"], prepared["Price"]
    issues = prepared[list(REQUIRED_TEXT)].isna().add_prefix("missing_")
    issues["invalid_or_missing_quantity"] = quantity.isna()
    issues["invalid_or_missing_price"] = price.isna()
    issues["invalid_or_missing_invoice_date"] = prepared["InvoiceDate"].isna()
    issues["negative_price"] = price.lt(0)
    issues["non_finite_total"] = np.isinf(_total_amount(quantity, price))
    return prepared, issues


def _sign_counts(values: pd.Series) -> dict[str, int]:
    return {
        "negative": int(values.lt(0).sum()),
        "zero": int(values.eq(0).sum()),
        "positive": int(values.gt(0).sum()),
    }


def _quality_report(
    df: pd.DataFrame, prepared: pd.DataFrame, issues: pd.DataFrame
) -> dict:
    missing = df.isna().sum()
    duplicate_rows = df.duplicated()
    cancelled = prepared["Invoice"].str.upper().str.startswith("C", na=False)
    returns = prepared["Quantity"].lt(0).fillna(False)
    rejected = issues.any(axis=1)
    invalid_conversions = {
        column: int((df[column].notna() & prepared[column].isna()).sum())
        for column in ("Quantity", "Price", "InvoiceDate", "Customer ID")
    }
    logger.info("[QUALITY] Missing values by raw column: %s", missing.to_dict())
    logger.info(
        "[QUALITY] Duplicate records: %d; invalid conversions: %s",
        duplicate_rows.sum(),
        invalid_conversions,
    )

    return {
        "rows": len(df),
        "column_count": len(df.columns),
        "columns": list(df.columns),
        "dtypes": df.dtypes.astype(str).to_dict(),
        "missing": {
            column: {"count": int(count), "percent": float(count / len(df) * 100)}
            for column, count in missing.items()
        },
        "duplicate_rows": int(duplicate_rows.sum()),
        "duplicate_ratio": float(duplicate_rows.mean()),
        "quantity": _sign_counts(prepared["Quantity"]),
        "price": _sign_counts(prepared["Price"]),
        "cancellation_rows": int(cancelled.sum()),
        "negative_quantity_cancellation_rows": int((cancelled & returns).sum()),
        "invalid_conversions": invalid_conversions,
        "optional_nulls_after_normalization": {
            column: int(prepared[column].isna().sum())
            for column in ("Customer ID", "Description")
        },
        "duplicate_rows_retained": int((duplicate_rows & ~rejected).sum()),
        "filter_reasons": {reason: int(count) for reason, count in issues.sum().items()},
        "rows_rejected": int(rejected.sum()),
        "rows_retained": int((~rejected).sum()),
    }


def assess_data_quality(df: pd.DataFrame) -> dict:
    """Return raw metrics and the expected impact of cleaning."""
    validate_schema(df)
    prepared, issues = _prepare_rows(df)
    return _quality_report(df, prepared, issues)


def _clean_rows(prepared: pd.DataFrame, issues: pd.DataFrame) -> pd.DataFrame:
    logger.info("[CLEAN] Applying cleaning rules to %d rows", len(prepared))
    rejected = issues.any(axis=1)
    cleaned = prepared.loc[~rejected, list(COLUMN_NAMES)].reset_index(drop=True)
    cleaned["Quantity"] = cleaned["Quantity"].astype("int64")
    logger.info("[CLEAN] Rows after cleaning: %d; removed: %d", len(cleaned), rejected.sum())
    if rejected.any():
        reasons = {reason: int(count) for reason, count in issues.sum().items() if count}
        logger.warning("[CLEAN] Rejection reasons (may overlap): %s", reasons)
        if cleaned.empty:
            raise ValueError(f"No valid transactions remain after cleaning: {reasons}")
    return cleaned


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize and filter raw rows while keeping the source column names."""
    validate_schema(df)
    return _clean_rows(*_prepare_rows(df))


def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    """Build the final schema from the result of clean_data."""
    result = df.rename(columns=COLUMN_NAMES)
    logger.info("[TRANSFORM] Calculating total_amount")
    result["total_amount"] = _total_amount(result["quantity"], result["unit_price"])
    result["is_cancelled"] = result["invoice_no"].str.upper().str.startswith("C").astype(bool)
    result["is_return"] = result["quantity"].lt(0)
    if result.dtypes.astype(str).to_dict() != OUTPUT_DTYPES or list(result) != list(OUTPUT_DTYPES):
        raise ValueError("Transformed DataFrame does not match the output schema")
    logger.info("[TRANSFORM] Output schema verified")
    return result


def validate_and_transform(df: pd.DataFrame) -> pd.DataFrame:
    """Turn a raw Extract DataFrame into a cleaned transaction DataFrame."""
    validate_schema(df)
    prepared, issues = _prepare_rows(df)
    audit = _quality_report(df, prepared, issues)
    logger.info(
        "[QUALITY] Cancellations: %d; negative quantity: %d; zero price: %d",
        audit["cancellation_rows"],
        audit["quantity"]["negative"],
        audit["price"]["zero"],
    )
    result = transform_data(_clean_rows(prepared, issues))
    logger.info("[PIPELINE] Validate & Transform completed with %d rows", len(result))
    return result
