"""Service for managing dynamic JSON parser specs in the database."""

import json
import logging

from pydantic import ValidationError
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.parser_spec import DynamicParserSpec
from app.parsers.dynamic_parser import DynamicParser, load_parser_from_dict
from app.schemas.parser_spec import ParserSpecSchema

logger = logging.getLogger(__name__)


class DynamicParserService:
    """Service layer for CRUD and runtime operations on DynamicParserSpec records."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the service with a database session.

        Args:
            session: An async SQLAlchemy session.
        """
        self.session = session

    async def create_spec(
        self,
        user_id: str | None,
        spec_dict: dict,
        is_public: bool = False,
    ) -> DynamicParserSpec:
        """Validate and persist a new parser spec to the database.

        Args:
            user_id: Owner user ID, or None for system/global specs.
            spec_dict: Raw parser spec dictionary (validated against ParserSpecSchema).
            is_public: Whether the spec is visible to all users.

        Returns:
            The newly created DynamicParserSpec record.

        Raises:
            pydantic.ValidationError: If spec_dict fails schema validation.
        """
        validated = ParserSpecSchema.model_validate(spec_dict)

        record = DynamicParserSpec(
            user_id=user_id,
            name=validated.name,
            version=validated.version,
            spec_json=json.dumps(spec_dict),
            enabled=validated.enabled,
            priority=validated.priority,
            description=validated.description,
            is_public=is_public,
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def get_spec(self, spec_id: str) -> DynamicParserSpec | None:
        """Retrieve a single parser spec by its primary key.

        Args:
            spec_id: UUID string of the spec record.

        Returns:
            DynamicParserSpec instance, or None if not found.
        """
        result = await self.session.execute(
            select(DynamicParserSpec).where(DynamicParserSpec.id == spec_id)
        )
        return result.scalar_one_or_none()

    async def list_specs(
        self,
        user_id: str | None,
        include_public: bool = True,
    ) -> list[DynamicParserSpec]:
        """List parser specs accessible to the given user.

        Args:
            user_id: User ID to filter by, or None for system specs only.
            include_public: Whether to include public (shared) specs.

        Returns:
            List of DynamicParserSpec records ordered by priority descending.
        """
        conditions = []
        if user_id is not None:
            conditions.append(DynamicParserSpec.user_id == user_id)
        else:
            conditions.append(DynamicParserSpec.user_id.is_(None))

        if include_public:
            conditions.append(DynamicParserSpec.is_public.is_(True))

        query = (
            select(DynamicParserSpec)
            .where(or_(*conditions))
            .order_by(DynamicParserSpec.priority.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_spec(
        self, spec_id: str, spec_dict: dict
    ) -> DynamicParserSpec | None:
        """Replace a stored spec's JSON and metadata with new validated data.

        Args:
            spec_id: UUID string of the spec to update.
            spec_dict: New parser spec dictionary.

        Returns:
            Updated DynamicParserSpec record, or None if not found.

        Raises:
            pydantic.ValidationError: If spec_dict fails schema validation.
        """
        record = await self.get_spec(spec_id)
        if record is None:
            return None

        validated = ParserSpecSchema.model_validate(spec_dict)

        record.name = validated.name
        record.version = validated.version
        record.spec_json = json.dumps(spec_dict)
        record.enabled = validated.enabled
        record.priority = validated.priority
        record.description = validated.description

        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def delete_spec(self, spec_id: str) -> bool:
        """Delete a parser spec by ID.

        Args:
            spec_id: UUID string of the spec to delete.

        Returns:
            True if deleted, False if the record was not found.
        """
        record = await self.get_spec(spec_id)
        if record is None:
            return False

        await self.session.delete(record)
        await self.session.commit()
        return True

    async def toggle_enabled(
        self, spec_id: str, enabled: bool
    ) -> DynamicParserSpec | None:
        """Enable or disable a parser spec.

        Args:
            spec_id: UUID string of the spec.
            enabled: New enabled state.

        Returns:
            Updated DynamicParserSpec record, or None if not found.
        """
        record = await self.get_spec(spec_id)
        if record is None:
            return None

        record.enabled = enabled
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def load_into_registry(
        self, registry: object, user_id: str | None = None
    ) -> int:
        """Load all enabled parser specs into the given parser registry.

        Retrieves enabled specs for the user (and public specs), instantiates
        DynamicParser objects, and registers them directly into the registry's
        _parser_instances dict.

        Args:
            registry: A ParserRegistry instance that exposes _parser_instances.
            user_id: User ID whose specs to load, or None for system specs.

        Returns:
            Number of parsers successfully loaded into the registry.
        """
        specs = await self.list_specs(user_id=user_id, include_public=True)
        count = 0
        for spec_record in specs:
            if not spec_record.enabled:
                continue
            try:
                spec_dict = json.loads(spec_record.spec_json)
                parser: DynamicParser = load_parser_from_dict(spec_dict)
                registry._parser_instances[parser.name] = parser  # type: ignore[attr-defined]
                logger.info(
                    f"Loaded dynamic parser '{parser.name}' (v{parser.version}) into registry"
                )
                count += 1
            except Exception as e:
                logger.error(
                    f"Failed to load dynamic parser spec '{spec_record.name}': {e}"
                )
        return count

    async def test_spec(
        self,
        spec_dict: dict,
        email_body: str,
        sender: str = "",
        subject: str = "",
    ) -> tuple[bool, dict | None, list[str], float]:
        """Test a parser spec against a sample email without persisting.

        Args:
            spec_dict: Raw parser spec dictionary.
            email_body: Sample email body text.
            sender: Sample email sender address.
            subject: Sample email subject line.

        Returns:
            Tuple of (matched, result_dict_or_None, errors, elapsed_ms).

        Raises:
            pydantic.ValidationError: If spec_dict fails schema validation.
        """
        parser = load_parser_from_dict(spec_dict)
        matched = parser.matches_email(sender, subject)

        result, errors, elapsed_ms = await parser.parse_with_context(
            email_body, sender=sender, subject=subject
        )

        result_dict = result.to_dict() if result is not None else None
        return matched, result_dict, errors, elapsed_ms
