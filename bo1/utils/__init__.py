"""Shared utilities for Board of One system."""

from bo1.utils.error_handling import log_fallback, log_parsing_failure
from bo1.utils.json_parsing import parse_json_with_fallback, validate_json_schema
from bo1.utils.xml_parsing import extract_multiple_tags, extract_xml_tag

__all__ = [
    "extract_xml_tag",
    "extract_multiple_tags",
    "parse_json_with_fallback",
    "validate_json_schema",
    "log_fallback",
    "log_parsing_failure",
]
