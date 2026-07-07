# src/services/analytics_service.py - COMPLETE WITH SQL TIMING

import logging
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, case, desc, func, select, text
from sqlalchemy.orm import Session
from src.models.transaction import Transaction

logger = logging.getLogger(__name__)


# ============================================================
# PERFORMANCE PROFILING
# ============================================================


def profile_method(name: str):
    """Decorator to profile method execution time"""

    def decorator(func):
        def wrapper(self, *args, **kwargs):
            start = time.perf_counter()
            result = func(self, *args, **kwargs)
            elapsed = (time.perf_counter() - start) * 1000
            logger.info(f"⏱️ {name} took {elapsed:.0f}ms")
            return result

        return wrapper

    return decorator


# ============================================================
# ANALYTICS SERVICE
# ============================================================


class AnalyticsService:
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self._cache = {}
        self._cached = False

    def _get_cached(self, key: str, compute_func):
        """Get from request cache or compute and store"""
        if key in self._cache:
            return self._cache[key]
        result = compute_func()
        self._cache[key] = result
        self._cached = True
        return result

    def clear_cache(self):
        """Clear request-level cache"""
        self._cache = {}
        self._cached = False
        logger.info("🗑️ Analytics cache cleared")

    # ============================================================
    # 🚀 DASHBOARD - SINGLE OPTIMIZED REQUEST
    # ============================================================

    @profile_method("get_dashboard_data")
    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        🚀 Get all dashboard data in one go.
        Uses cached summary to avoid duplicate queries.
        """
        start = time.perf_counter()

        # Get summary (cached)
        summary = self._get_cached("summary", self._get_summary)

        # Get insights from summary (no DB query)
        insights = self._generate_basic_insights(summary)

        # Get recent transactions (limited)
        recent = self._get_cached(
            "recent", lambda: self._get_recent_transactions(limit=8)
        )

        # Get top counterparties (SQL aggregated)
        counterparties = self._get_cached(
            "counterparties", lambda: self._get_top_counterparties(limit=5)
        )

        # Get spending categories (SQL aggregated)
        categories = self._get_cached("categories", self._get_spending_categories)

        elapsed = (time.perf_counter() - start) * 1000
        logger.info(f"📊 Dashboard data assembled in {elapsed:.0f}ms")

        return {
            "summary": summary,
            "recent_transactions": recent,
            "top_counterparties": counterparties,
            "spending_breakdown": categories,
            "insights": insights,
            "health_score": {
                "score": summary.get("financial_health_score", 0),
                "grade": summary.get("grade", "N/A"),
                "savings_rate": summary.get("savings_rate", 0),
            },
        }

    # ============================================================
    # 📊 SUMMARY - SINGLE OPTIMIZED QUERY WITH TIMING
    # ============================================================

    @profile_method("_get_summary")
    def _get_summary(self) -> Dict:
        """Single optimized query for summary metrics"""
        query_start = time.perf_counter()

        result = self.db.execute(
            select(
                func.coalesce(
                    func.sum(Transaction.amount).filter(
                        Transaction.transaction_type == "received"
                    ),
                    0,
                ).label("money_in"),
                func.coalesce(
                    func.sum(Transaction.amount).filter(
                        Transaction.transaction_type == "sent"
                    ),
                    0,
                ).label("money_out"),
                func.count(Transaction.id).label("total_transactions"),
                func.count(func.distinct(Transaction.counterparty)).label(
                    "unique_counterparties"
                ),
            ).where(Transaction.tenant_id == self.tenant_id)
        )

        row = result.one()
        query_elapsed = (time.perf_counter() - query_start) * 1000
        print(f"⏱️ GET_SUMMARY_SQL={query_elapsed:.2f}ms")
        logger.info(f"⏱️ GET_SUMMARY_SQL={query_elapsed:.2f}ms")

        money_in = float(row.money_in or 0)
        money_out = float(row.money_out or 0)
        net_flow = money_in - money_out
        total_transactions = row.total_transactions or 0
        unique_counterparties = row.unique_counterparties or 0

        health_score = self._calculate_health_score(
            money_in=money_in,
            money_out=money_out,
            net_flow=net_flow,
            transaction_count=total_transactions,
        )

        savings_rate = round(
            ((money_in - money_out) / money_in * 100) if money_in > 0 else 0, 1
        )

        return {
            "money_in": float(money_in),
            "money_out": float(money_out),
            "net_flow": float(net_flow),
            "total_transactions": total_transactions,
            "unique_counterparties": unique_counterparties,
            "financial_health_score": health_score["score"],
            "grade": health_score["grade"],
            "income_consistency": (
                "Strong" if money_in > money_out * 1.2 else "Moderate"
            ),
            "spending_discipline": (
                "Strong" if money_out < money_in * 0.7 else "Moderate"
            ),
            "transaction_stability": (
                "Strong" if total_transactions > 20 else "Building"
            ),
            "savings_rate": savings_rate,
        }

    # ============================================================
    # 📋 RECENT TRANSACTIONS - LIMITED QUERY
    # ============================================================

    @profile_method("_get_recent_transactions")
    def _get_recent_transactions(self, limit: int = 8) -> List[Dict]:
        """Get only recent transactions - no full table scan"""
        query_start = time.perf_counter()

        result = self.db.execute(
            select(Transaction)
            .where(Transaction.tenant_id == self.tenant_id)
            .order_by(desc(Transaction.date))
            .limit(limit)
        )

        transactions = result.scalars().all()
        query_time = (time.perf_counter() - query_start) * 1000
        logger.info(
            f"📊 Recent transactions query took {query_time:.0f}ms for {len(transactions)} rows"
        )

        return [
            {
                "id": str(t.id),
                "date": t.date.isoformat() if t.date else "",
                "amount": float(t.amount),
                "type": (
                    t.transaction_type
                    if t.transaction_type in ["sent", "received"]
                    else "unknown"
                ),
                "counterparty": t.counterparty or "Unknown",
                "description": t.description or "",
                "reference": t.reference or "",
                "balance": float(t.balance) if t.balance else None,
                "time_ago": self._get_time_ago(t.date) if t.date else "",
            }
            for t in transactions
        ]

    # ============================================================
    # 🏆 TOP COUNTERPARTIES - SQL AGGREGATION
    # ============================================================

    @profile_method("_get_top_counterparties")
    def _get_top_counterparties(self, limit: int = 5) -> List[Dict]:
        """
        🚀 Get top counterparties using SQL aggregation.
        No ORM hydration of all transactions.
        """
        query_start = time.perf_counter()

        result = self.db.execute(
            select(
                Transaction.counterparty,
                func.coalesce(
                    func.sum(Transaction.amount).filter(
                        Transaction.transaction_type == "sent"
                    ),
                    0,
                ).label("sent"),
                func.coalesce(
                    func.sum(Transaction.amount).filter(
                        Transaction.transaction_type == "received"
                    ),
                    0,
                ).label("received"),
                func.count(Transaction.id).label("count"),
            )
            .where(
                and_(
                    Transaction.tenant_id == self.tenant_id,
                    Transaction.counterparty.isnot(None),
                    Transaction.counterparty != "Unknown",
                    Transaction.counterparty != "",
                )
            )
            .group_by(Transaction.counterparty)
            .order_by(func.sum(Transaction.amount).desc())
            .limit(limit)
        )

        rows = result.all()
        query_time = (time.perf_counter() - query_start) * 1000
        logger.info(
            f"📊 Top counterparties query took {query_time:.0f}ms for {len(rows)} rows"
        )

        return [
            {
                "name": row.counterparty,
                "totalSent": float(row.sent or 0),
                "totalReceived": float(row.received or 0),
                "count": row.count,
                "type": self._detect_counterparty_type(row.counterparty or ""),
            }
            for row in rows
        ]

    # ============================================================
    # 📊 SPENDING CATEGORIES - SQL AGGREGATION
    # ============================================================

    @profile_method("_get_spending_categories")
    def _get_spending_categories(self) -> List[Dict]:
        """Get spending categories using SQL aggregation"""
        query_start = time.perf_counter()

        result = self.db.execute(
            select(
                Transaction.category,
                func.coalesce(
                    func.sum(Transaction.amount).filter(
                        Transaction.transaction_type == "sent"
                    ),
                    0,
                ).label("total"),
            )
            .where(
                and_(
                    Transaction.tenant_id == self.tenant_id,
                    Transaction.transaction_type == "sent",
                    Transaction.category.isnot(None),
                    Transaction.category != "",
                )
            )
            .group_by(Transaction.category)
            .order_by(func.sum(Transaction.amount).desc())
            .limit(10)
        )

        rows = result.all()
        query_time = (time.perf_counter() - query_start) * 1000
        logger.info(f"📊 Spending categories query took {query_time:.0f}ms")

        total_spent = sum(float(row.total or 0) for row in rows) if rows else 0

        return [
            {
                "name": row.category or "Uncategorized",
                "amount": float(row.total or 0),
                "percentage": round(
                    (
                        (float(row.total or 0) / total_spent * 100)
                        if total_spent > 0
                        else 0
                    ),
                    1,
                ),
            }
            for row in rows
        ]

    # ============================================================
    # 👥 PEOPLE & BUSINESSES - PURE SQL AGGREGATION
    # ============================================================

    @profile_method("get_people_businesses")
    def get_people_businesses(self) -> Dict[str, Any]:
        """
        🚀 Get people and businesses using pure SQL aggregation.
        All aggregation done in PostgreSQL - NO Python loops.
        """
        query_start = time.perf_counter()

        # ✅ PostgreSQL does all the aggregation work
        result = self.db.execute(
            select(
                Transaction.counterparty,
                func.coalesce(
                    func.sum(Transaction.amount).filter(
                        Transaction.transaction_type == "sent"
                    ),
                    0,
                ).label("sent"),
                func.coalesce(
                    func.sum(Transaction.amount).filter(
                        Transaction.transaction_type == "received"
                    ),
                    0,
                ).label("received"),
                func.count(Transaction.id).label("count"),
                func.min(Transaction.date).label("first_seen"),
                func.max(Transaction.date).label("last_seen"),
            )
            .where(
                and_(
                    Transaction.tenant_id == self.tenant_id,
                    Transaction.counterparty.isnot(None),
                    Transaction.counterparty != "",
                    Transaction.counterparty != "Unknown",
                    Transaction.counterparty != "N/A",
                )
            )
            .group_by(Transaction.counterparty)
            .order_by(
                (
                    func.coalesce(
                        func.sum(Transaction.amount).filter(
                            Transaction.transaction_type == "sent"
                        ),
                        0,
                    )
                    + func.coalesce(
                        func.sum(Transaction.amount).filter(
                            Transaction.transaction_type == "received"
                        ),
                        0,
                    )
                ).desc()
            )
            .limit(20)
        )

        rows = result.all()
        query_time = (time.perf_counter() - query_start) * 1000
        logger.info(
            f"📊 People-businesses SQL query took {query_time:.0f}ms for {len(rows)} rows"
        )

        # ✅ Get total count - single scalar query
        total_start = time.perf_counter()
        total_count = (
            self.db.execute(
                select(func.count(Transaction.id)).where(
                    Transaction.tenant_id == self.tenant_id
                )
            ).scalar()
            or 0
        )
        total_time = (time.perf_counter() - total_start) * 1000
        logger.info(f"📊 Total count query took {total_time:.0f}ms")

        # ✅ Serialize results (minimal Python work)
        serialize_start = time.perf_counter()
        counterparties = [
            {
                "name": row.counterparty,
                "totalSent": float(row.sent or 0),
                "totalReceived": float(row.received or 0),
                "count": row.count,
                "firstSeen": row.first_seen.isoformat() if row.first_seen else None,
                "lastSeen": row.last_seen.isoformat() if row.last_seen else None,
                "type": self._detect_counterparty_type(row.counterparty or ""),
            }
            for row in rows
        ]
        serialize_time = (time.perf_counter() - serialize_start) * 1000
        logger.info(f"📊 Serialization took {serialize_time:.0f}ms")

        return {
            "counterparties": counterparties,
            "total_counterparties": len(rows),
            "total_transactions": total_count,
        }

    # ============================================================
    # 💡 INSIGHTS - NO EXTRA QUERIES
    # ============================================================

    @profile_method("get_insights")
    def get_insights(self) -> List[Dict]:
        """
        🚀 Get insights using cached summary data.
        No database queries - uses data from dashboard.
        """
        summary = self._get_cached("summary", self._get_summary)
        return self._generate_basic_insights(summary)

    @profile_method("_generate_basic_insights")
    def _generate_basic_insights(self, summary: Dict) -> List[Dict]:
        """Generate insights from summary data (no database queries)"""
        insights = []
        start = time.perf_counter()

        # Cash flow insight
        if summary["total_transactions"] == 0:
            insights.append(
                {
                    "type": "opportunity",
                    "title": "Upload your first statement",
                    "description": "Upload an M-PESA statement to see personalized financial insights.",
                    "confidence": 78,
                    "actionLabel": "Upload Now",
                }
            )
        else:
            net_flow = summary.get("net_flow", 0)
            money_in = summary.get("money_in", 0)

            if abs(net_flow) < 50000:
                insights.append(
                    {
                        "type": "insight",
                        "title": "Near Breakeven Operation",
                        "description": f"Your finances operated within {abs(net_flow / max(money_in, 1) * 100):.1f}% of breakeven.",
                        "confidence": 96,
                        "impact": "Small efficiency improvements could move you into positive territory.",
                        "actionLabel": "Analyze Efficiency",
                    }
                )
            elif net_flow < 0:
                insights.append(
                    {
                        "type": "warning",
                        "title": "Cash Flow Deficit",
                        "description": f"Outflows exceed inflows by KES {abs(net_flow):,.0f}.",
                        "confidence": 94,
                        "impact": "Review your top spending categories for potential savings.",
                        "actionLabel": "Review Spending",
                    }
                )
            else:
                insights.append(
                    {
                        "type": "positive",
                        "title": "Positive Cash Flow",
                        "description": f"You have a surplus of KES {net_flow:,.0f}.",
                        "confidence": 94,
                        "impact": "This provides room for savings or investment.",
                        "actionLabel": "Create Savings Plan",
                    }
                )

            # Transaction volume insight
            total_transactions = summary.get("total_transactions", 0)
            if total_transactions > 100:
                insights.append(
                    {
                        "type": "positive",
                        "title": f"High transaction volume: {total_transactions:,} transactions",
                        "description": f"You average {total_transactions // 12:,} transactions per month.",
                        "confidence": 92,
                        "impact": "Your activity level is in the top tier of users.",
                        "actionLabel": "View Activity",
                    }
                )

            # Network size insight
            unique_counterparties = summary.get("unique_counterparties", 0)
            if unique_counterparties > 10:
                insights.append(
                    {
                        "type": "positive",
                        "title": f"Financial network with {unique_counterparties} entities",
                        "description": f"You've transacted with {unique_counterparties} different people, businesses, and utilities.",
                        "confidence": 90,
                        "impact": "Building a diverse financial network improves resilience.",
                        "actionLabel": "View Network",
                    }
                )

        elapsed = (time.perf_counter() - start) * 1000
        logger.info(f"📊 Generated {len(insights)} insights in {elapsed:.0f}ms")
        return insights

    # ============================================================
    # 🏥 HEALTH SCORE
    # ============================================================

    def _calculate_health_score(self, **kwargs) -> Dict:
        """Calculate financial health score"""
        score = 70

        if kwargs["net_flow"] > 0:
            score += min(20, (kwargs["net_flow"] / 10000) * 5)
        if kwargs["transaction_count"] > 100:
            score += 10
        if kwargs["money_in"] > kwargs["money_out"] * 1.2:
            score += 10
        if kwargs["net_flow"] < 0:
            score -= min(20, (abs(kwargs["net_flow"]) / 10000) * 5)

        score = max(0, min(100, score))

        grade = "Poor"
        if score >= 80:
            grade = "Excellent"
        elif score >= 65:
            grade = "Good"
        elif score >= 50:
            grade = "Fair"

        return {"score": round(score), "grade": grade}

    # ============================================================
    # 🔧 UTILITY METHODS
    # ============================================================

    @staticmethod
    def _get_time_ago(date: datetime) -> str:
        if not date:
            return "Unknown"
        diff = datetime.now() - date
        if diff.days > 0:
            return f"{diff.days} days ago"
        if diff.seconds > 3600:
            return f"{diff.seconds // 3600} hours ago"
        if diff.seconds > 60:
            return f"{diff.seconds // 60} minutes ago"
        return "Just now"

    @staticmethod
    def _detect_counterparty_type(name: str) -> str:
        if not name:
            return "unknown"

        business_keywords = [
            "Ltd",
            "Limited",
            "Shop",
            "Mart",
            "Supermarket",
            "Restaurant",
            "Cafe",
            "Store",
            "Mall",
            "Hotel",
        ]
        utility_keywords = [
            "Safaricom",
            "KPLC",
            "Water",
            "Internet",
            "Kenya Power",
            "Airtel",
        ]

        name_lower = name.lower()
        if any(k.lower() in name_lower for k in utility_keywords):
            return "utility"
        if any(k.lower() in name_lower for k in business_keywords):
            return "business"
        if re.match(r"^07\d{8}$", name) or re.match(r"^\+254\d{9}$", name):
            return "person"
        if re.match(r"^01\d{8}$", name):
            return "person"
        return "unknown"

    # ============================================================
    # 🎯 GET HEALTH SCORE (Public Method)
    # ============================================================

    def _get_health_score(self) -> Dict:
        """Get financial health score with breakdown"""
        summary = self._get_summary()
        return {
            "score": summary.get("financial_health_score", 0),
            "grade": summary.get("grade", "N/A"),
            "factors": [
                {"name": "Cash Flow", "value": summary.get("net_flow", 0)},
                {
                    "name": "Transaction Volume",
                    "value": summary.get("total_transactions", 0),
                },
                {"name": "Savings Rate", "value": summary.get("savings_rate", 0)},
            ],
        }
