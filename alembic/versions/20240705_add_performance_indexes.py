# alembic/versions/20240705_add_performance_indexes.py - FIXED for PostgreSQL

"""Add performance indexes for analytics queries

Revision ID: add_performance_indexes
Revises:
Create Date: 2024-07-05
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "add_performance_indexes"
down_revision = None  # First migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ✅ Simple CREATE INDEX statements - PostgreSQL compatible
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_transactions_tenant ON transactions(tenant_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_transactions_tenant_date ON transactions(tenant_id, date DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_transactions_tenant_counterparty ON transactions(tenant_id, counterparty)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_transactions_tenant_type ON transactions(tenant_id, transaction_type)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_transactions_tenant_category ON transactions(tenant_id, category)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_transactions_tenant_category")
    op.execute("DROP INDEX IF EXISTS idx_transactions_tenant_type")
    op.execute("DROP INDEX IF EXISTS idx_transactions_tenant_counterparty")
    op.execute("DROP INDEX IF EXISTS idx_transactions_tenant_date")
    op.execute("DROP INDEX IF EXISTS idx_transactions_tenant")
