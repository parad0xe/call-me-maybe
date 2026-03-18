from typing import Optional, Union

from pydantic import ValidationError

from src.exceptions.base import AppError


class LoaderError(AppError):
    """
    Base class for all errors related to load files.

    Attributes:
        default_message: Fallback message used when no message is provided.
        filepath: The path to the file that caused the error, if applicable.
    """

    default_message = "Failed to load file."

    def __init__(
        self,
        message: Optional[str] = None,
        filepath: Union[str, None] = None,
    ) -> None:
        """
        Initializes the error with an optional message and filepath.

        Args:
            message: Custom error message.
            filepath: Path to the file.
        """
        self.filepath = filepath

        if message is None:
            if self.filepath:
                message = f"Failed to load file '{self.filepath}'."
            else:
                message = self.default_message
        elif self.filepath:
            message = f"({self.filepath}) {message}"

        super().__init__(message)


class LoaderFileNotFoundError(LoaderError):
    """
    Error raised when the target file does not exist on the filesystem.
    """

    def __init__(self, filepath: str) -> None:
        super().__init__(
            f"The specified file '{filepath}' was not found.",
            filepath=filepath,
        )


class LoaderFilePermissionError(LoaderError):
    """
    Error raised when the application lacks permissions to access the file.
    """

    def __init__(self, filepath: str) -> None:
        super().__init__(
            f"Permission denied for the specified file '{filepath}'.",
            filepath=filepath,
        )


class LoaderEmptyFileError(LoaderError):
    """
    Error raised when the provided file contains no data to load.
    """

    def __init__(self, filepath: str) -> None:
        super().__init__(
            f"The specified file '{filepath}' is empty.",
            filepath=filepath,
        )


class LoaderValidationError(LoaderError):
    """Error raised when configuration data fails validation checks."""

    def __init__(self, e: ValidationError, filepath: str) -> None:
        """
        Initializes the validation error with formatted messages.

        Args:
            e: The Pydantic validation error.
            filepath: Path to the invalid file.
        """
        messages: list[str] = []

        messages.append("")
        for error in e.errors():
            location = (
                " -> ".join(str(loc) for loc in error["loc"])
                if error["loc"] else "model"
            )

            messages.append(f"- ({location}) {error['msg']}")

        super().__init__(
            "\n".join(messages),
            filepath=filepath,
        )
