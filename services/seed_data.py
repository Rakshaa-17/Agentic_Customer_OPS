"""
Realistic seed data for E-Commerce Customer Operations scenarios.
"""
import json
from typing import Optional
from services.db import get_connection, init_db

def seed_database(db_path: Optional[str] = None) -> None:
    init_db(db_path)
    conn = get_connection(db_path)
    with conn:
        # Clear existing
        conn.execute("DELETE FROM refund_transactions;")
        conn.execute("DELETE FROM payments;")
        conn.execute("DELETE FROM orders;")
        conn.execute("DELETE FROM customers;")

        # 1. Customers
        customers = [
            ("CUST-101", "Alice Vance", "alice@example.com", "vip", "+1-555-0101"),
            ("CUST-102", "Bob Smith", "bob.smith@example.com", "gold", "+1-555-0102"),
            ("CUST-103", "Charlie Davis", "charlie.davis@example.com", "regular", "+1-555-0103"),
            ("CUST-104", "Diana Prince", "diana.prince@example.com", "regular", "+1-555-0104"),
        ]
        conn.executemany(
            "INSERT INTO customers (id, name, email, tier, phone) VALUES (?, ?, ?, ?, ?);",
            customers
        )

        # 2. Orders
        # ORD-1001: Pending (Address change allowed, total $35.00)
        # ORD-1002: Delivered (Damaged item, total $24.99 -> < $50 auto-refund)
        # ORD-1003: Delivered (Expensive electronics, total $180.00 -> > $50 requires HITL approval)
        # ORD-1004: Shipped (In transit, address change NOT allowed)
        orders = [
            (
                "ORD-1001",
                "CUST-101",
                json.dumps([{"item_id": "SKU-A1", "name": "Organic Coffee Beans (2lb)", "qty": 1, "price": 35.00}]),
                35.00,
                "USD",
                "pending",
                "742 Evergreen Terrace, Springfield, OR 97477",
                None,
                "2026-11-20 10:00:00",
                None
            ),
            (
                "ORD-1002",
                "CUST-102",
                json.dumps([{"item_id": "SKU-B2", "name": "Ceramic Pour-Over Mug", "qty": 1, "price": 24.99}]),
                24.99,
                "USD",
                "delivered",
                "123 Elm Street, Austin, TX 78701",
                "TRK-98765432",
                "2026-11-10 14:30:00",
                "2026-11-13 16:00:00"
            ),
            (
                "ORD-1003",
                "CUST-103",
                json.dumps([{"item_id": "SKU-C3", "name": "Noise Cancelling Headphones", "qty": 1, "price": 180.00}]),
                180.00,
                "USD",
                "delivered",
                "456 Oak Avenue, Seattle, WA 98101",
                "TRK-11223344",
                "2026-11-05 09:15:00",
                "2026-11-09 11:20:00"
            ),
            (
                "ORD-1004",
                "CUST-104",
                json.dumps([{"item_id": "SKU-D4", "name": "Wireless Ergonomic Mouse", "qty": 1, "price": 45.00}]),
                45.00,
                "USD",
                "shipped",
                "89 Pine Road, Boulder, CO 80302",
                "TRK-55667788",
                "2026-11-18 11:00:00",
                None
            ),
        ]
        conn.executemany(
            """
            INSERT INTO orders 
            (id, customer_id, items_json, total_amount, currency, status, shipping_address, tracking_number, order_date, delivery_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            orders
        )

        # 3. Payments
        payments = [
            ("PAY-1001", "ORD-1001", 35.00, "USD", "completed", 0.0, "credit_card"),
            ("PAY-1002", "ORD-1002", 24.99, "USD", "completed", 0.0, "apple_pay"),
            ("PAY-1003", "ORD-1003", 180.00, "USD", "completed", 0.0, "credit_card"),
            ("PAY-1004", "ORD-1004", 45.00, "USD", "completed", 0.0, "paypal"),
        ]
        conn.executemany(
            """
            INSERT INTO payments (id, order_id, amount, currency, status, refunded_amount, payment_method)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            payments
        )
    conn.close()

if __name__ == "__main__":
    seed_database()
    print("Database initialized and seeded successfully.")
