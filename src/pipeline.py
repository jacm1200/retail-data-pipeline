"""Starter retail CSV cleaning and loading pipeline."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
RAW_FILE = ROOT / "data" / "raw" / "orders_dirty.csv"
CLEAN_FILE = ROOT / "data" / "processed" / "orders_clean.csv"
REJECTED_FILE = ROOT / "data" / "rejected" / "orders_rejected.csv"
REPORT_FILE = ROOT / "data" / "reports" / "quality_report.json"

REQUIRED_COLUMNS = [
    "order_id", "order_date", "customer_id", "product",
    "quantity", "unit_price", "country"
]

logger = logging.getLogger(__name__)


def parse_price(value):
    """Parse values such as '12.50', '12,50' and '€12,50'."""
    if pd.isna(value):
        return pd.NA
    value = str(value).strip().replace("€", "").replace("$", "").replace(" ", "")
    if not value:
        return pd.NA
    # For this sample dataset, a comma is treated as the decimal separator.
    if "," in value and "." not in value:
        value = value.replace(",", ".")
    elif "," in value and "." in value:
        # Treat the last separator as decimal when both are present.
        if value.rfind(",") > value.rfind("."):
            value = value.replace(".", "").replace(",", ".")
        else:
            value = value.replace(",", "")
    try:
        return float(value)
    except ValueError:
        return pd.NA


def load_raw_data(path: Path) -> pd.DataFrame:
    logger.info("Reading input CSV: %s", path)
    if not path.exists():
        raise FileNotFoundError(f"Input CSV not found: {path}")
    df = pd.read_csv(path, dtype="string")
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    missing = sorted(set(REQUIRED_COLUMNS) - set(df.columns))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    logger.info("Read %d input records from %s", len(df), path)
    return df


def clean_and_validate(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    original_count = len(df)
    df = df.copy()

    for col in ["order_id", "customer_id", "product", "country"]:
        df[col] = df[col].astype("string").str.strip()
        df[col] = df[col].replace("", pd.NA)

    # Parse multiple common date formats, including day-first dates.
    raw_dates = df["order_date"].astype("string").str.strip()
    parsed_dates = pd.to_datetime(
        raw_dates, errors="coerce", 
        format="mixed", 
        dayfirst=True)
    
    df["order_date"] = parsed_dates.dt.strftime("%Y-%m-%d")

    df["quantity"] = pd.to_numeric(
        df["quantity"].str.strip(), 
        errors="coerce")
    
    df["unit_price"] = pd.to_numeric(
        df["unit_price"].map(parse_price), 
        errors="coerce")
    
    df["country"] = df["country"].str.title()
    df["product"] = df["product"].str.title()

    # Remove exact duplicate rows before applying business rules.
    before_dedup = len(df)
    df = df.drop_duplicates()
    exact_duplicates_removed = before_dedup - len(df)

    required_fields = ["order_id", "order_date", "product", "quantity", "unit_price"]
    missing_required = df[required_fields].isna().any(axis=1)
    invalid_quantity = df["quantity"].notna() & (df["quantity"] <= 0)
    invalid_price = df["unit_price"].notna() & (df["unit_price"] < 0)
    rejected_mask = missing_required | invalid_quantity | invalid_price

    rejected = df.loc[rejected_mask].copy()
    rejected["rejection_reason"] = rejected.apply(
        lambda row: "; ".join(
            reason for condition, reason in [
                (row[required_fields].isna().any(), "missing_or_unparseable_required_field"),
                (pd.notna(row["quantity"]) and row["quantity"] <= 0, "quantity_must_be_positive"),
                (pd.notna(row["unit_price"]) and row["unit_price"] < 0, "unit_price_must_be_non_negative"),
            ] if condition
        ),
        axis=1,
    )

    clean = df.loc[~rejected_mask].copy()
    clean["quantity"] = clean["quantity"].astype(int)
    clean["unit_price"] = clean["unit_price"].astype(float)
    clean["order_date"] = pd.to_datetime(clean["order_date"]).dt.date
    clean["customer_id"] = clean["customer_id"].astype("string")

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_file": str(RAW_FILE.relative_to(ROOT)),
        "input_rows": int(original_count),
        "exact_duplicates_removed": int(exact_duplicates_removed),
        "valid_rows": int(len(clean)),
        "rejected_rows": int(len(rejected)),
        "rejection_reasons": {
            "missing_or_unparseable_required_field": int(missing_required.sum()),
            "quantity_must_be_positive": int(invalid_quantity.sum()),
            "unit_price_must_be_non_negative": int(invalid_price.sum()),
        },
        "quality_rate_percent": round((len(clean) / original_count * 100), 2) if original_count else 0,
    }
    return clean, rejected, report


def database_url() -> str:
    load_dotenv(ROOT / ".env")
    user = os.getenv("POSTGRES_USER", "retail_user")
    password = os.getenv("POSTGRES_PASSWORD", "change_this_local_password")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "retail_db")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"



def load_to_postgres(df: pd.DataFrame) -> int:
    logger.info("Loading %d valid records into PostgreSQL", len(df))
    engine = create_engine(database_url())

    try:
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS retail_orders (
                    order_id TEXT PRIMARY KEY,
                    order_date DATE NOT NULL,
                    customer_id TEXT,
                    product TEXT NOT NULL,
                    quantity INTEGER NOT NULL CHECK (quantity > 0),
                    unit_price NUMERIC(12, 2) NOT NULL
                        CHECK (unit_price >= 0),
                    country TEXT
                )
            """))

            # Convert pandas missing values to Python None.
            records = (
                df.astype(object)
                .where(pd.notna(df), None)
                .to_dict(orient="records")
            )

            if records:
                conn.execute(
                    text("""
                        INSERT INTO retail_orders (
                            order_id, order_date, customer_id,
                            product, quantity, unit_price, country
                        )
                        VALUES (
                            :order_id, :order_date, :customer_id,
                            :product, :quantity, :unit_price, :country
                        )
                        ON CONFLICT (order_id) DO UPDATE SET
                            order_date = EXCLUDED.order_date,
                            customer_id = EXCLUDED.customer_id,
                            product = EXCLUDED.product,
                            quantity = EXCLUDED.quantity,
                            unit_price = EXCLUDED.unit_price,
                            country = EXCLUDED.country
                    """),
                    records,
                )

        logger.info("Upserted %d records into retail_orders", len(records))
        return len(records)

    finally:
        engine.dispose()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger.info("\n========== Pipeline started ==========\n")
    for directory in [CLEAN_FILE.parent, REJECTED_FILE.parent, REPORT_FILE.parent]:
        directory.mkdir(parents=True, exist_ok=True)

    raw = load_raw_data(RAW_FILE)
    clean, rejected, report = clean_and_validate(raw)
    logger.info(
        "Validation complete: input=%d, valid=%d, rejected=%d, exact_duplicates_removed=%d",
        report["input_rows"], report["valid_rows"], report["rejected_rows"],
        report["exact_duplicates_removed"],
    )

    clean.to_csv(CLEAN_FILE, index=False)
    logger.info("Saved %d valid records to %s", len(clean), CLEAN_FILE)
    rejected.to_csv(REJECTED_FILE, index=False)
    logger.info("Saved %d rejected records to %s", len(rejected), REJECTED_FILE)
    REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    logger.info("Saved quality report to %s", REPORT_FILE)

    try:
        loaded = load_to_postgres(clean)
        report["rows_upserted_to_postgres"] = loaded
        report["postgres_load_status"] = "success"
    except Exception as exc:
        report["rows_upserted_to_postgres"] = 0        
        report["postgres_load_status"] = "failed"
        report["postgres_error"] = str(exc)
        REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
        logger.exception("PostgreSQL load failed; updated quality report at %s", REPORT_FILE)
        raise

    REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    logger.info("\n========== Pipeline finished successfully ==========\n")


if __name__ == "__main__":
    main()
