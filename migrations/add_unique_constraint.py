"""
Migration: Add unique constraint on (transaction_id, tenant_id)
Run with: python migrations/add_unique_constraint.py
"""

import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DB_PATH = os.getenv("DATABASE_URL", "sqlite:///./analytics.db").replace(
    "sqlite:///", ""
)


def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if constraint already exists
        cursor.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='transactions'"
        )
        result = cursor.fetchone()

        if result and "UNIQUE" not in result[0]:
            print("Adding unique constraint...")
            # SQLite doesn't support ALTER TABLE ADD CONSTRAINT
            # Need to recreate table
            cursor.execute("ALTER TABLE transactions RENAME TO transactions_old")

            cursor.execute("""
                CREATE TABLE transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    transaction_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    date TIMESTAMP,
                    amount FLOAT,
                    transaction_type TEXT,
                    counterparty TEXT,
                    category TEXT,
                    description TEXT,
                    raw_text TEXT,
                    created_at TIMESTAMP,
                    UNIQUE(transaction_id, tenant_id)
                )
            """)

            cursor.execute("""
                INSERT INTO transactions (id, transaction_id, tenant_id, date, amount, transaction_type, counterparty, category, description, raw_text, created_at)
                SELECT id, transaction_id, tenant_id, date, amount, transaction_type, counterparty, category, description, raw_text, created_at
                FROM transactions_old
            """)

            cursor.execute("DROP TABLE transactions_old")
            print("✅ Unique constraint added successfully")

    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.commit()
        conn.close()


if __name__ == "__main__":
    migrate()
