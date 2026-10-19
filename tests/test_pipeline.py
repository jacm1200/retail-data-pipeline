
import pandas as pd

from src.pipeline import clean_and_validate, parse_price


def test_parse_price():
    assert parse_price("19.99") == 19.99
    assert parse_price("49,90") == 49.90
    assert parse_price("€179,99") == 179.99


def test_parse_invalid_price():
    assert pd.isna(parse_price("not_a_price"))
    assert pd.isna(parse_price(""))


def test_clean_and_validate_removes_exact_duplicates():
    data = pd.DataFrame({
        "order_id": ["1001", "1001"],
        "order_date": ["2026-01-10", "2026-01-10"],
        "customer_id": ["C01", "C01"],
        "product": ["Laptop", "Laptop"],
        "quantity": ["2", "2"],
        "unit_price": ["100.00", "100.00"],
        "country": ["Spain", "Spain"],
    })

    clean, rejected, report = clean_and_validate(data)

    assert len(clean) == 1
    assert len(rejected) == 0
    assert report["exact_duplicates_removed"] == 1


def test_clean_and_validate_rejects_invalid_quantity():
    data = pd.DataFrame({
        "order_id": ["1002"],
        "order_date": ["2026-01-10"],
        "customer_id": ["C02"],
        "product": ["Mouse"],
        "quantity": ["0"],
        "unit_price": ["20.00"],
        "country": ["Spain"],
    })

    clean, rejected, report = clean_and_validate(data)

    assert len(clean) == 0
    assert len(rejected) == 1
    assert "quantity_must_be_positive" in (
        rejected.iloc[0]["rejection_reason"]
    )
    assert report["rejected_rows"] == 1
