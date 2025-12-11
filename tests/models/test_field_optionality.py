"""Tests for Pydantic model field optionality vs database NULL constraints.

Validates that Pydantic models accurately reflect database schema nullability.
This prevents runtime errors when:
- Pydantic expects required fields but DB returns NULL
- Pydantic provides defaults for columns that are NOT NULL

See TASK [DATA][P2] Audit Pydantic model field optionality vs database NULL constraints
"""

import pytest
from pydantic import BaseModel
from pydantic.fields import FieldInfo

# =============================================================================
# Model-to-Table Mappings
# =============================================================================

# Maps (Pydantic model name, field name) -> (table name, column name)
# Only include fields that have a direct DB column mapping
MODEL_DB_MAPPINGS: dict[tuple[str, str], tuple[str, str, bool]] = {
    # Format: (model, field): (table, column, db_nullable)
    #
    # recommendations table
    ("Recommendation", "persona_code"): ("recommendations", "persona_code", False),
    ("Recommendation", "persona_name"): ("recommendations", "persona_name", True),
    ("Recommendation", "recommendation"): ("recommendations", "recommendation", False),
    ("Recommendation", "reasoning"): ("recommendations", "reasoning", True),
    ("Recommendation", "confidence"): ("recommendations", "confidence", True),
    ("Recommendation", "conditions"): ("recommendations", "conditions", True),
    ("Recommendation", "weight"): ("recommendations", "weight", True),
}

# =============================================================================
# Known Intentional Divergences
# =============================================================================

# Fields where Pydantic optionality intentionally differs from DB nullable
OPTIONALITY_EXCEPTIONS: dict[tuple[str, str], str] = {
    # Pydantic requires these for domain validation even though DB allows NULL
    # Reason: These fields SHOULD always be populated by the LLM;
    # DB allows NULL for forward compatibility / partial inserts during development
    (
        "Recommendation",
        "persona_name",
    ): "Required for display; DB nullable for migration flexibility",
    ("Recommendation", "reasoning"): "Required for audit trail; DB nullable for partial saves",
    ("Recommendation", "confidence"): "Required for aggregation; DB nullable for legacy data",
}


# =============================================================================
# Helper Functions
# =============================================================================


def is_pydantic_optional(field_info: FieldInfo) -> bool:
    """Check if a Pydantic field is optional (allows None or has default).

    For DB comparison purposes:
    - 'optional' means the field can be omitted when constructing the model
    - A field with `Field(...)` (Ellipsis) is REQUIRED
    - A field with `Field(default=X)` or `default_factory` is optional
    """
    from pydantic_core import PydanticUndefined

    # Check if field has a default value or factory
    has_default = (
        field_info.default is not PydanticUndefined or field_info.default_factory is not None
    )
    return has_default


def get_pydantic_models() -> dict[str, type[BaseModel]]:
    """Import and return all relevant Pydantic models."""
    from bo1.models import Recommendation

    return {
        "Recommendation": Recommendation,
    }


# =============================================================================
# Tests
# =============================================================================


class TestFieldOptionalityAudit:
    """Audit Pydantic field optionality against database nullability."""

    def test_pydantic_optionality_matches_db_nullable(self):
        """Validate that Pydantic optionality aligns with DB nullable (with exceptions)."""
        models = get_pydantic_models()
        mismatches: list[str] = []

        for (model_name, field_name), (
            table,
            column,
            db_nullable,
        ) in MODEL_DB_MAPPINGS.items():
            model = models.get(model_name)
            if model is None:
                continue

            field_info = model.model_fields.get(field_name)
            if field_info is None:
                mismatches.append(f"{model_name}.{field_name}: field not found in model")
                continue

            pydantic_optional = is_pydantic_optional(field_info)

            # Check for mismatch
            if db_nullable and not pydantic_optional:
                # DB allows NULL but Pydantic requires value
                key = (model_name, field_name)
                if key not in OPTIONALITY_EXCEPTIONS:
                    mismatches.append(
                        f"{model_name}.{field_name}: DB {table}.{column} is NULL-able "
                        f"but Pydantic field is required"
                    )
            elif not db_nullable and pydantic_optional:
                # DB requires value but Pydantic allows None
                key = (model_name, field_name)
                if key not in OPTIONALITY_EXCEPTIONS:
                    mismatches.append(
                        f"{model_name}.{field_name}: DB {table}.{column} is NOT NULL "
                        f"but Pydantic field is optional"
                    )

        if mismatches:
            pytest.fail(
                "Pydantic/DB optionality mismatches found:\n"
                + "\n".join(f"  - {m}" for m in mismatches)
                + "\n\nAdd to OPTIONALITY_EXCEPTIONS if intentional."
            )

    def test_exceptions_are_documented(self):
        """Verify all exceptions have rationale and map to real fields."""
        models = get_pydantic_models()

        for (model_name, field_name), rationale in OPTIONALITY_EXCEPTIONS.items():
            # Verify model exists
            model = models.get(model_name)
            assert model is not None, f"Exception references non-existent model: {model_name}"

            # Verify field exists
            assert field_name in model.model_fields, (
                f"Exception references non-existent field: {model_name}.{field_name}"
            )

            # Verify rationale is documented
            assert rationale, f"Exception {model_name}.{field_name} missing rationale"

    def test_no_stale_exceptions(self):
        """Ensure exceptions correspond to actual mismatches."""
        models = get_pydantic_models()

        for (model_name, field_name), _ in OPTIONALITY_EXCEPTIONS.items():
            # Verify this exception is actually needed
            mapping = MODEL_DB_MAPPINGS.get((model_name, field_name))
            if mapping is None:
                # Exception for field not in mapping - that's okay
                continue

            table, column, db_nullable = mapping
            model = models.get(model_name)
            if model is None:
                continue

            field_info = model.model_fields.get(field_name)
            if field_info is None:
                continue

            pydantic_optional = is_pydantic_optional(field_info)

            # Verify there IS a mismatch (exception is needed)
            has_mismatch = (db_nullable and not pydantic_optional) or (
                not db_nullable and pydantic_optional
            )
            assert has_mismatch, (
                f"Stale exception: {model_name}.{field_name} - "
                f"Pydantic and DB now agree (both {'optional' if pydantic_optional else 'required'})"
            )
