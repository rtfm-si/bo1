# Remaining Issues Fix Plan

This plan addresses issues detected during testing of the clarification flow fix. These are pre-existing issues unrelated to the clarification fix.

**Reference**: Best practices from `zzz_important/PROMPT_ENGINEERING_FRAMEWORK.md` are incorporated, particularly for JSON response handling.

## Issue Summary

| # | Issue | Severity | Root Cause | Fix Complexity |
|---|-------|----------|------------|----------------|
| 1 | JSON parsing fails when LLM wraps response in markdown | High | No markdown stripping before `json.loads()` | Low |
| 2 | Database save errors for contributions | Medium | Exception message unclear ("0") | Investigation needed |
| 3 | Facilitator decisions constraint errors | Medium | Missing/nullable user_id handling | Low |

---

## Issue 1: JSON Parsing Fails with Markdown-Wrapped Responses

### Problem
When LLMs respond with JSON wrapped in markdown code blocks (` ```json ... ``` `), the direct `json.loads()` call fails.

**Affected files:**
- `bo1/graph/quality/contribution_check.py:269` - Quality check JSON parsing
- `bo1/agents/research_detector.py:159` - Research detection JSON parsing

**Error observed:**
```
Failed to parse quality check output as JSON: Expecting value: line 1 column 1 (char 0)
Failed to parse research detection JSON: ...
```

### Root Cause
Both files call `json.loads(response_text)` directly without stripping markdown code block wrappers. When Claude/Haiku returns:
```
```json
{"key": "value"}
```
```
The `json.loads()` fails because the string starts with backticks.

### Solution: Multi-Layer Defense (per PROMPT_ENGINEERING_FRAMEWORK.md)

The prompt engineering framework recommends multiple techniques for reliable JSON extraction:

1. **Assistant Prefill** - Force LLM to start with `{` (already supported via `PromptRequest.prefill`)
2. **XML Tags** - Wrap JSON in `<json_output>...</json_output>` for reliable extraction
3. **Fallback Parsing** - Strip markdown if other methods fail

**Recommended approach**: Use prefill as primary (prevents the problem) + fallback parsing (handles edge cases).

#### Step 1: Create utility function in `bo1/llm/response_parser.py`

```python
def extract_json_from_response(text: str) -> dict:
    """Extract JSON from LLM response, stripping markdown/XML if present.

    Handles common LLM output patterns (in order of preference):
    1. Raw JSON: {"key": "value"}
    2. XML wrapped: <json_output>{"key": "value"}</json_output>
    3. Markdown wrapped: ```json\n{"key": "value"}\n```

    This is the FALLBACK parser. Prefer using prefill="{" in PromptRequest
    to prevent markdown wrapping in the first place.

    Args:
        text: Raw LLM response text

    Returns:
        Parsed JSON as dict

    Raises:
        json.JSONDecodeError: If JSON parsing fails after all extraction attempts
    """
    import json
    import re

    text = text.strip()

    # Try raw JSON first (most common with prefill)
    if text.startswith('{'):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass  # Fall through to other patterns

    # Pattern 1: XML tags <json_output>...</json_output>
    xml_pattern = r'<json_output>\s*(.*?)\s*</json_output>'
    match = re.search(xml_pattern, text, re.DOTALL)
    if match:
        return json.loads(match.group(1).strip())

    # Pattern 2: Markdown code blocks ```json ... ``` or ``` ... ```
    code_block_pattern = r'^```(?:json)?\s*\n?(.*?)\n?```$'
    match = re.match(code_block_pattern, text, re.DOTALL)
    if match:
        return json.loads(match.group(1).strip())

    # Pattern 3: Malformed markdown (leading ``` without proper closing)
    if text.startswith('```'):
        lines = text.split('\n')
        if lines[-1].strip() == '```':
            lines = lines[1:-1]
        else:
            lines = lines[1:]
        return json.loads('\n'.join(lines).strip())

    # Last resort: try parsing as-is
    return json.loads(text)
```

#### Step 2: Update `bo1/graph/quality/contribution_check.py`

**2a. Add prefill to the PromptRequest (line ~256-263):**
```python
# Before
request = PromptRequest(
    system=QUALITY_CHECK_SYSTEM_PROMPT,
    user_message=user_prompt,
    model=config.get("model", "haiku") if config else "haiku",
    temperature=config.get("temperature", 0.0) if config else 0.0,
    max_tokens=config.get("max_tokens", 500) if config else 500,
    phase="quality_check",
)

# After - add prefill to force JSON start
request = PromptRequest(
    system=QUALITY_CHECK_SYSTEM_PROMPT,
    user_message=user_prompt,
    model=config.get("model", "haiku") if config else "haiku",
    temperature=config.get("temperature", 0.0) if config else 0.0,
    max_tokens=config.get("max_tokens", 500) if config else 500,
    phase="quality_check",
    prefill="{",  # Force JSON output - prevents markdown wrapping
)
```

**2b. Use fallback parser (line ~269):**
```python
# Before
result_dict = json.loads(response_text)

# After - use robust extraction as fallback
from bo1.llm.response_parser import extract_json_from_response
result_dict = extract_json_from_response(response_text)
```

#### Step 3: Update `bo1/agents/research_detector.py`

This file uses the raw Anthropic client instead of PromptBroker, so we need a different approach.

**3a. Add assistant prefill to the messages (line ~142-147):**
```python
# Before
response = await self.anthropic_client.messages.create(
    model=model,
    max_tokens=500,
    temperature=0.0,
    messages=[{"role": "user", "content": prompt}],
)

# After - add assistant prefill message
response = await self.anthropic_client.messages.create(
    model=model,
    max_tokens=500,
    temperature=0.0,
    messages=[
        {"role": "user", "content": prompt},
        {"role": "assistant", "content": "{"},  # Prefill forces JSON start
    ],
)
```

**3b. Prepend the prefill to content and use fallback parser (line ~154-159):**
```python
# Before
content = first_block.text if first_block and hasattr(first_block, "text") else "{}"

try:
    result_data = json.loads(content)

# After
raw_content = first_block.text if first_block and hasattr(first_block, "text") else "}"
content = "{" + raw_content  # Prepend the prefill we used

from bo1.llm.response_parser import extract_json_from_response
try:
    result_data = extract_json_from_response(content)
```

#### Step 4: Add tests for the utility

Create `tests/test_response_parser.py`:
```python
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
        "feedback": "Add concrete details"
    }
    text = f'```json\n{json.dumps(expected)}\n```'
    assert extract_json_from_response(text) == expected


def test_extract_json_invalid_raises():
    """Invalid JSON raises JSONDecodeError."""
    with pytest.raises(json.JSONDecodeError):
        extract_json_from_response("not json at all")
```

---

## Issue 2: Database Save Errors for Contributions

### Problem
Contributions fail to save with cryptic error message "0".

**Error observed:**
```
Failed to save contribution to database: 0
```

### Investigation Needed

The error message "0" is unusual. Possible causes:

1. **Validation returning 0 instead of raising**: Check if `_validate_positive_int` returns the value on error
2. **round_number of 0 is valid**: According to `ContributionMessage` schema (`ge=0`) and validator (`value < 0`)
3. **Database constraint**: Some other constraint may be failing

**Step 1: Add better error logging in persona_executor.py:274-276**

```python
except Exception as e:
    # Enhanced logging for debugging
    logger.error(
        f"Failed to save contribution to database: {e!r}, "
        f"type={type(e).__name__}, "
        f"session_id={session_id}, "
        f"round_number={contrib_msg.round_number}"
    )
```

**Step 2: Check if exception is a psycopg2 error with specific codes**

The "0" might be from `psycopg2.errors.IntegrityError` where the actual error code is being printed instead of the message.

**Step 3: Add try-except specificity**

```python
from psycopg2 import errors as pg_errors

try:
    save_contribution(...)
except pg_errors.IntegrityError as e:
    logger.error(f"Database integrity error: {e.pgerror}, constraint: {e.pgcode}")
except Exception as e:
    logger.error(f"Unexpected save error: {e!r}")
```

---

## Issue 3: Facilitator Decisions Constraint Errors

### Problem
Facilitator decisions fail to save due to null user_id constraint violation.

**Error observed:**
```
null value in column "user_id" of relation "facilitator_decisions" violates not-null constraint
```

### Analysis

1. **Original migration** (`80cf34f1b577_add_persistence_tables.py`): `facilitator_decisions` table does NOT have a `user_id` column
2. **Repository function** (`contribution_repository.py:299`): `save_facilitator_decision` does NOT include `user_id`
3. **This suggests** either:
   - The database was manually modified to add user_id with NOT NULL
   - The error is from a different table (misquoted in logs)
   - An RLS policy is causing issues

### Solution

**Option A: If user_id was manually added to DB**

Create a migration to properly add user_id:

```python
# migrations/versions/xxx_add_user_id_facilitator_decisions.py
def upgrade():
    # Add user_id column (nullable first)
    op.add_column("facilitator_decisions",
        sa.Column("user_id", sa.String(255), nullable=True))

    # Backfill from sessions
    op.execute("""
        UPDATE facilitator_decisions fd
        SET user_id = s.user_id
        FROM sessions s
        WHERE fd.session_id = s.id
        AND fd.user_id IS NULL
    """)
```

Update `contribution_repository.py:save_facilitator_decision` to include user_id:

```python
def save_facilitator_decision(
    self,
    session_id: str,
    round_number: int,
    action: str,
    reasoning: str | None = None,
    next_speaker: str | None = None,
    moderator_type: str | None = None,
    research_query: str | None = None,
    sub_problem_index: int | None = None,
    user_id: str | None = None,  # ADD THIS
) -> dict[str, Any]:
    # ...
    # Fetch user_id from session if not provided
    if user_id is None:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT user_id FROM sessions WHERE id = %s", (session_id,))
                result = cur.fetchone()
                if result:
                    user_id = result[0]
```

**Option B: If error is from RLS**

Check if RLS policies on `facilitator_decisions` require user_id even though the table doesn't have it:

```sql
SELECT * FROM pg_policies WHERE tablename = 'facilitator_decisions';
```

If RLS policy references user_id but column doesn't exist, drop and recreate the policy.

---

## Implementation Order

1. **Issue 1 (JSON Parsing)** - Quick win, fixes user-facing errors immediately
   - Create `extract_json_from_response()` utility
   - Update quality_check.py
   - Update research_detector.py
   - Add tests

2. **Issue 2 (Contribution Save)** - Add enhanced logging first to understand root cause
   - Add detailed error logging
   - Deploy and monitor
   - Fix based on findings

3. **Issue 3 (Facilitator Decisions)** - Investigate DB state first
   - Check production DB schema for facilitator_decisions
   - Verify if user_id column exists
   - Create migration or fix RLS based on findings

---

## Verification

After implementing fixes:

1. Run a test deliberation and verify:
   - No JSON parsing errors in logs
   - Contributions save successfully
   - Facilitator decisions save successfully

2. Check logs for any remaining database errors

3. Run `make pre-commit` to ensure code quality

---

## Files to Modify

| File | Change |
|------|--------|
| `bo1/llm/response_parser.py` | Add `extract_json_from_response()` function |
| `bo1/graph/quality/contribution_check.py` | Use new JSON extraction utility |
| `bo1/agents/research_detector.py` | Use new JSON extraction utility |
| `bo1/orchestration/persona_executor.py` | Enhance error logging |
| `bo1/state/repositories/contribution_repository.py` | Add user_id to facilitator decision (if needed) |
| `migrations/versions/xxx.py` | Add user_id column migration (if needed) |
