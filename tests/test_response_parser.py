"""Tests for extract_json_from_response utility."""

import json

import pytest

from bo1.llm.response_parser import extract_json_from_response


def test_extract_json_raw():
    """Raw JSON parses directly."""
    assert extract_json_from_response('{"a": 1}') == {"a": 1}


def test_extract_json_raw_with_whitespace():
    """Raw JSON with whitespace."""
    assert extract_json_from_response('  {"a": 1}  ') == {"a": 1}


def test_extract_json_xml_tags():
    """XML-wrapped JSON extracts correctly."""
    text = '<json_output>{"a": 1}</json_output>'
    assert extract_json_from_response(text) == {"a": 1}


def test_extract_json_xml_tags_with_whitespace():
    """XML-wrapped JSON with internal whitespace."""
    text = '<json_output>\n  {"a": 1}\n</json_output>'
    assert extract_json_from_response(text) == {"a": 1}


def test_extract_json_markdown():
    """Markdown code block with json tag."""
    text = '```json\n{"a": 1}\n```'
    assert extract_json_from_response(text) == {"a": 1}


def test_extract_json_markdown_no_lang():
    """Markdown code block without language tag."""
    text = '```\n{"a": 1}\n```'
    assert extract_json_from_response(text) == {"a": 1}


def test_extract_json_complex():
    """Complex nested JSON structure."""
    expected = {
        "is_shallow": True,
        "quality_score": 0.25,
        "weak_aspects": ["specificity", "evidence"],
        "feedback": "Add concrete details",
    }
    text = f"```json\n{json.dumps(expected)}\n```"
    assert extract_json_from_response(text) == expected


def test_extract_json_invalid_raises():
    """Invalid JSON raises JSONDecodeError."""
    with pytest.raises(json.JSONDecodeError):
        extract_json_from_response("not json at all")


def test_extract_json_malformed_markdown_no_closing():
    """Markdown without proper closing backticks."""
    text = '```json\n{"a": 1}'
    assert extract_json_from_response(text) == {"a": 1}


def test_extract_json_multiline():
    """Multiline JSON in markdown block."""
    text = """```json
{
    "needs_research": false,
    "confidence": 0.85,
    "queries": [],
    "reason": "No external data needed"
}
```"""
    result = extract_json_from_response(text)
    assert result["needs_research"] is False
    assert result["confidence"] == 0.85


def test_extract_json_quality_check_response():
    """Simulates actual quality check LLM response format."""
    text = """```json
{
    "is_shallow": false,
    "quality_score": 0.85,
    "weak_aspects": [],
    "feedback": "Good contribution with specific details"
}
```"""
    result = extract_json_from_response(text)
    assert result["is_shallow"] is False
    assert result["quality_score"] == 0.85
    assert result["weak_aspects"] == []
