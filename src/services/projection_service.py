# src/services/projection_service.py - NEW

import logging
from typing import Any, Dict, List

from sqlalchemy import func
from sqlalchemy.orm import Session
from src.models.analytics_snapshot import AnalyticsSnapshot
from src.models.counterparty_directory import CounterpartyDirectory
from src.models.transaction import Transaction
from src.services.health_score_service import HealthScoreService

logger = logging.getLogger(__name__)


class ProjectionService:
    """Clean projection layer - separates read from write models"""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def refresh_snapshot(self, upload_id: str = None) -> AnalyticsSnapshot:
        """Refresh analytics snapshot"""

        snapshot = (
            self.db.query(AnalyticsSnapshot)
            .filter(AnalyticsSnapshot.tenant_id == self.tenant_id)
            .first()
        )

        if not snapshot:
            snapshot = AnalyticsSnapshot(tenant_id=self.tenant_id)
            self.db.add(snapshot)
            return self._build_full(snapshot)

        return self._update_incremental(snapshot, upload_id)

    def _build_full(self, snapshot: AnalyticsSnapshot) -> AnalyticsSnapshot:
        """Full rebuild (first time)"""

        result = (
            self.db.query(
                func.count(Transaction.id).label("total_transactions"),
                func.count(func.distinct(Transaction.counterparty)).label(
                    "unique_counterparties"
                ),
                func.sum(Transaction.amount)
                .filter(Transaction.amount > 0)
                .label("total_received"),
                func.sum(Transaction.amount)
                .filter(Transaction.amount < 0)
                .label("total_sent"),
                func.min(Transaction.date).label("first_date"),
                func.max(Transaction.date).label("last_date"),
            )
            .filter(Transaction.tenant_id == self.tenant_id)
            .first()
        )

        if not result or result.total_transactions == 0:
            return snapshot

        snapshot.total_transactions = result.total_transactions
        snapshot.unique_counterparties = result.unique_counterparties
        snapshot.total_received = abs(float(result.total_received or 0))
        snapshot.total_sent = abs(float(result.total_sent or 0))
        snapshot.net_flow = snapshot.total_received - snapshot.total_sent
        snapshot.first_transaction_date = result.first_date
        snapshot.last_transaction_date = result.last_date

        self._update_health_score(snapshot)
        self.db.commit()
        return snapshot

    def _update_incremental(
        self, snapshot: AnalyticsSnapshot, upload_id: str
    ) -> AnalyticsSnapshot:
        """Incremental update"""

        # Get transactions for this upload
        transactions = (
            self.db.query(Transaction)
            .filter(
                Transaction.tenant_id == self.tenant_id,
                Transaction.upload_id == upload_id,
            )
            .all()
        )

        if not transactions:
            return snapshot

        # Calculate deltas
        total_received = sum(float(t.amount) for t in transactions if t.amount > 0)
        total_sent = sum(float(abs(t.amount)) for t in transactions if t.amount < 0)
        total_count = len(transactions)

        # Update aggregates
        snapshot.total_transactions += total_count
        snapshot.total_received += total_received
        snapshot.total_sent += total_sent
        snapshot.net_flow = snapshot.total_received - snapshot.total_sent

        # Update counterparty count from directory
        actual_count = (
            self.db.query(func.count(CounterpartyDirectory.id))
            .filter(
                CounterpartyDirectory.tenant_id == self.tenant_id,
                CounterpartyDirectory.is_active == True,
            )
            .scalar()
            or 0
        )
        snapshot.unique_counterparties = actual_count

        # Update timestamps
        if transactions:
            dates = [t.date for t in transactions if t.date]
            if dates:
                if (
                    not snapshot.first_transaction_date
                    or min(dates) < snapshot.first_transaction_date
                ):
                    snapshot.first_transaction_date = min(dates)
                if (
                    not snapshot.last_transaction_date
                    or max(dates) > snapshot.last_transaction_date
                ):
                    snapshot.last_transaction_date = max(dates)

        snapshot.last_upload_id = upload_id
        snapshot.last_imported_at = datetime.utcnow()
        snapshot.is_stale = False

        self._update_health_score(snapshot)
        self.db.commit()

        return snapshot

    def _update_health_score(self, snapshot: AnalyticsSnapshot):
        """Update health score"""

        health_result = HealthScoreService.calculate(
            money_in=snapshot.total_received,
            money_out=snapshot.total_sent,
            net_flow=snapshot.net_flow,
            total_transactions=snapshot.total_transactions,
            unique_counterparties=snapshot.unique_counterparties,
        )

        snapshot.health_score = health_result["score"]
        snapshot.grade = health_result["grade"]
        snapshot.savings_rate = health_result["savings_rate"]
        snapshot.snapshot_version = HealthScoreService.VERSION
