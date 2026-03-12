from abc import ABC


class AppError(Exception, ABC):
    """
    Base class for all domain-specific errors in the system.

    Attributes:
        default_message: Fallback message used when no message is provided.
    """

    default_message = "An unspecified error occurred."

    def __init__(self, message: str | None = None) -> None:
        """
        Initializes the exception with a custom or default message.

        Args:
            message: Specific error details or None to use the default message.
        """
        super().__init__(message or self.default_message)
