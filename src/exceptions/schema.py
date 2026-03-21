from pydantic import ValidationError

from src.exceptions.base import AppError


class SchemaError(AppError):
    """
    Base class for data schema and validation errors.

    Attributes:
        default_message: Fallback message used when no message is provided.
    """

    default_message = "A schema validation operation failed."

    def __init__(self, message: str | None = None) -> None:
        """
        Initializes the error with an optional message.

        Args:
            message: Custom error message.
        """
        super().__init__(message or self.default_message)


class SchemaValidationError(SchemaError):
    """Error raised when data fails Pydantic validation checks."""

    def __init__(
        self,
        e: ValidationError,
        context: str | None = None,
    ) -> None:
        """
        Initializes the validation error with formatted messages.

        Args:
            e: The validation error object.
            context: Information about where the error occurred.
        """
        header = (
            f"Validation failed in '{context}':"
            if context else "Validation failed:"
        )
        messages: list[str] = [header]

        for error in e.errors():
            location = (
                " -> ".join(str(loc) for loc in error["loc"])
                if error["loc"] else "model"
            )
            messages.append(f"- ({location}) {error['msg']}")

        super().__init__("\n".join(messages))


class SchemaInvalidJSONFormatError(SchemaError):
    """Error raised when a JSON structure is invalid or unparsable."""

    def __init__(
        self,
        context: str | None = None,
        lineno: int | None = None,
    ) -> None:
        """
        Initializes the error for an invalid JSON structure.

        Args:
            context: Information about where the error occurred.
            lineno: Line number where the JSON parser failed.
        """
        message = "Invalid JSON format"
        if lineno is not None:
            message += f" at line {lineno}"
        if context:
            message += f" in '{context}'"

        super().__init__(f"{message}.")


class SchemaInvalidJSONRootError(SchemaError):
    """Error raised when the parsed JSON root structure is incorrect."""

    def __init__(
        self,
        expected: type[list | dict],
        context: str | None = None,
    ) -> None:
        """
        Initializes the error for an invalid JSON root element.

        Args:
            expected: The expected root type.
            context: Information about where the error occurred.
        """
        root_type = "list" if expected is list else "dict"
        message = f"Expected a JSON {root_type} at the root"
        if context:
            message += f" of '{context}'"

        super().__init__(f"{message}.")


class SchemaConstraintArgumentError(SchemaError):
    """Error raised when an argument is missing for a Constraint token."""

    def __init__(self, token_name: str) -> None:
        """
        Initializes the error for a missing Constraint argument.

        Args:
            token_name: The name of the missing argument token.
        """
        super(
        ).__init__(f"Missing argument '{token_name}' in Constraint args.")
