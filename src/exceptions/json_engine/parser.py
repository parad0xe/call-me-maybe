from typing import List, Optional

from src.exceptions.base import AppError
from src.json_engine.lexer import TOKEN


class ParserError(AppError):
    """
    Base class for all errors related to parsing.
    """

    default_message = "Failed to parse tokens."

    def __init__(self, message: Optional[str] = None) -> None:
        super().__init__(message or self.default_message)


class ParserUnexpectedTokenError(ParserError):
    """
    Error raised when the parser encounters a token it wasn't expecting.
    """

    def __init__(
        self, expected: List[TOKEN], received: TOKEN | tuple[None, None]
    ) -> None:
        expected_names = ", ".join([t.name for t in expected])
        super().__init__(
            f"Unexpected token {received[0] if received else 'None'}. "
            f"Expected one of: [{expected_names}]."
        )


class ParserInvalidRootError(ParserError):
    """
    Error raised when the JSON doesn't start with '{' or '['.
    """

    def __init__(self, received: TOKEN) -> None:
        super().__init__(
            "Invalid JSON root. Expected OBJ_OPEN or ARR_OPEN, "
            f"but got {received.name}."
        )


class ParserEmptyInputError(ParserError):
    """
    Error raised when the token list is empty.
    """

    def __init__(self) -> None:
        super().__init__("Cannot parse an empty list of tokens.")
