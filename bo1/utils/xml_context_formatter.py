"""Formatting utilities for context data.

Consolidates XML formatting patterns used across agents for prompt composition.
"""

from typing import Any


class XMLContextFormatter:
    """Utility for formatting context data as XML for prompts.

    Consolidates common XML formatting patterns that were duplicated across
    context_collector.py and researcher.py.

    Examples:
        >>> formatter = XMLContextFormatter()
        >>> data = {"business_model": "B2B SaaS", "revenue": "$100K ARR"}
        >>> print(formatter.format_dict_as_xml(data, "business_context"))
        <business_context>
          <business_model>B2B SaaS</business_model>
          <revenue>$100K ARR</revenue>
        </business_context>
    """

    @staticmethod
    def format_dict_as_xml(
        data: dict[str, Any],
        root_tag: str,
        item_tag: str | None = None,
    ) -> str:
        r"""Format dictionary as XML with optional nested structure.

        Args:
            data: Dictionary to format
            root_tag: Root XML tag name
            item_tag: Optional tag name for items (unused, for signature compatibility)

        Returns:
            Formatted XML string

        Examples:
            >>> data = {"name": "John", "role": "CEO"}
            >>> XMLContextFormatter.format_dict_as_xml(data, "person")
            '<person>\\n  <name>John</name>\\n  <role>CEO</role>\\n</person>'

            >>> data = {"skills": ["Python", "Go"], "level": "Senior"}
            >>> XMLContextFormatter.format_dict_as_xml(data, "developer")
            '<developer>\\n  <skills>\\n    Python\\n    Go\\n  </skills>\\n  <level>Senior</level>\\n</developer>'
        """
        if not data:
            return ""

        lines = [f"<{root_tag}>"]
        for key, value in data.items():
            if isinstance(value, list):
                lines.append(f"  <{key}>")
                for item in value:
                    lines.append(f"    {item}")
                lines.append(f"  </{key}>")
            else:
                lines.append(f"  <{key}>{value}</{key}>")
        lines.append(f"</{root_tag}>")
        return "\n".join(lines)

    @staticmethod
    def format_list_as_xml(
        items: list[dict[str, Any]],
        root_tag: str,
        item_tag: str,
        field_mapping: dict[str, str],
    ) -> str:
        """Format list of dicts as XML with field mapping.

        Args:
            items: List of dictionaries to format
            root_tag: Root XML tag name
            item_tag: Tag name for each item
            field_mapping: Dict mapping field names to XML tag names
                          e.g., {"question": "q", "priority": "p"}

        Returns:
            Formatted XML string

        Examples:
            >>> items = [
            ...     {"question": "What is your revenue?", "priority": "HIGH"},
            ...     {"question": "How many employees?", "priority": "LOW"}
            ... ]
            >>> mapping = {"question": "text", "priority": "level"}
            >>> print(XMLContextFormatter.format_list_as_xml(items, "questions", "q", mapping))
            <questions>
              <q>
                <text>What is your revenue?</text>
                <level>HIGH</level>
              </q>
              <q>
                <text>How many employees?</text>
                <level>LOW</level>
              </q>
            </questions>
        """
        if not items:
            return ""

        lines = [f"<{root_tag}>"]
        for item in items:
            lines.append(f"  <{item_tag}>")
            for field, label in field_mapping.items():
                if field in item:
                    lines.append(f"    <{label}>{item[field]}</{label}>")
            lines.append(f"  </{item_tag}>")
        lines.append(f"</{root_tag}>")
        return "\n".join(lines)
