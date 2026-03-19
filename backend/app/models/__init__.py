"""Database models."""

from app.models.email import Email, EmailAccount
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
from app.models.matching import Alias, TransactionGroup, TransactionGroupMember
from app.models.parser_spec import DynamicParserSpec
from app.models.health import ParserHealthMetric, ParserDisabledLog

__all__ = [
    # Email models
    "EmailAccount",
    "Email",
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
    # Matching models
    "Alias",
    "TransactionGroup",
    "TransactionGroupMember",
    # Dynamic parser models
    "DynamicParserSpec",
    # Health monitoring models
    "ParserHealthMetric",
    "ParserDisabledLog",
]
