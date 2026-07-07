# scripts/explain_analyze.py - Run this in your Python environment

import asyncio

from sqlalchemy import text
from src.core.database import SessionLocal
from src.models.transaction import Transaction


async def run_explain_analyze():
    """Run EXPLAIN ANALYZE on the critical queries"""
    db = SessionLocal()
    tenant_id = "tenant_ee51aabfb07b"  # ⚠️ REPLACE with your actual tenant

    print("=" * 60)
    print("📊 EXPLAIN ANALYZE RESULTS")
    print("=" * 60)

    # Query 1: Summary
    print("\n🔍 QUERY 1: Summary Aggregation")
    print("-" * 40)
    result = db.execute(
        text("""
        EXPLAIN ANALYZE
        SELECT
            COALESCE(SUM(amount) FILTER (WHERE transaction_type = 'received'), 0) as money_in,
            COALESCE(SUM(amount) FILTER (WHERE transaction_type = 'sent'), 0) as money_out,
            COUNT(*) as total_transactions,
            COUNT(DISTINCT counterparty) as unique_counterparties
        FROM transactions
        WHERE tenant_id = :tenant_id
    """),
        {"tenant_id": tenant_id},
    )

    for row in result:
        print(row[0])

    # Query 2: Counterparties
    print("\n🔍 QUERY 2: Top Counterparties")
    print("-" * 40)
    result = db.execute(
        text("""
        EXPLAIN ANALYZE
        SELECT
            counterparty,
            COALESCE(SUM(amount) FILTER (WHERE transaction_type = 'sent'), 0) as sent,
            COALESCE(SUM(amount) FILTER (WHERE transaction_type = 'received'), 0) as received,
            COUNT(*) as count
        FROM transactions
        WHERE tenant_id = :tenant_id
            AND counterparty IS NOT NULL
            AND counterparty != ''
            AND counterparty != 'Unknown'
        GROUP BY counterparty
        ORDER BY COUNT(*) DESC
        LIMIT 20
    """),
        {"tenant_id": tenant_id},
    )

    for row in result:
        print(row[0])

    # Query 3: Recent Transactions
    print("\n🔍 QUERY 3: Recent Transactions")
    print("-" * 40)
    result = db.execute(
        text("""
        EXPLAIN ANALYZE
        SELECT *
        FROM transactions
        WHERE tenant_id = :tenant_id
        ORDER BY date DESC
        LIMIT 8
    """),
        {"tenant_id": tenant_id},
    )

    for row in result:
        print(row[0])

    db.close()
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(run_explain_analyze())
