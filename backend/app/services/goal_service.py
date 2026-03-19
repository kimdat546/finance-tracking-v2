"""Goal service - business logic for financial goal tracking."""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.planning import Goal, GoalStatus
from app.schemas.planning import GoalCreateRequest, GoalUpdateRequest


class GoalService:
    """Service for managing financial goals and tracking progress."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialise the service with a database session.

        Args:
            session: The async SQLAlchemy session to use for all queries.
        """
        self.session = session

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _compute_percentage(self, goal: Goal) -> float:
        """Compute percentage of goal completion.

        Args:
            goal: The Goal model instance.

        Returns:
            Float between 0.0 and 100.0 (capped at 100).
        """
        if goal.target_amount <= 0:
            return 0.0
        pct = float(goal.current_amount / goal.target_amount * 100)
        return round(min(pct, 100.0), 2)

    def _to_schema_dict(self, goal: Goal) -> dict:
        """Convert a Goal ORM instance to a dict matching GoalSchema.

        Args:
            goal: The Goal model instance.

        Returns:
            Dict suitable for constructing GoalSchema.
        """
        return {
            "id": goal.id,
            "name": goal.name,
            "description": goal.description,
            "target_amount": goal.target_amount,
            "current_amount": goal.current_amount,
            "percentage_complete": self._compute_percentage(goal),
            "start_date": goal.start_date,
            "target_date": goal.target_date,
            "currency": goal.currency,
            "status": goal.status.value if hasattr(goal.status, "value") else goal.status,
            "priority": goal.priority,
            "icon": goal.icon,
            "color": goal.color,
            "is_active": goal.status == GoalStatus.ACTIVE,
        }

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    async def create_goal(self, user_id: str, data: GoalCreateRequest) -> Goal:
        """Create a new financial goal.

        Args:
            user_id: The authenticated user's ID.
            data: Validated goal creation data.

        Returns:
            The newly created Goal instance.
        """
        goal = Goal(
            user_id=user_id,
            name=data.name,
            description=data.description,
            target_amount=data.target_amount,
            current_amount=Decimal("0"),
            currency=data.currency,
            start_date=data.start_date,
            target_date=data.target_date,
            status=GoalStatus.ACTIVE,
            priority=data.priority,
            icon=data.icon,
            color=data.color,
        )
        self.session.add(goal)
        await self.session.commit()
        await self.session.refresh(goal)
        return goal

    async def get_goals(self, user_id: str, active_only: bool = True) -> list[Goal]:
        """Retrieve all goals for a user.

        Args:
            user_id: The authenticated user's ID.
            active_only: When True, only return goals with status ACTIVE.

        Returns:
            List of Goal instances.
        """
        query = select(Goal).where(Goal.user_id == user_id)
        if active_only:
            query = query.where(Goal.status == GoalStatus.ACTIVE)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_goal(self, goal_id: str, user_id: str) -> Goal | None:
        """Fetch a single goal by ID.

        Args:
            goal_id: The goal's UUID.
            user_id: The authenticated user's ID.

        Returns:
            The Goal instance or None if not found.
        """
        result = await self.session.execute(
            select(Goal).where(Goal.id == goal_id, Goal.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def update_goal(
        self, goal_id: str, user_id: str, data: GoalUpdateRequest
    ) -> Goal | None:
        """Update an existing goal.

        Args:
            goal_id: The goal's UUID.
            user_id: The authenticated user's ID.
            data: Fields to update (only non-None values are applied).

        Returns:
            Updated Goal instance, or None if not found.
        """
        goal = await self.get_goal(goal_id, user_id)
        if goal is None:
            return None

        if data.name is not None:
            goal.name = data.name
        if data.description is not None:
            goal.description = data.description
        if data.target_amount is not None:
            goal.target_amount = data.target_amount
        if data.start_date is not None:
            goal.start_date = data.start_date
        if data.target_date is not None:
            goal.target_date = data.target_date
        if data.currency is not None:
            goal.currency = data.currency
        if data.priority is not None:
            goal.priority = data.priority
        if data.icon is not None:
            goal.icon = data.icon
        if data.color is not None:
            goal.color = data.color
        if data.status is not None:
            goal.status = GoalStatus(data.status)

        await self.session.commit()
        await self.session.refresh(goal)
        return goal

    async def add_contribution(
        self, goal_id: str, amount: float, user_id: str
    ) -> Goal | None:
        """Add a monetary contribution to a goal's current_amount.

        If the contribution brings the goal to or above target_amount,
        the goal status is updated to COMPLETED.

        Args:
            goal_id: The goal's UUID.
            amount: The contribution amount (must be positive).
            user_id: The authenticated user's ID.

        Returns:
            Updated Goal instance, or None if not found.

        Raises:
            ValueError: If the amount is not positive.
        """
        if amount <= 0:
            raise ValueError("Contribution amount must be positive.")

        goal = await self.get_goal(goal_id, user_id)
        if goal is None:
            return None

        goal.current_amount = goal.current_amount + Decimal(str(amount))

        # Auto-complete goal when target is reached
        if goal.current_amount >= goal.target_amount:
            goal.status = GoalStatus.COMPLETED

        await self.session.commit()
        await self.session.refresh(goal)
        return goal

    async def delete_goal(self, goal_id: str, user_id: str) -> bool:
        """Delete a goal permanently.

        Args:
            goal_id: The goal's UUID.
            user_id: The authenticated user's ID.

        Returns:
            True if the goal was found and deleted, False otherwise.
        """
        goal = await self.get_goal(goal_id, user_id)
        if goal is None:
            return False
        await self.session.delete(goal)
        await self.session.commit()
        return True

    async def get_goals_summary(self, user_id: str) -> dict:
        """Return aggregate statistics for all goals belonging to a user.

        Args:
            user_id: The authenticated user's ID.

        Returns:
            Dict with total_goals, total_target, total_saved, completion_percentage.
        """
        result = await self.session.execute(
            select(Goal).where(Goal.user_id == user_id)
        )
        goals = list(result.scalars().all())

        total_goals = len(goals)
        active_goals = sum(1 for g in goals if g.status == GoalStatus.ACTIVE)
        completed_goals = sum(1 for g in goals if g.status == GoalStatus.COMPLETED)
        total_target = sum(float(g.target_amount) for g in goals if g.target_amount)
        total_saved = sum(float(g.current_amount) for g in goals if g.current_amount)

        completion_pct = (
            round(total_saved / total_target * 100, 2) if total_target > 0 else 0.0
        )

        return {
            "total_goals": total_goals,
            "active_goals": active_goals,
            "completed_goals": completed_goals,
            "total_target": total_target,
            "total_saved": total_saved,
            "completion_percentage": completion_pct,
        }
