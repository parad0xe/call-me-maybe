from __future__ import annotations

import re
from collections import deque
from enum import Enum
from typing import TypeAlias

from src.exceptions.json_engine.lexer import (
    LexerInvalidCharacterError,
)

WS: str = r"[\s\n\t\r]*"


class TOKEN(tuple, Enum):
    # ARR_OPEN = "ARR_OPEN"
    # ARR_CLOSE = "ARR_CLOSE"
    # OBJ_OPEN = "OBJ_OPEN"
    # OBJ_CLOSE = "OBJ_CLOSE"
    # INTEGER = "INTEGER"
    # FLOAT = "FLOAT"
    # BOOL = "BOOL"
    # NULL = "NULL"
    # STRING_OPEN = "STRING_OPEN"
    # STRING_CLOSE = "STRING_CLOSE"
    # TEXT = "TEXT"
    # COMMA = "COMMA"
    # COLON = "COLON"

    ARR_OPEN = ("ARR_OPEN", rf"{WS}(\[){WS}")
    ARR_CLOSE = ("ARR_CLOSE", rf"{WS}(]){WS}")
    OBJ_OPEN = ("OBJ_OPEN", rf"{WS}(\{{){WS}")
    OBJ_CLOSE = ("OBJ_CLOSE", rf"{WS}(\}}){WS}")
    INTEGER = ("INTEGER", rf"{WS}(\d+){WS}")
    FLOAT = ("FLOAT", rf"{WS}(\d+\.\d*){WS}")
    BOOL = ("BOOL", rf"{WS}(true|false){WS}")
    NULL = ("NULL", rf"{WS}(null){WS}")
    STRING_OPEN = ("STRING_OPEN", rf"{WS}(\").*{WS}")
    STRING_CLOSE = ("STRING_CLOSE", rf"{WS}.*(\"){WS}")
    TEXT = ("TEXT", rf"{WS}([^\"\\]*(?:\\.[^\"\\]*)*){WS}")
    COMMA = ("COMMA", rf"{WS}(,){WS}")
    COLON = ("COLON", rf"{WS}(:){WS}")


TOKEN_TYPE: TypeAlias = tuple[TOKEN, str | int | float | bool | None]
TOKEN_LIST_TYPE: TypeAlias = deque[TOKEN_TYPE]


class JSONLexer:

    @staticmethod
    def lex(text: str) -> TOKEN_LIST_TYPE:
        tokens: TOKEN_LIST_TYPE = deque([])
        i = 0
        while i < len(text):
            c = text[i]

            if c.isspace():
                i += 1
                continue

            if c == "[":
                tokens.append((TOKEN.ARR_OPEN, "["))
            elif c == "]":
                tokens.append((TOKEN.ARR_CLOSE, "]"))
            elif c == "{":
                tokens.append((TOKEN.OBJ_OPEN, "{"))
            elif c == "}":
                tokens.append((TOKEN.OBJ_CLOSE, "}"))
            elif c == ",":
                tokens.append((TOKEN.COMMA, ","))
            elif c == ":":
                tokens.append((TOKEN.COLON, ":"))
            elif c == '"':
                tokens.append((TOKEN.STRING_OPEN, '"'))
                substr: str = ""
                i += 1
                while i < len(text) - 1 and text[i] != '"':
                    substr += text[i]
                    i += 1

                if i < len(text) and text[i] != '"' or text[i - 1] == "\\":
                    substr += text[i]

                if i < len(text):
                    tokens.append((TOKEN.TEXT, substr))

                if i < len(text) and text[i] == '"' and text[i - 1] != "\\":
                    tokens.append((TOKEN.STRING_CLOSE, '"'))
            elif match := re.match(r"(\d+).*", text[i:]):
                value = match.group(1)
                i += len(value) - 1
                number_int: int = int(value)
                tokens.append((TOKEN.INTEGER, number_int))
            elif match := re.match(r"(\d+\.\d*).*", text[i:]):
                value = match.group(1)
                i += len(value) - 1
                number_float: float = float(value)
                tokens.append((TOKEN.FLOAT, number_float))
            elif match := re.match(r"(true|false).*", text[i:]):
                value = match.group(1)
                i += len(value) - 1
                boolean: int = bool(True if value == "true" else False)
                tokens.append((TOKEN.BOOL, boolean))
            elif match := re.match(r"(null).*", text[i:]):
                value = match.group(1)
                i += len(value) - 1
                tokens.append((TOKEN.NULL, None))
            else:
                raise LexerInvalidCharacterError(c)
            i += 1
        return tokens
