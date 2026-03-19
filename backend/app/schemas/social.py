"""Social finance feature schemas (contacts, split bills, groups)."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Contact schemas
# ---------------------------------------------------------------------------


class ContactCreateRequest(BaseModel):
    """Request body for creating a contact."""

    name: str = Field(description="Contact name", min_length=1, max_length=255)
    phone: str | None = Field(default=None, description="Phone number", max_length=20)
    email: str | None = Field(default=None, description="Email address", max_length=255)
    notes: str | None = Field(default=None, description="Additional notes")


class ContactUpdateRequest(BaseModel):
    """Request body for updating a contact (all fields optional)."""

    name: str | None = Field(default=None, description="Contact name", max_length=255)
    phone: str | None = Field(default=None, description="Phone number", max_length=20)
    email: str | None = Field(default=None, description="Email address", max_length=255)
    notes: str | None = Field(default=None, description="Additional notes")


class ContactSchema(BaseModel):
    """Contact response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Contact ID")
    name: str = Field(description="Contact name")
    phone: str | None = Field(description="Phone number")
    email: str | None = Field(description="Email address")
    notes: str | None = Field(description="Additional notes")
    created_at: datetime = Field(description="Created at timestamp")


class ContactListResponse(BaseModel):
    """Paginated list of contacts."""

    items: list[ContactSchema] = Field(description="List of contacts")
    total: int = Field(description="Total number of contacts")
    page: int = Field(description="Current page")
    page_size: int = Field(description="Page size")
    total_pages: int = Field(description="Total pages")


# ---------------------------------------------------------------------------
# Split Group schemas
# ---------------------------------------------------------------------------


class SplitGroupCreateRequest(BaseModel):
    """Request body for creating a split group."""

    name: str = Field(description="Group name", min_length=1, max_length=255)
    description: str | None = Field(default=None, description="Group description")
    contact_ids: list[str] = Field(default_factory=list, description="Initial member contact IDs")


class SplitGroupUpdateRequest(BaseModel):
    """Request body for updating a split group."""

    name: str | None = Field(default=None, description="Group name", max_length=255)
    description: str | None = Field(default=None, description="Group description")


class SplitGroupSchema(BaseModel):
    """Split group response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Group ID")
    name: str = Field(description="Group name")
    description: str | None = Field(description="Group description")
    member_count: int = Field(description="Number of members in the group")
    total_amount: Decimal = Field(description="Total amount across all bills in this group")
    created_at: datetime = Field(description="Created at timestamp")


class SplitGroupListResponse(BaseModel):
    """Paginated list of split groups."""

    items: list[SplitGroupSchema] = Field(description="List of groups")
    total: int = Field(description="Total number of groups")
    page: int = Field(description="Current page")
    page_size: int = Field(description="Page size")
    total_pages: int = Field(description="Total pages")


# ---------------------------------------------------------------------------
# Split Bill schemas
# ---------------------------------------------------------------------------


class SplitParticipantInput(BaseModel):
    """Input for a single participant in a split bill."""

    contact_id: str = Field(description="Contact ID of the participant")
    share_amount: Decimal = Field(description="Amount this participant owes", ge=0)
    already_paid: bool = Field(default=False, description="Whether this participant has already paid")


class SplitBillCreateRequest(BaseModel):
    """Request body for creating a split bill."""

    title: str = Field(description="Bill title", min_length=1, max_length=255)
    total_amount: Decimal = Field(description="Total bill amount", gt=0)
    payer_contact_id: str = Field(description="Contact ID of who paid the bill")
    group_id: str | None = Field(default=None, description="Split group ID (optional)")
    splits: list[SplitParticipantInput] = Field(
        description="List of participants and their share amounts"
    )
    transaction_id: str | None = Field(
        default=None, description="Linked transaction ID (optional)"
    )
    notes: str | None = Field(default=None, description="Additional notes")


class SplitBillUpdateRequest(BaseModel):
    """Request body for updating a split bill."""

    title: str | None = Field(default=None, description="Bill title", max_length=255)
    notes: str | None = Field(default=None, description="Additional notes")


class SplitParticipantSchema(BaseModel):
    """Participant in a split bill response schema."""

    model_config = ConfigDict(from_attributes=True)

    contact_id: str = Field(description="Contact ID")
    contact_name: str = Field(description="Contact name")
    share_amount: Decimal = Field(description="Amount this participant owes")
    paid_amount: Decimal = Field(description="Amount already paid by this participant")
    is_settled: bool = Field(description="Whether this participant has fully settled")


class SplitBillSchema(BaseModel):
    """Split bill response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Split bill ID")
    title: str = Field(description="Bill title")
    total_amount: Decimal = Field(description="Total bill amount")
    payer_contact_id: str = Field(description="Contact ID of who paid")
    status: str = Field(description="Bill status: pending | partial | settled")
    participants: list[SplitParticipantSchema] = Field(
        description="List of participants"
    )
    notes: str | None = Field(description="Additional notes")
    created_at: datetime = Field(description="Created at timestamp")


class SplitBillListResponse(BaseModel):
    """Paginated list of split bills."""

    items: list[SplitBillSchema] = Field(description="List of split bills")
    total: int = Field(description="Total number of bills")
    page: int = Field(description="Current page")
    page_size: int = Field(description="Page size")
    total_pages: int = Field(description="Total pages")


# ---------------------------------------------------------------------------
# Settlement / Balance schemas
# ---------------------------------------------------------------------------


class SettleParticipantRequest(BaseModel):
    """Request body for settling a participant's share."""

    contact_id: str = Field(description="Contact ID of the participant settling")
    amount: Decimal = Field(description="Amount being paid", gt=0)


class NetBalanceSchema(BaseModel):
    """Net balance between the user and a contact."""

    contact_id: str = Field(description="Contact ID")
    contact_name: str = Field(description="Contact name")
    they_owe_me: Decimal = Field(description="Total amount this contact owes the user")
    i_owe_them: Decimal = Field(description="Total amount the user owes this contact")
    net: Decimal = Field(
        description="Net balance: positive means they owe the user, negative means user owes them"
    )


class SettlementSummarySchema(BaseModel):
    """High-level settlement summary for the user."""

    total_owed_to_me: Decimal = Field(description="Sum of all amounts owed to the user")
    total_i_owe: Decimal = Field(description="Sum of all amounts the user owes others")
    net_position: Decimal = Field(
        description="Net position: positive means user is owed more than they owe"
    )
    unsettled_bills_count: int = Field(description="Number of unsettled or partially settled bills")


# ---------------------------------------------------------------------------
# Reminder schemas
# ---------------------------------------------------------------------------


class PendingReminderSchema(BaseModel):
    """Pending reminder for a contact."""

    contact_id: str = Field(description="Contact ID")
    contact_name: str = Field(description="Contact name")
    total_owed: Decimal = Field(description="Total amount owed by this contact")
    oldest_bill_date: datetime = Field(description="Date of the oldest unsettled bill")
    bill_titles: list[str] = Field(description="Titles of unsettled bills")
    reminder_message: str = Field(description="Formatted reminder message")


class AddGroupMemberRequest(BaseModel):
    """Request body for adding a member to a group."""

    contact_id: str = Field(description="Contact ID to add to the group")
