from abc import ABC


class AppError(Exception, ABC):
    """Base class for all domain-specific errors in the application.

    Attributes:
        default_message: Fallback message when no custom message is given.
    """

    default_message = "An unexpected application error occurred."

    def __init__(self, message: str | None = None) -> None:
        """Initializes the exception with a custom or default message.

        Args:
            message: Specific error details to display.
        """
        super().__init__(message or self.default_message)
