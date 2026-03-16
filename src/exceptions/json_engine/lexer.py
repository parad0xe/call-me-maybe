from typing import Optional

from src.exceptions.base import AppError


class LexerError(AppError):
    """
    Base class for all errors related to lexical analysis.
    """

    default_message = "Failed to tokenize input."

    def __init__(self, message: Optional[str] = None) -> None:
        super().__init__(message or self.default_message)


class LexerInvalidCharacterError(LexerError):
    """
    Error raised when a character does not match any known token rule.
    """

    def __init__(self, char: str) -> None:
        super(
        ).__init__(f"Invalid character '{char}' encountered during lexing.")


class LexerUnterminatedStringError(LexerError):
    """
    Error raised when a string literal is opened but never closed.
    """

    def __init__(self) -> None:
        super().__init__("Unterminated string literal found.")
