
from datetime import date

import pandas as pd
from sqlalchemy import create_engine, text

from src.pipeline import database_url, load_to_postgres


TEST_ORDER_ID = "TEST-UPSERT-999"


def test_upsert_inserts_updates_without_duplicates():
    engine = create_engine(database_url())

    first_order = pd.DataFrame([{
        "order_id": TEST_ORDER_ID,
        "order_date": date(2026, 1, 10),
        "customer_id": "TEST-C01",
        "product": "Test Mouse",
        "quantity": 2,
        "unit_price": 19.99,
        "country": "Spain",
    }])

    updated_order = first_order.copy()
    updated_order.loc[0, "product"] = "Updated Test Mouse"
    updated_order.loc[0, "quantity"] = 3

    try:
        # Remove leftovers from a previous test run.
        with engine.begin() as conn:
            conn.execute(
                text("""
                    DELETE FROM retail_orders
                    WHERE order_id = :order_id
                """),
                {"order_id": TEST_ORDER_ID},
            )

        # First load inserts the order.
        assert load_to_postgres(first_order) == 1

        # Second load updates the same order.
        assert load_to_postgres(updated_order) == 1

        with engine.connect() as conn:
            rows = conn.execute(
                text("""
                    SELECT product, quantity, COUNT(*) OVER () AS total
                    FROM retail_orders
                    WHERE order_id = :order_id
                """),
                {"order_id": TEST_ORDER_ID},
            ).mappings().all()

        assert len(rows) == 1
        assert rows[0]["product"] == "Updated Test Mouse"
        assert rows[0]["quantity"] == 3
        assert rows[0]["total"] == 1

    finally:
        # Keep the database clean after the test.
        with engine.begin() as conn:
            conn.execute(
                text("""
                    DELETE FROM retail_orders
                    WHERE order_id = :order_id
                """),
                {"order_id": TEST_ORDER_ID},
            )
        engine.dispose()
