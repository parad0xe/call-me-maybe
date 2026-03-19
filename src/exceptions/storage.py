from typing import Optional, Union

from src.exceptions.base import AppError


class StorageError(AppError):
    """
    Base class for all errors related to file operations (read/write).

    Attributes:
        default_message: Fallback message used when no message is provided.
        filepath: The path to the file that caused the error, if applicable.
    """

    default_message = "A file operation failed."

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
            message = (
                f"Failed to access or process file '{filepath}'."
                if filepath else self.default_message
            )
        elif self.filepath:
            message = f"({self.filepath}) {message}"

        super().__init__(message)


class StorageFileNotFoundError(StorageError):
    """
    Error raised when the target file does not exist on the filesystem.
    """

    def __init__(self, filepath: str) -> None:
        super().__init__(
            f"The specified file '{filepath}' was not found.",
            filepath=filepath,
        )


class StorageFilePermissionError(StorageError):
    """Error raised when lacking permissions to read or write the file."""

    def __init__(self, filepath: str) -> None:
        super().__init__(
            f"Permission denied for the specified file '{filepath}'.",
            filepath=filepath,
        )


class StorageEmptyFileError(StorageError):
    """
    Error raised when the provided file contains no data.
    """

    def __init__(self, filepath: str) -> None:
        super().__init__(
            f"The specified file '{filepath}' is empty.",
            filepath=filepath,
        )
