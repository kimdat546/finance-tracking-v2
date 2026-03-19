"""Category seeder service – seeds default categories and rules for new users."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Category, CategorizationRule, TransactionType
from app.services.categorizer import RuleEngine

logger = logging.getLogger(__name__)

DEFAULT_CATEGORIES: list[dict] = [
    # Income
    {"name": "Lương", "name_en": "Salary", "type": "income", "icon": "💼", "color": "#4CAF50"},
    {"name": "Thưởng", "name_en": "Bonus", "type": "income", "icon": "🎁", "color": "#8BC34A"},
    {"name": "Đầu tư", "name_en": "Investment", "type": "income", "icon": "📈", "color": "#009688"},
    {
        "name": "Khác",
        "name_en": "Other Income",
        "type": "income",
        "icon": "💰",
        "color": "#00BCD4",
    },
    # Food & Drink
    {
        "name": "Ăn uống",
        "name_en": "Food & Drink",
        "type": "expense",
        "icon": "🍜",
        "color": "#FF5722",
    },
    {
        "name": "Cà phê",
        "name_en": "Coffee",
        "type": "expense",
        "icon": "☕",
        "color": "#795548",
    },
    {
        "name": "Đặt đồ ăn",
        "name_en": "Food Delivery",
        "type": "expense",
        "icon": "🛵",
        "color": "#FF9800",
    },
    # Transport
    {
        "name": "Di chuyển",
        "name_en": "Transport",
        "type": "expense",
        "icon": "🚗",
        "color": "#2196F3",
    },
    {
        "name": "Grab/Taxi",
        "name_en": "Ride Hailing",
        "type": "expense",
        "icon": "🚕",
        "color": "#3F51B5",
    },
    {
        "name": "Xăng dầu",
        "name_en": "Fuel",
        "type": "expense",
        "icon": "⛽",
        "color": "#607D8B",
    },
    # Shopping
    {
        "name": "Mua sắm",
        "name_en": "Shopping",
        "type": "expense",
        "icon": "🛍️",
        "color": "#E91E63",
    },
    {
        "name": "Siêu thị",
        "name_en": "Grocery",
        "type": "expense",
        "icon": "🛒",
        "color": "#9C27B0",
    },
    # Bills & Utilities
    {
        "name": "Hóa đơn",
        "name_en": "Bills",
        "type": "expense",
        "icon": "📄",
        "color": "#F44336",
    },
    {
        "name": "Điện nước",
        "name_en": "Utilities",
        "type": "expense",
        "icon": "💡",
        "color": "#FF5722",
    },
    {
        "name": "Internet",
        "name_en": "Internet",
        "type": "expense",
        "icon": "🌐",
        "color": "#009688",
    },
    # Entertainment
    {
        "name": "Giải trí",
        "name_en": "Entertainment",
        "type": "expense",
        "icon": "🎬",
        "color": "#673AB7",
    },
    {
        "name": "Streaming",
        "name_en": "Streaming",
        "type": "expense",
        "icon": "📺",
        "color": "#9C27B0",
    },
    {"name": "Game", "name_en": "Gaming", "type": "expense", "icon": "🎮", "color": "#3F51B5"},
    # Health
    {
        "name": "Sức khỏe",
        "name_en": "Health",
        "type": "expense",
        "icon": "🏥",
        "color": "#F44336",
    },
    {
        "name": "Thuốc",
        "name_en": "Medicine",
        "type": "expense",
        "icon": "💊",
        "color": "#E91E63",
    },
    # Education
    {
        "name": "Giáo dục",
        "name_en": "Education",
        "type": "expense",
        "icon": "📚",
        "color": "#2196F3",
    },
    {
        "name": "Khóa học",
        "name_en": "Courses",
        "type": "expense",
        "icon": "🎓",
        "color": "#03A9F4",
    },
    # Subscriptions
    {
        "name": "Subscription",
        "name_en": "Subscription",
        "type": "expense",
        "icon": "🔄",
        "color": "#FF9800",
    },
    {
        "name": "Dev Tools",
        "name_en": "Dev Tools",
        "type": "expense",
        "icon": "💻",
        "color": "#607D8B",
    },
    # Savings & Transfer
    {
        "name": "Tiết kiệm",
        "name_en": "Savings",
        "type": "transfer",
        "icon": "🏦",
        "color": "#4CAF50",
    },
    {
        "name": "Chuyển khoản",
        "name_en": "Transfer",
        "type": "transfer",
        "icon": "↔️",
        "color": "#9E9E9E",
    },
    # Other
    {
        "name": "Khác",
        "name_en": "Other",
        "type": "expense",
        "icon": "📦",
        "color": "#9E9E9E",
    },
]

# Default rules reference category by *name_en* for lookup convenience
DEFAULT_RULES: list[dict] = [
    # Food delivery
    {
        "pattern": r"grab food|grabfood|shopeefood|baemin|gofood",
        "category_name_en": "Food Delivery",
        "match_type": "regex",
        "match_field": "any",
        "priority": 80,
        "name": "Food Delivery Apps",
    },
    # Coffee
    {
        "pattern": r"cà phê|coffee|highlands|starbucks|the coffee house|phuc long",
        "category_name_en": "Coffee",
        "match_type": "regex",
        "match_field": "any",
        "priority": 80,
        "name": "Coffee Shops",
    },
    # Ride hailing
    {
        "pattern": r"grab|gojek|be app|taxi",
        "category_name_en": "Ride Hailing",
        "match_type": "regex",
        "match_field": "merchant",
        "priority": 70,
        "name": "Ride Hailing Apps",
    },
    # Fuel
    {
        "pattern": r"xăng|petrolimex|shell|fuel",
        "category_name_en": "Fuel",
        "match_type": "regex",
        "match_field": "any",
        "priority": 70,
        "name": "Fuel Stations",
    },
    # Shopping
    {
        "pattern": r"shopee|lazada|tiki|sendo",
        "category_name_en": "Shopping",
        "match_type": "regex",
        "match_field": "merchant",
        "priority": 70,
        "name": "Online Shopping",
    },
    # Grocery
    {
        "pattern": r"vinmart|coopmart|big c|lotte mart|mm mega",
        "category_name_en": "Grocery",
        "match_type": "regex",
        "match_field": "merchant",
        "priority": 70,
        "name": "Supermarkets",
    },
    # Internet / Telecom
    {
        "pattern": r"vnpt|viettel|mobifone|vinaphone",
        "category_name_en": "Internet",
        "match_type": "regex",
        "match_field": "merchant",
        "priority": 70,
        "name": "Telecom Providers",
    },
    # Streaming
    {
        "pattern": r"netflix|spotify|youtube premium|apple|disney",
        "category_name_en": "Streaming",
        "match_type": "regex",
        "match_field": "any",
        "priority": 70,
        "name": "Streaming Services",
    },
    # Dev Tools
    {
        "pattern": r"github|jetbrains|digitalocean|aws|google cloud|cloudflare",
        "category_name_en": "Dev Tools",
        "match_type": "regex",
        "match_field": "any",
        "priority": 70,
        "name": "Developer Tools",
    },
]

# Map TransactionType string values
_TX_TYPE_MAP: dict[str, TransactionType] = {
    "income": TransactionType.INCOME,
    "expense": TransactionType.EXPENSE,
    "transfer": TransactionType.TRANSFER,
}


class CategorySeeder:
    """Seeds default categories and rules for a new user."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialise CategorySeeder.

        Args:
            session: Async SQLAlchemy database session.
        """
        self.session = session

    async def seed_categories(self, user_id: str) -> list[Category]:
        """Create default categories for a user, skipping any that already exist.

        Args:
            user_id: The user's ID.

        Returns:
            List of newly created Category objects.
        """
        existing_result = await self.session.execute(
            select(Category.name).where(Category.user_id == user_id)
        )
        existing_names: set[str] = {row[0] for row in existing_result.all()}

        created: list[Category] = []
        for cat_def in DEFAULT_CATEGORIES:
            if cat_def["name"] in existing_names:
                continue
            tx_type = _TX_TYPE_MAP.get(cat_def["type"], TransactionType.EXPENSE)
            category = Category(
                user_id=user_id,
                name=cat_def["name"],
                description=cat_def.get("name_en"),
                icon=cat_def.get("icon"),
                color=cat_def.get("color"),
                transaction_type=tx_type,
                is_system=True,
                is_active=True,
            )
            self.session.add(category)
            created.append(category)

        if created:
            await self.session.flush()
            logger.info("Seeded %d categories for user %s", len(created), user_id)
        return created

    async def seed_rules(self, user_id: str) -> list[CategorizationRule]:
        """Create default categorization rules for a user.

        Categories must already exist (call seed_categories first).

        Args:
            user_id: The user's ID.

        Returns:
            List of newly created CategorizationRule objects.
        """
        # Build name_en → Category.id map
        cat_result = await self.session.execute(
            select(Category).where(Category.user_id == user_id, Category.is_active == True)  # noqa: E712
        )
        categories = list(cat_result.scalars().all())
        # description column stores name_en
        name_en_to_id: dict[str, str] = {
            (cat.description or ""): cat.id for cat in categories if cat.description
        }
        # Also index by Vietnamese name as fallback
        name_to_id: dict[str, str] = {cat.name: cat.id for cat in categories}

        # Existing rule patterns to avoid duplicates
        existing_result = await self.session.execute(
            select(CategorizationRule.pattern).where(
                CategorizationRule.user_id == user_id,
                CategorizationRule.is_active == True,  # noqa: E712
            )
        )
        existing_patterns: set[str] = {row[0] for row in existing_result.all() if row[0]}

        rule_engine = RuleEngine(self.session)
        created: list[CategorizationRule] = []
        for rule_def in DEFAULT_RULES:
            if rule_def["pattern"] in existing_patterns:
                continue
            cat_id = name_en_to_id.get(rule_def["category_name_en"]) or name_to_id.get(
                rule_def["category_name_en"]
            )
            if not cat_id:
                logger.warning(
                    "Seed rule '%s': category '%s' not found, skipping",
                    rule_def["name"],
                    rule_def["category_name_en"],
                )
                continue
            rule = await rule_engine.create_rule(
                user_id=user_id,
                name=rule_def["name"],
                pattern=rule_def["pattern"],
                category_id=cat_id,
                priority=rule_def.get("priority", 50),
                match_type=rule_def["match_type"],
                match_field=rule_def["match_field"],
            )
            created.append(rule)

        if created:
            await self.session.flush()
            logger.info("Seeded %d rules for user %s", len(created), user_id)
        return created

    async def seed_all(self, user_id: str) -> dict:
        """Seed categories and rules for a user.

        Args:
            user_id: The user's ID.

        Returns:
            Dictionary with keys "categories_created" and "rules_created".
        """
        categories = await self.seed_categories(user_id)
        rules = await self.seed_rules(user_id)
        return {
            "categories_created": len(categories),
            "rules_created": len(rules),
        }

    async def is_seeded(self, user_id: str) -> bool:
        """Check whether default categories have already been seeded for a user.

        Args:
            user_id: The user's ID.

        Returns:
            True if the user already has at least 10 active categories.
        """
        result = await self.session.execute(
            select(Category)
            .where(
                Category.user_id == user_id,
                Category.is_active == True,  # noqa: E712
                Category.is_system == True,  # noqa: E712
            )
            .limit(10)
        )
        rows = result.scalars().all()
        return len(rows) >= 10
