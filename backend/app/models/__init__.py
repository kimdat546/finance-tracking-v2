"""Database models."""

from app.models.transaction import Account, Category, CategorizationRule, Transaction
from app.models.social import Contact, SplitBill, SplitGroup, SplitParticipant
from app.models.planning import Budget, Debt, Goal, Subscription
from app.models.system import (
    EmailSyncLog,
    ParserError,
    ParserHealthAlert,
    ParserRegistry,
    ParserVersion,
    UnrecognizedEmail,
    User,
    UserSetting,
)

__all__ = [
    # Transaction models
    "Account",
    "Category",
    "Transaction",
    "CategorizationRule",
    # Social models
    "Contact",
    "SplitGroup",
    "SplitBill",
    "SplitParticipant",
    # Planning models
    "Budget",
    "Goal",
    "Debt",
    "Subscription",
    # System models
    "User",
    "EmailSyncLog",
    "ParserError",
    "ParserRegistry",
    "ParserVersion",
    "UnrecognizedEmail",
    "ParserHealthAlert",
    "UserSetting",
]
