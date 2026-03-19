"""Planning schemas: Budget, Goal, Debt, Subscription."""

from decimal import Decimal

from pydantic import BaseModel, Field, computed_field, model_validator

from app.models.planning import BudgetPeriod


# ---------------------------------------------------------------------------
# Budget schemas
# ---------------------------------------------------------------------------


class BudgetCreateRequest(BaseModel):
    """Request body for creating a budget."""

    category_id: str = Field(description="Category ID for this budget")
    name: str = Field(description="Budget name")
    amount: Decimal = Field(gt=0, decimal_places=2, description="Budget limit amount")
    period: BudgetPeriod = Field(default=BudgetPeriod.MONTHLY, description="Budget period")
    start_date: str = Field(description="Start date (YYYY-MM-DD)")
    end_date: str | None = Field(default=None, description="End date (YYYY-MM-DD), optional")
    currency: str = Field(default="VND", description="Currency code")
    alert_threshold: int = Field(default=80, ge=1, le=100, description="Alert threshold percent")


class BudgetUpdateRequest(BaseModel):
    """Request body for updating a budget (all fields optional)."""

    category_id: str | None = Field(default=None, description="Category ID")
    name: str | None = Field(default=None, description="Budget name")
    amount: Decimal | None = Field(default=None, gt=0, decimal_places=2, description="Budget limit")
    period: BudgetPeriod | None = Field(default=None, description="Budget period")
    start_date: str | None = Field(default=None, description="Start date")
    end_date: str | None = Field(default=None, description="End date")
    currency: str | None = Field(default=None, description="Currency code")
    alert_threshold: int | None = Field(default=None, ge=1, le=100, description="Alert threshold %")
    is_active: bool | None = Field(default=None, description="Is budget active")


class BudgetSchema(BaseModel):
    """Budget response schema with computed spending fields."""

    id: str = Field(description="Budget ID")
    category_id: str = Field(description="Category ID")
    category_name: str | None = Field(default=None, description="Category name (if loaded)")
    name: str = Field(description="Budget name")
    amount: Decimal = Field(description="Budget limit amount")
    period: BudgetPeriod = Field(description="Budget period")
    currency: str = Field(description="Currency code")
    spent_amount: Decimal = Field(default=Decimal("0"), description="Amount spent so far")
    remaining: Decimal = Field(default=Decimal("0"), description="Remaining budget")
    percentage_used: float = Field(default=0.0, description="Percentage of budget used")
    start_date: str = Field(description="Start date")
    end_date: str | None = Field(default=None, description="End date")
    is_active: bool = Field(description="Is budget active")
    alert_threshold: int = Field(description="Alert threshold %")

    model_config = {"from_attributes": True}


class BudgetListResponse(BaseModel):
    """Paginated budget list response."""

    items: list[BudgetSchema] = Field(description="Budget items")
    total: int = Field(description="Total count")


# ---------------------------------------------------------------------------
# Goal schemas
# ---------------------------------------------------------------------------


class GoalCreateRequest(BaseModel):
    """Request body for creating a goal."""

    name: str = Field(description="Goal name")
    description: str | None = Field(default=None, description="Goal description")
    target_amount: Decimal = Field(gt=0, decimal_places=2, description="Target amount")
    start_date: str = Field(description="Goal start date (YYYY-MM-DD)")
    target_date: str = Field(description="Target date (YYYY-MM-DD)")
    currency: str = Field(default="VND", description="Currency code")
    priority: int = Field(default=0, ge=0, description="Priority (higher = more important)")
    icon: str | None = Field(default=None, description="Icon identifier")
    color: str | None = Field(default=None, description="Color hex code")


class GoalUpdateRequest(BaseModel):
    """Request body for updating a goal (all fields optional)."""

    name: str | None = Field(default=None, description="Goal name")
    description: str | None = Field(default=None, description="Goal description")
    target_amount: Decimal | None = Field(default=None, gt=0, description="Target amount")
    start_date: str | None = Field(default=None, description="Start date")
    target_date: str | None = Field(default=None, description="Target date")
    currency: str | None = Field(default=None, description="Currency code")
    priority: int | None = Field(default=None, ge=0, description="Priority")
    icon: str | None = Field(default=None, description="Icon identifier")
    color: str | None = Field(default=None, description="Color hex code")
    status: str | None = Field(default=None, description="Goal status")


class GoalSchema(BaseModel):
    """Goal response schema with computed progress fields."""

    id: str = Field(description="Goal ID")
    name: str = Field(description="Goal name")
    description: str | None = Field(default=None, description="Goal description")
    target_amount: Decimal = Field(description="Target amount")
    current_amount: Decimal = Field(description="Current saved amount")
    percentage_complete: float = Field(description="Completion percentage")
    start_date: str = Field(description="Start date")
    target_date: str = Field(description="Target date")
    currency: str = Field(description="Currency code")
    status: str = Field(description="Goal status")
    priority: int = Field(description="Priority")
    icon: str | None = Field(default=None, description="Icon")
    color: str | None = Field(default=None, description="Color")
    is_active: bool = Field(description="Is goal active (status == active)")

    model_config = {"from_attributes": True}


class GoalListResponse(BaseModel):
    """Paginated goal list response."""

    items: list[GoalSchema] = Field(description="Goal items")
    total: int = Field(description="Total count")


# ---------------------------------------------------------------------------
# Debt schemas
# ---------------------------------------------------------------------------


class DebtCreateRequest(BaseModel):
    """Request body for creating a debt record."""

    name: str = Field(description="Debt name / label")
    creditor: str = Field(description="Creditor name (who you owe) or debtor name (who owes you)")
    description: str | None = Field(default=None, description="Additional notes")
    amount: Decimal = Field(gt=0, decimal_places=2, description="Original debt amount")
    currency: str = Field(default="VND", description="Currency code")
    interest_rate: Decimal | None = Field(default=None, ge=0, description="Annual interest rate %")
    monthly_payment: Decimal | None = Field(default=None, ge=0, description="Monthly payment amount")
    start_date: str = Field(description="Debt start date (YYYY-MM-DD)")
    due_date: str | None = Field(default=None, description="Due/payoff date")
    debt_type: str = Field(default="owe", description="'owe' (you owe) or 'owed' (owed to you)")

    @model_validator(mode="after")
    def validate_debt_type(self) -> "DebtCreateRequest":
        """Validate that debt_type is either 'owe' or 'owed'."""
        if self.debt_type not in ("owe", "owed"):
            raise ValueError("debt_type must be 'owe' or 'owed'")
        return self


class DebtUpdateRequest(BaseModel):
    """Request body for updating a debt (all fields optional)."""

    name: str | None = Field(default=None, description="Debt name")
    creditor: str | None = Field(default=None, description="Creditor/debtor name")
    description: str | None = Field(default=None, description="Description")
    interest_rate: Decimal | None = Field(default=None, ge=0, description="Interest rate %")
    monthly_payment: Decimal | None = Field(default=None, ge=0, description="Monthly payment")
    due_date: str | None = Field(default=None, description="Due date")
    status: str | None = Field(default=None, description="Debt status")


class DebtSchema(BaseModel):
    """Debt response schema with computed fields."""

    id: str = Field(description="Debt ID")
    name: str = Field(description="Debt name")
    creditor: str = Field(description="Creditor/debtor name")
    description: str | None = Field(default=None, description="Description")
    amount: Decimal = Field(description="Original debt amount")
    paid_amount: Decimal = Field(description="Amount already paid")
    remaining_amount: Decimal = Field(description="Remaining balance")
    currency: str = Field(description="Currency code")
    interest_rate: Decimal | None = Field(default=None, description="Annual interest rate %")
    monthly_payment: Decimal | None = Field(default=None, description="Monthly payment")
    start_date: str = Field(description="Start date")
    due_date: str | None = Field(default=None, description="Due date")
    paid_off_date: str | None = Field(default=None, description="Paid off date")
    debt_type: str = Field(description="'owe' or 'owed'")
    status: str = Field(description="Debt status")
    is_active: bool = Field(description="Is debt still active")

    model_config = {"from_attributes": True}


class DebtListResponse(BaseModel):
    """Paginated debt list response."""

    items: list[DebtSchema] = Field(description="Debt items")
    total: int = Field(description="Total count")


class DebtPaymentRequest(BaseModel):
    """Request body for recording a debt payment."""

    amount: Decimal = Field(gt=0, decimal_places=2, description="Payment amount")
    payment_date: str = Field(description="Payment date (YYYY-MM-DD)")
    notes: str | None = Field(default=None, description="Payment notes")


# ---------------------------------------------------------------------------
# Subscription schemas
# ---------------------------------------------------------------------------


class SubscriptionCreateRequest(BaseModel):
    """Request body for creating a subscription."""

    name: str = Field(description="Subscription name")
    description: str | None = Field(default=None, description="Description")
    amount: Decimal = Field(gt=0, decimal_places=2, description="Billing amount per cycle")
    currency: str = Field(default="VND", description="Currency code")
    billing_cycle: BudgetPeriod = Field(
        default=BudgetPeriod.MONTHLY, description="Billing cycle period"
    )
    start_date: str = Field(description="Subscription start date (YYYY-MM-DD)")
    next_billing_date: str = Field(description="Next billing date (YYYY-MM-DD)")
    end_date: str | None = Field(default=None, description="Subscription end date")
    category_id: str | None = Field(default=None, description="Category ID")
    url: str | None = Field(default=None, description="Subscription URL")
    is_auto_renew: bool = Field(default=True, description="Auto-renew flag")


class SubscriptionUpdateRequest(BaseModel):
    """Request body for updating a subscription (all fields optional)."""

    name: str | None = Field(default=None, description="Subscription name")
    description: str | None = Field(default=None, description="Description")
    amount: Decimal | None = Field(default=None, gt=0, description="Billing amount")
    currency: str | None = Field(default=None, description="Currency")
    billing_cycle: BudgetPeriod | None = Field(default=None, description="Billing cycle")
    next_billing_date: str | None = Field(default=None, description="Next billing date")
    end_date: str | None = Field(default=None, description="End date")
    category_id: str | None = Field(default=None, description="Category ID")
    is_active: bool | None = Field(default=None, description="Is subscription active")
    is_auto_renew: bool | None = Field(default=None, description="Auto-renew")


class SubscriptionSchema(BaseModel):
    """Subscription response schema with computed fields."""

    id: str = Field(description="Subscription ID")
    name: str = Field(description="Subscription name")
    description: str | None = Field(default=None, description="Description")
    amount: Decimal = Field(description="Billing amount per cycle")
    currency: str = Field(description="Currency code")
    billing_cycle: BudgetPeriod = Field(description="Billing cycle period")
    start_date: str = Field(description="Start date")
    next_billing_date: str = Field(description="Next billing date")
    end_date: str | None = Field(default=None, description="End date")
    annual_cost: Decimal = Field(description="Estimated annual cost")
    is_active: bool = Field(description="Is subscription active")
    is_auto_renew: bool = Field(description="Auto-renew flag")
    category_id: str | None = Field(default=None, description="Category ID")

    model_config = {"from_attributes": True}


class SubscriptionListResponse(BaseModel):
    """Paginated subscription list response."""

    items: list[SubscriptionSchema] = Field(description="Subscription items")
    total: int = Field(description="Total count")


class SubscriptionDetectionResult(BaseModel):
    """Result of auto-detecting a subscription from transactions."""

    name: str = Field(description="Detected subscription/merchant name")
    amount: Decimal = Field(description="Detected billing amount")
    suggested_category: str | None = Field(
        default=None, description="Suggested category name"
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Detection confidence (0-1)")
    transaction_ids: list[str] = Field(description="Transaction IDs that support this detection")
    billing_cycle: str = Field(default="monthly", description="Detected billing cycle")
