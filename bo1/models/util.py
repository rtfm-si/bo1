"""Model utility helpers for Board of One.

Consolidates common patterns for UUID normalization and enum coercion
used across from_db_row() methods.
"""

from datetime import datetime
from enum import Enum
from typing import Any, ClassVar, TypeVar, get_args, get_origin

from pydantic import BaseModel, Field
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined

E = TypeVar("E", bound=Enum)
T = TypeVar("T", bound="FromDbRowMixin")


def normalize_uuid(value: Any) -> str | None:
    """Normalize UUID value to string.

    Handles psycopg2 returning UUID objects (with .hex attribute)
    instead of strings.

    Args:
        value: UUID object, string, or None

    Returns:
        String representation of UUID, or None if input was None/falsy

    Example:
        >>> normalize_uuid(UUID("abc123..."))
        "abc123..."
        >>> normalize_uuid("abc123...")
        "abc123..."
        >>> normalize_uuid(None)
        None
    """
    if value is None:
        return None
    if hasattr(value, "hex"):
        return str(value)
    return str(value) if not isinstance(value, str) else value


def normalize_uuid_required(value: Any) -> str:
    """Normalize UUID value to string, asserting non-None.

    Use for required UUID fields where None is not allowed.

    Args:
        value: UUID object or string (must not be None)

    Returns:
        String representation of UUID

    Raises:
        ValueError: If value is None
    """
    if value is None:
        raise ValueError("UUID value cannot be None")
    if hasattr(value, "hex"):
        return str(value)
    return str(value) if not isinstance(value, str) else value


def coerce_enum(value: Any, enum_class: type[E], default: E | None = None) -> E:
    """Coerce value to enum type.

    Handles database returning string values that need conversion to enum.

    Args:
        value: String, enum instance, or None
        enum_class: Target enum class
        default: Default value if value is None (optional)

    Returns:
        Enum instance

    Raises:
        ValueError: If value is None and no default provided, or invalid value

    Example:
        >>> coerce_enum("active", ProjectStatus)
        ProjectStatus.ACTIVE
        >>> coerce_enum(ProjectStatus.ACTIVE, ProjectStatus)
        ProjectStatus.ACTIVE
        >>> coerce_enum(None, ProjectStatus, ProjectStatus.ACTIVE)
        ProjectStatus.ACTIVE
    """
    if value is None:
        if default is not None:
            return default
        raise ValueError(f"Cannot coerce None to {enum_class.__name__} without default")
    if isinstance(value, enum_class):
        return value
    return enum_class(value)


def _get_enum_class(annotation: Any) -> type[Enum] | None:
    """Extract enum class from a type annotation.

    Handles plain enums, Optional[EnumType], and union types.

    Returns:
        Enum class if found, None otherwise
    """
    # Direct enum type
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return annotation

    # Handle Optional[X] / X | None / Union[X, Y]
    origin = get_origin(annotation)
    if origin is not None:
        for arg in get_args(annotation):
            if arg is type(None):
                continue
            if isinstance(arg, type) and issubclass(arg, Enum):
                return arg
    return None


def _get_field_default(field_info: FieldInfo) -> Any:
    """Extract default value from Pydantic field info.

    Returns:
        Default value, or PydanticUndefined if no default
    """
    if field_info.default is not PydanticUndefined:
        return field_info.default
    if field_info.default_factory is not None:
        # default_factory is Callable[[], Any] per Pydantic docs
        return field_info.default_factory()  # type: ignore[call-arg]
    return PydanticUndefined


def _is_list_type(annotation: Any) -> bool:
    """Check if annotation is a list type."""
    origin = get_origin(annotation)
    if origin is list:
        return True
    # Handle Optional[list[X]]
    if origin is not None:
        for arg in get_args(annotation):
            if arg is type(None):
                continue
            if get_origin(arg) is list:
                return True
    return False


class AuditFieldsMixin(BaseModel):
    """Mixin providing standard audit timestamp fields.

    Use with FromDbRowMixin for automatic from_db_row() support.

    Example:
        class MyModel(AuditFieldsMixin, FromDbRowMixin):
            id: str
            name: str
    """

    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class FromDbRowMixin(BaseModel):
    """Mixin providing automatic from_db_row() for Pydantic models.

    Uses field introspection to:
    - Normalize UUID fields (objects with .hex → string)
    - Coerce enum fields (string → enum)
    - Apply list defaults (None → [])
    - Use field defaults for missing keys

    Override `_uuid_fields` class var to specify which fields are UUIDs.
    By default, 'id' and fields ending in '_id' are treated as UUIDs.

    Example:
        class MyModel(FromDbRowMixin):
            id: str
            status: MyStatus
            items: list[str] = []

            _uuid_fields: ClassVar[set[str]] = {"id", "other_uuid"}

        row = {"id": UUID(...), "status": "active"}
        model = MyModel.from_db_row(row)
    """

    _uuid_fields: ClassVar[set[str]] = set()

    @classmethod
    def _is_uuid_field(cls, field_name: str) -> bool:
        """Check if field should be treated as UUID."""
        if field_name in cls._uuid_fields:
            return True
        # Convention: 'id' or fields ending in '_id'
        return field_name == "id" or field_name.endswith("_id")

    @classmethod
    def from_db_row(cls: type[T], row: dict[str, Any]) -> T:
        """Create model instance from database row dict.

        Args:
            row: Dict from psycopg2 cursor with column data

        Returns:
            Model instance with validated data

        Raises:
            KeyError: If required field is missing from row
            ValueError: If enum coercion fails
        """
        kwargs: dict[str, Any] = {}

        for field_name, field_info in cls.model_fields.items():
            annotation = field_info.annotation

            # Check if field exists in row
            if field_name in row:
                value = row[field_name]
            else:
                # Use default if available
                default = _get_field_default(field_info)
                if default is PydanticUndefined:
                    # Required field missing - let Pydantic handle validation
                    continue
                value = default

            # Handle None values
            if value is None:
                # Check if list type - use empty list
                if _is_list_type(annotation):
                    kwargs[field_name] = []
                else:
                    kwargs[field_name] = None
                continue

            # UUID normalization
            if cls._is_uuid_field(field_name):
                value = normalize_uuid(value)

            # Enum coercion
            enum_class = _get_enum_class(annotation)
            if enum_class is not None:
                default = _get_field_default(field_info)
                if default is PydanticUndefined:
                    default = None
                # Only use default if it's an enum of the right type
                if not isinstance(default, enum_class):
                    default = None
                value = coerce_enum(value, enum_class, default)

            kwargs[field_name] = value

        return cls(**kwargs)
