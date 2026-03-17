from typing import TypeAlias

from pydantic import BaseModel

from src.exceptions.json_engine.parser import ParserUnexpectedTokenError
from src.json_engine.lexer import TOKEN, TOKEN_LIST_TYPE, TOKEN_TYPE

VALUE: list[TOKEN] = [
    TOKEN.STRING_OPEN,
    TOKEN.INTEGER,
    TOKEN.FLOAT,
    TOKEN.ARR_OPEN,
    TOKEN.OBJ_OPEN,
    TOKEN.BOOL,
    TOKEN.NULL,
]

PREDICATES_TYPE: TypeAlias = list[tuple[str, str]]


class JSONParser(BaseModel):
    tokens: TOKEN_LIST_TYPE

    @classmethod
    def next(cls, tokens: TOKEN_LIST_TYPE) -> PREDICATES_TYPE:
        return cls(tokens=tokens)._next()

    @property
    def _get_current_token(self) -> TOKEN | tuple[None, None]:
        if not self.tokens:
            return None, None
        return self.tokens[0][0]

    def _eat(self) -> TOKEN_TYPE | tuple[tuple[None, None], None]:
        if self.tokens:
            return self.tokens.popleft()
        return (None, None), None

    def _is(self, token: TOKEN) -> bool:
        return self._get_current_token == token

    def _expected(self, expected: list[TOKEN]) -> PREDICATES_TYPE | None:
        if self._get_current_token not in expected:
            if self.tokens:
                raise ParserUnexpectedTokenError(
                    expected, self._get_current_token
                )
            return [e.value for e in expected]
        return None

    def _expected_eat(self, expected: TOKEN) -> PREDICATES_TYPE | None:
        current_token, _ = self._eat()
        if current_token != expected:
            if self.tokens:
                raise ParserUnexpectedTokenError([expected], current_token)
            return [expected.value]
        return None

    def _next(self) -> PREDICATES_TYPE:
        if self._is(TOKEN.ARR_OPEN):
            return self._parse_array()

        if self._is(TOKEN.OBJ_OPEN):
            return self._parse_object()

        return [TOKEN.ARR_OPEN.value, TOKEN.OBJ_OPEN.value]

    def _parse_null(self) -> PREDICATES_TYPE:
        if predicates := self._expected_eat(TOKEN.NULL):
            return predicates
        return []

    def _parse_bool(self) -> PREDICATES_TYPE:
        if predicates := self._expected_eat(TOKEN.BOOL):
            return predicates
        return []

    def _parse_array(self) -> PREDICATES_TYPE:
        if predicates := self._expected_eat(TOKEN.ARR_OPEN):
            return predicates

        if predicates := self._expected(VALUE):
            return predicates

        while self.tokens and not self._is(TOKEN.ARR_CLOSE):
            if predicates := self._parse_value():
                return predicates

            if predicates := self._expected([TOKEN.COMMA, TOKEN.ARR_CLOSE]):
                return predicates

            if self._is(TOKEN.COMMA):
                self._eat()

                if predicates := self._expected(VALUE):
                    return predicates

        if predicates := self._expected_eat(TOKEN.ARR_CLOSE):
            return predicates

        return []

    def _parse_object(self) -> PREDICATES_TYPE:
        if predicates := self._expected_eat(TOKEN.OBJ_OPEN):
            return predicates

        if predicates := self._expected([TOKEN.STRING_OPEN, TOKEN.OBJ_CLOSE]):
            return predicates

        while self.tokens and not self._is(TOKEN.OBJ_CLOSE):
            if self._is(TOKEN.STRING_OPEN):
                if predicates := self._parse_string():
                    return predicates

                if predicates := self._expected_eat(TOKEN.COLON):
                    return predicates

                if predicates := self._expected(VALUE):
                    return predicates

                if predicates := self._parse_value():
                    return predicates

                if predicates := self._expected([TOKEN.COMMA,
                                                 TOKEN.OBJ_CLOSE]):
                    return predicates

                if self._is(TOKEN.COMMA):
                    self._eat()

                    if predicates := self._expected([TOKEN.STRING_OPEN]):
                        return predicates

            elif self._is(TOKEN.OBJ_CLOSE):
                break

        if predicates := self._expected_eat(TOKEN.OBJ_CLOSE):
            return predicates

        return []

    def _parse_number(self) -> PREDICATES_TYPE:
        if predicates := self._expected([TOKEN.INTEGER, TOKEN.FLOAT]):
            return predicates
        self._eat()
        return []

    def _parse_string(self) -> PREDICATES_TYPE:
        if predicates := self._expected_eat(TOKEN.STRING_OPEN):
            return predicates

        if predicates := self._expected([TOKEN.TEXT, TOKEN.STRING_CLOSE]):
            return predicates

        if self._is(TOKEN.TEXT):
            self._eat()

        if predicates := self._expected_eat(TOKEN.STRING_CLOSE):
            return predicates + [TOKEN.TEXT.value]

        return []

    def _parse_value(self) -> PREDICATES_TYPE:
        if predicates := self._expected(VALUE):
            return predicates

        match self._get_current_token:
            case TOKEN.STRING_OPEN:
                return self._parse_string()
            case TOKEN.FLOAT:
                return self._parse_number()
            case TOKEN.INTEGER:
                return self._parse_number()
            case TOKEN.OBJ_OPEN:
                return self._parse_object()
            case TOKEN.ARR_OPEN:
                return self._parse_array()
            case TOKEN.BOOL:
                return self._parse_bool()
            case TOKEN.NULL:
                return self._parse_null()
            case _:
                return [v[1].value for v in VALUE]
