"""Email digest service - generates weekly spending summary data and formatted emails."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.planning import Budget, Subscription
from app.models.transaction import Category, Transaction, TransactionType


class EmailDigestService:
    """Generates weekly spending summaries for email digests."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialise the service with a database session.

        Args:
            session: The async SQLAlchemy session to use for all queries.
        """
        self.session = session

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _sum_expense(self, user_id: str, start: str, end: str) -> Decimal:
        """Sum expense transactions for a date range.

        Args:
            user_id: The user's ID.
            start: Start date string (YYYY-MM-DD).
            end: End date string (YYYY-MM-DD).

        Returns:
            Total expenses as Decimal.
        """
        result = await self.session.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.user_id == user_id,
                Transaction.type == TransactionType.EXPENSE,
                Transaction.transaction_date >= start,
                Transaction.transaction_date <= end,
            )
        )
        val = result.scalar_one_or_none()
        return Decimal(str(val)) if val is not None else Decimal("0")

    async def _top_categories(self, user_id: str, start: str, end: str) -> list[dict]:
        """Get top expense categories for the given date range.

        Args:
            user_id: The user's ID.
            start: Start date string.
            end: End date string.

        Returns:
            List of dicts with name, amount, count (top 5).
        """
        result = await self.session.execute(
            select(
                Category.name,
                func.sum(Transaction.amount).label("total"),
                func.count(Transaction.id).label("cnt"),
            )
            .join(Transaction, Transaction.category_id == Category.id)
            .where(
                Transaction.user_id == user_id,
                Transaction.type == TransactionType.EXPENSE,
                Transaction.transaction_date >= start,
                Transaction.transaction_date <= end,
                Transaction.category_id.isnot(None),
            )
            .group_by(Category.id, Category.name)
            .order_by(func.sum(Transaction.amount).desc())
            .limit(5)
        )
        return [
            {"name": r.name, "amount": float(r.total), "count": r.cnt}
            for r in result.all()
        ]

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    async def generate_weekly_digest(
        self, user_id: str, week_start: datetime
    ) -> dict:
        """Generate weekly digest data.

        Args:
            user_id: The authenticated user's ID.
            week_start: The Monday of the week to generate the digest for.

        Returns:
            Dict with period, total_spent, vs_last_week, top_categories,
            biggest_transaction, budget_warnings, upcoming_subscriptions.
        """
        week_end = week_start + timedelta(days=6)
        prev_week_start = week_start - timedelta(days=7)
        prev_week_end = week_start - timedelta(days=1)

        start_str = week_start.strftime("%Y-%m-%d")
        end_str = week_end.strftime("%Y-%m-%d")
        prev_start_str = prev_week_start.strftime("%Y-%m-%d")
        prev_end_str = prev_week_end.strftime("%Y-%m-%d")

        total_spent = await self._sum_expense(user_id, start_str, end_str)
        prev_spent = await self._sum_expense(user_id, prev_start_str, prev_end_str)

        if prev_spent > 0:
            vs_last_week = float((total_spent - prev_spent) / prev_spent * 100)
        else:
            vs_last_week = 0.0

        top_categories = await self._top_categories(user_id, start_str, end_str)

        # Biggest transaction this week
        big_result = await self.session.execute(
            select(Transaction)
            .where(
                Transaction.user_id == user_id,
                Transaction.type == TransactionType.EXPENSE,
                Transaction.transaction_date >= start_str,
                Transaction.transaction_date <= end_str,
            )
            .order_by(Transaction.amount.desc())
            .limit(1)
        )
        biggest_tx = big_result.scalar_one_or_none()
        biggest_transaction = (
            {
                "id": biggest_tx.id,
                "amount": float(biggest_tx.amount),
                "description": biggest_tx.description,
                "merchant": biggest_tx.merchant,
                "transaction_date": biggest_tx.transaction_date,
            }
            if biggest_tx
            else None
        )

        # Budget warnings for the current month
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1).strftime("%Y-%m-%d")
        month_end = end_str  # Up to end of this week

        budgets_result = await self.session.execute(
            select(Budget)
            .where(Budget.user_id == user_id, Budget.is_active.is_(True))
        )
        budgets = budgets_result.scalars().all()
        budget_warnings: list[dict] = []
        for budget in budgets:
            spent_result = await self.session.execute(
                select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                    Transaction.user_id == user_id,
                    Transaction.category_id == budget.category_id,
                    Transaction.type == TransactionType.EXPENSE,
                    Transaction.transaction_date >= month_start,
                    Transaction.transaction_date <= month_end,
                )
            )
            spent_val = spent_result.scalar_one_or_none()
            spent = Decimal(str(spent_val)) if spent_val is not None else Decimal("0")
            limit = Decimal(str(budget.limit_amount))
            pct = float(spent / limit * 100) if limit > 0 else 0.0
            if pct >= 80:
                budget_warnings.append(
                    {
                        "name": budget.name,
                        "limit": float(limit),
                        "spent": float(spent),
                        "percentage": round(pct, 1),
                    }
                )

        # Upcoming subscriptions in next 7 days
        today_str = now.strftime("%Y-%m-%d")
        next_week_str = (now + timedelta(days=7)).strftime("%Y-%m-%d")
        subs_result = await self.session.execute(
            select(Subscription)
            .where(
                Subscription.user_id == user_id,
                Subscription.is_active.is_(True),
                Subscription.next_billing_date >= today_str,
                Subscription.next_billing_date <= next_week_str,
            )
            .order_by(Subscription.next_billing_date)
        )
        upcoming_subs = subs_result.scalars().all()
        upcoming_subscriptions = [
            {
                "name": s.name,
                "amount": float(s.amount),
                "next_billing_date": s.next_billing_date,
                "currency": s.currency,
            }
            for s in upcoming_subs
        ]

        return {
            "period": f"{start_str} đến {end_str}",
            "total_spent": float(total_spent),
            "vs_last_week": round(vs_last_week, 2),
            "top_categories": top_categories,
            "biggest_transaction": biggest_transaction,
            "budget_warnings": budget_warnings,
            "upcoming_subscriptions": upcoming_subscriptions,
        }

    async def format_digest_html(self, digest_data: dict) -> str:
        """Format digest as HTML email body.

        Args:
            digest_data: The digest dict returned by generate_weekly_digest.

        Returns:
            HTML string suitable for an email body.
        """
        period = digest_data.get("period", "")
        total_spent = digest_data.get("total_spent", 0)
        vs_last_week = digest_data.get("vs_last_week", 0)
        top_cats = digest_data.get("top_categories", [])
        biggest = digest_data.get("biggest_transaction")
        budget_warnings = digest_data.get("budget_warnings", [])
        upcoming = digest_data.get("upcoming_subscriptions", [])

        change_sign = "+" if vs_last_week >= 0 else ""
        change_color = "#e53e3e" if vs_last_week > 0 else "#38a169"

        cat_rows = "".join(
            f"<tr><td style='padding:6px 12px;'>{c['name']}</td>"
            f"<td style='padding:6px 12px; text-align:right;'>"
            f"{c['amount']:,.0f} ₫</td></tr>"
            for c in top_cats
        )

        budget_rows = "".join(
            f"<tr><td style='padding:6px 12px;'>{b['name']}</td>"
            f"<td style='padding:6px 12px; text-align:right;'>{b['percentage']}%</td></tr>"
            for b in budget_warnings
        )

        sub_rows = "".join(
            f"<tr><td style='padding:6px 12px;'>{s['name']}</td>"
            f"<td style='padding:6px 12px; text-align:right;'>"
            f"{s['amount']:,.0f} ₫</td>"
            f"<td style='padding:6px 12px;'>{s['next_billing_date']}</td></tr>"
            for s in upcoming
        )

        biggest_section = ""
        if biggest:
            biggest_section = f"""
            <h3 style='color:#2d3748;'>Giao Dịch Lớn Nhất</h3>
            <p>{biggest.get('description', '')} - <strong>{biggest.get('amount', 0):,.0f} ₫</strong>
            ({biggest.get('transaction_date', '')})</p>
            """

        return f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset='utf-8'></head>
        <body style='font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;
                     background: #f7fafc; padding: 20px;'>
          <div style='background: white; border-radius: 8px; padding: 24px;'>
            <h1 style='color:#2b6cb0;'>Tóm Tắt Chi Tiêu Tuần</h1>
            <p style='color:#718096;'>{period}</p>
            <hr style='border-color:#e2e8f0;'>
            <h2 style='font-size:2em; color:#2d3748;'>{total_spent:,.0f} ₫</h2>
            <p style='color:{change_color};'>
              {change_sign}{vs_last_week:.1f}% so với tuần trước
            </p>
            <h3 style='color:#2d3748;'>Top Danh Mục Chi Tiêu</h3>
            <table style='width:100%; border-collapse:collapse;
                          border:1px solid #e2e8f0;'>
              <tr style='background:#edf2f7;'>
                <th style='padding:8px 12px; text-align:left;'>Danh mục</th>
                <th style='padding:8px 12px; text-align:right;'>Số tiền</th>
              </tr>
              {cat_rows}
            </table>
            {biggest_section}
            {"<h3 style='color:#c53030;'>Cảnh Báo Ngân Sách</h3><table style='width:100%;border-collapse:collapse;border:1px solid #e2e8f0;'><tr style='background:#fff5f5;'><th style='padding:8px 12px; text-align:left;'>Ngân sách</th><th style='padding:8px 12px; text-align:right;'>Đã dùng</th></tr>" + budget_rows + "</table>" if budget_warnings else ""}
            {"<h3 style='color:#2d3748;'>Sắp Gia Hạn</h3><table style='width:100%;border-collapse:collapse;border:1px solid #e2e8f0;'><tr style='background:#edf2f7;'><th style='padding:8px 12px; text-align:left;'>Dịch vụ</th><th style='padding:8px 12px; text-align:right;'>Số tiền</th><th style='padding:8px 12px;'>Ngày</th></tr>" + sub_rows + "</table>" if upcoming else ""}
            <hr style='border-color:#e2e8f0; margin-top:24px;'>
            <p style='color:#a0aec0; font-size:12px;'>
              Được tạo tự động bởi Hệ Thống Quản Lý Tài Chính Cá Nhân.
            </p>
          </div>
        </body>
        </html>
        """

    async def format_digest_text(self, digest_data: dict) -> str:
        """Format digest as plain text.

        Args:
            digest_data: The digest dict returned by generate_weekly_digest.

        Returns:
            Plain text string suitable for a text/plain email part.
        """
        period = digest_data.get("period", "")
        total_spent = digest_data.get("total_spent", 0)
        vs_last_week = digest_data.get("vs_last_week", 0)
        top_cats = digest_data.get("top_categories", [])
        biggest = digest_data.get("biggest_transaction")
        budget_warnings = digest_data.get("budget_warnings", [])
        upcoming = digest_data.get("upcoming_subscriptions", [])

        sign = "+" if vs_last_week >= 0 else ""
        lines = [
            "TÓM TẮT CHI TIÊU TUẦN",
            "=" * 40,
            f"Kỳ: {period}",
            f"Tổng chi tiêu: {total_spent:,.0f} đ",
            f"So với tuần trước: {sign}{vs_last_week:.1f}%",
            "",
            "TOP DANH MỤC CHI TIÊU:",
        ]
        for cat in top_cats:
            lines.append(f"  - {cat['name']}: {cat['amount']:,.0f} đ ({cat['count']} giao dịch)")

        if biggest:
            lines += [
                "",
                "GIAO DỊCH LỚN NHẤT:",
                f"  {biggest.get('description', '')} - {biggest.get('amount', 0):,.0f} đ",
                f"  Ngày: {biggest.get('transaction_date', '')}",
            ]

        if budget_warnings:
            lines += ["", "CẢNH BÁO NGÂN SÁCH:"]
            for b in budget_warnings:
                lines.append(f"  - {b['name']}: đã dùng {b['percentage']}%")

        if upcoming:
            lines += ["", "SẮP GIA HẠN:"]
            for s in upcoming:
                lines.append(
                    f"  - {s['name']}: {s['amount']:,.0f} đ (ngày {s['next_billing_date']})"
                )

        lines += ["", "-" * 40, "Hệ Thống Quản Lý Tài Chính Cá Nhân"]
        return "\n".join(lines)
