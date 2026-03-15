"""Parser registry and discovery."""

import importlib
import logging
from pathlib import Path
from typing import Type

from app.parsers.base import BaseBankParser

logger = logging.getLogger(__name__)


class ParserRegistry:
    """Registry for managing transaction parsers."""

    _instance: "ParserRegistry | None" = None
    _parsers: dict[str, Type[BaseBankParser]] = {}
    _parser_instances: dict[str, BaseBankParser] = {}

    def __new__(cls) -> "ParserRegistry":
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register_parser(
        self,
        parser_class: Type[BaseBankParser],
        override: bool = False,
    ) -> None:
        """Register a parser class.

        Args:
            parser_class: Parser class to register
            override: Whether to override existing parser with same name
        """
        name = parser_class.name or parser_class.__name__
        if name in self._parsers and not override:
            logger.warning(f"Parser '{name}' already registered, skipping")
            return

        self._parsers[name] = parser_class
        # Create instance
        try:
            self._parser_instances[name] = parser_class()
            logger.info(f"Registered parser: {name} (v{parser_class.version})")
        except Exception as e:
            logger.error(f"Failed to instantiate parser {name}: {e}")

    def get_parser(self, name: str) -> BaseBankParser | None:
        """Get parser by name.

        Args:
            name: Parser name

        Returns:
            Parser instance or None if not found
        """
        return self._parser_instances.get(name)

    def get_all_parsers(self) -> list[BaseBankParser]:
        """Get all registered parsers."""
        return list(self._parser_instances.values())

    async def find_parser_for_email(
        self,
        sender: str,
        subject: str,
    ) -> BaseBankParser | None:
        """Find best parser for email.

        Args:
            sender: Email sender address
            subject: Email subject

        Returns:
            Best matching parser or None
        """
        matching_parsers: list[tuple[BaseBankParser, bool]] = []

        for parser in self._parser_instances.values():
            if parser.matches_email(sender, subject):
                matching_parsers.append((parser, True))
            # Also include parsers that have matching senders
            elif any(
                sender_pattern.lower() in sender.lower()
                for sender_pattern in parser.supported_senders
                if sender_pattern
            ):
                matching_parsers.append((parser, False))

        if not matching_parsers:
            return None

        # Sort by priority: exact matches first, then by order registered
        matching_parsers.sort(key=lambda x: (not x[1], -self._get_parser_priority(x[0])))
        return matching_parsers[0][0]

    def _get_parser_priority(self, parser: BaseBankParser) -> int:
        """Get parser priority (higher = earlier)."""
        # In future, this could be customizable per user/account
        # For now, return 0 for all
        return 0

    def auto_discover_parsers(self, parsers_dir: str | Path | None = None) -> int:
        """Auto-discover and register parsers.

        Args:
            parsers_dir: Directory containing parser modules (default: banks/)

        Returns:
            Number of parsers discovered
        """
        if parsers_dir is None:
            parsers_dir = Path(__file__).parent / "banks"
        else:
            parsers_dir = Path(parsers_dir)

        if not parsers_dir.exists():
            logger.warning(f"Parsers directory not found: {parsers_dir}")
            return 0

        discovered = 0

        # Import all modules in the directory
        for module_path in parsers_dir.glob("*.py"):
            if module_path.name.startswith("_"):
                continue

            module_name = module_path.stem
            full_module_name = f"app.parsers.banks.{module_name}"

            try:
                module = importlib.import_module(full_module_name)

                # Find all parser classes in the module
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, BaseBankParser)
                        and attr is not BaseBankParser
                        and attr.name
                    ):
                        self.register_parser(attr)
                        discovered += 1
            except Exception as e:
                logger.error(f"Failed to import parser module {full_module_name}: {e}")

        logger.info(f"Auto-discovered {discovered} parsers")
        return discovered

    def list_parsers(self) -> list[dict[str, str]]:
        """List all registered parsers with metadata.

        Returns:
            List of parser metadata dictionaries
        """
        return [
            {
                "name": parser.name,
                "description": parser.description,
                "version": parser.version,
                "supported_senders": ", ".join(parser.supported_senders),
            }
            for parser in self._parser_instances.values()
        ]


# Global registry instance
registry = ParserRegistry()
