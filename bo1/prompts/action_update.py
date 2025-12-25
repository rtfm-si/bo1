"""Action update summarizer prompts.

Provides prompt templates for cleaning up and formatting user-submitted
action updates. Improves grammar, structure, and readability while
preserving the original intent.
"""

# System prompt for action update summarization
ACTION_UPDATE_SYSTEM_PROMPT = """You are a concise editor. Clean up user-submitted action updates.

Rules:
- Fix grammar and typos
- Structure bullet points if listing multiple items
- Preserve the user's meaning exactly
- Keep the same tone (professional but not stiff)
- Do NOT add information that wasn't there
- Do NOT change the substance or conclusions

Output ONLY the cleaned text. No preamble, no quotes, no explanation."""

# Constraints by update type
UPDATE_TYPE_CONSTRAINTS = {
    "progress": {"max_chars": 280, "instruction": "Keep concise - max 280 chars."},
    "note": {"max_chars": 500, "instruction": "Preserve detail but clean structure."},
    "blocker": {"max_chars": 500, "instruction": "Clarify the blocking issue."},
}


def build_action_update_prompt(content: str, update_type: str) -> str:
    """Build the user prompt for action update summarization.

    Args:
        content: Raw user-submitted update content
        update_type: Type of update (progress, blocker, note)

    Returns:
        Formatted user prompt string
    """
    constraints = UPDATE_TYPE_CONSTRAINTS.get(
        update_type, {"max_chars": 500, "instruction": "Clean up the text."}
    )

    return f"""Update type: {update_type}
{constraints["instruction"]}

Raw update:
{content}

Cleaned update:"""
