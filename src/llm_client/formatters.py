from __future__ import annotations

import json
import time
from types import TracebackType
from typing import Any, cast

import regex
from pydantic import BaseModel, PrivateAttr
from typing_extensions import Self

from src.exceptions.schema import SchemaConstraintArgumentError
from src.models.definition import Definition
from src.models.prompt import Prompt


class Constraint(BaseModel):
    """
    Context manager for building regex patterns.

    This class handles the registration and safe replacement of tokens
    to generate constrained formatting patterns for LLM outputs.
    """

    _registry: dict[str, tuple[bool, str]] = PrivateAttr(default_factory=dict)

    def build(self, fmt: str, args: dict[str, str] | None = None) -> str:
        """
        Replaces registered tokens in the format string with their values.

        Args:
            fmt: The format string containing tokens to replace.
            args: Dictionary mapping custom token names to their values.

        Returns:
            The final regex pattern string.

        Raises:
            SchemaConstraintArgumentError: If a required argument is missing.
        """

        args = args or {}

        required = {
            value
            for _, (is_internal_arg, value) in self._registry.items()
            if not is_internal_arg
        }

        if missing_args := required - args.keys():
            self._registry.clear()
            raise SchemaConstraintArgumentError(missing_args.pop())

        replacements: dict[str, str] = {
            token: args[self.safe_literal(value)]
            if not is_internal_arg
            else value
            for token, (is_internal_arg, value) in self._registry.items()
        }
        self._registry.clear()

        fmt = self.safe_literal(fmt)
        for token, value in replacements.items():
            fmt = fmt.replace(self.safe_literal(token), value)

        return fmt

    def build_json(
        self,
        data: dict[str, Any],
        args: dict[str, str] | None = None,
    ) -> str:
        """
        Serializes a dictionary to JSON and applies the build replacements.

        Args:
            data: The dictionary to format and build from.
            args: Dictionary mapping custom token names to their values.

        Returns:
            The final regex pattern string representing the JSON.
        """

        fmt = json.dumps(data)
        return self.build(fmt, args)

    def token(self, name: str, include_extra_quote: bool = False) -> str:
        """
        Registers a placeholder for a custom user-defined token.

        Args:
            name: The name identifying this token.
            include_extra_quote: Whether to expect surrounding quotes.
                (Useful when you need to enforce or omit double quotes in
                the resulting JSON string.)

        Returns:
            The generated placeholder string to use in the template.
        """

        name = self.safe_literal(name)
        return self._register(
            f"TOKEN_{name}",
            name,
            is_internal_arg=False,
            include_quote=include_extra_quote,
        )

    def string_regex(self, include_extra_quote: bool = True) -> str:
        """
        Registers a regex pattern for parsing a JSON string.

        Args:
            include_extra_quote: Whether to expect surrounding quotes.
                (Useful when you need to enforce or omit double quotes in
                the resulting JSON string.)

        Returns:
            The generated placeholder string to use in the template.
        """

        return self._register(
            "STRING",
            r'"([^"\\]*)"',
            is_internal_arg=True,
            include_quote=include_extra_quote,
        )

    def number_regex(self, include_extra_quote: bool = True) -> str:
        """
        Registers a regex pattern for parsing a JSON number.

        Args:
            include_extra_quote: Whether to expect surrounding quotes.
                (Useful when you need to enforce or omit double quotes in
                the resulting JSON string.)

        Returns:
            The generated placeholder string to use in the template.
        """

        return self._register(
            "NUMBER",
            r"[+-]?(\d{1,15}(\.\d{0,15})?|\.\d{1,15})([eE][+-]?\d{1,15})?",
            is_internal_arg=True,
            include_quote=include_extra_quote,
        )

    def bool_regex(self, include_extra_quote: bool = True) -> str:
        """
        Registers a regex pattern for parsing a JSON boolean.

        Args:
            include_extra_quote: Whether to expect surrounding quotes.
                (Useful when you need to enforce or omit double quotes in
                the resulting JSON string.)

        Returns:
            The generated placeholder string to use in the template.
        """

        return self._register(
            "BOOL",
            r"(true|false)",
            is_internal_arg=True,
            include_quote=include_extra_quote,
        )

    def safe_literal(self, value: str) -> str:
        """
        Safely escapes regex special characters within a given string.

        Args:
            value: The raw string to escape.

        Returns:
            The safely escaped string.
        """

        return cast(
            str, regex.escape(value, special_only=True, literal_spaces=True)
        )

    def _register(
        self,
        prefix: str,
        value: str,
        is_internal_arg: bool = False,
        include_quote: bool = False,
    ) -> str:
        """
        Internal method to store a replacement target in the registry.

        Args:
            prefix: An identifier prefix for the specific token type.
            value: The regex pattern or argument name to inject.
            is_internal_arg: True if 'value' is an internal regex.
            include_extra_quote: Whether to expect surrounding quotes.
                (Useful when you need to enforce or omit double quotes in
                the resulting JSON string.)

        Returns:
            The raw token string placeholder.
        """

        token: str = f"___JSON_TYPE_{prefix}_{time.time_ns()}__"
        target = f'"{token}"' if include_quote else token

        if target not in self._registry:
            self._registry[target] = (is_internal_arg, value)

        return token

    def __enter__(self) -> Self:
        """
        Enters the context manager and returns the Constraint instance.

        Returns:
            The current instance of the Constraint builder.
        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """
        Exits the context manager and cleans up the internal registry.

        Args:
            exc_type: The type of the exception raised, if any.
            exc_val: The instance of the exception raised, if any.
            exc_tb: The traceback of the exception raised, if any.
        """
        self._registry.clear()


def build_function_name_pattern(prompt: Prompt, functions: list[str]) -> str:
    """
    Generates a regex pattern to enforce a JSON function name.

    Args:
        prompt: User input prompt object.
        functions: List of available function names to match against.

    Returns:
        JSON string containing the regex pattern for the function name.
    """

    with Constraint() as cst:
        safe_functions = [cst.safe_literal(f) for f in functions]
        fmt = {
            "tool": cst.token("functions"),
        }
        return cst.build_json(
            fmt, {"functions": rf"({'|'.join(safe_functions)})"}
        )


def build_function_call_pattern(
    prompt: Prompt,
    definition: Definition,
) -> str:
    """
    Generates a regex pattern to enforce a JSON function call.

    Args:
        prompt: User input prompt object.
        definition: Function definition to enforce and format.

    Returns:
        String representing the regex pattern for the expected JSON call.
    """

    with Constraint() as cst:
        params: dict[str, Any] = {
            "prompt": prompt.prompt,
            "name": definition.name,
            "parameters": {},
        }

        for name, data in definition.parameters.items():
            match data.type:
                case "number":
                    params["parameters"][name] = cst.number_regex()
                case "bool":
                    params["parameters"][name] = cst.bool_regex()
                case "string" | _:
                    params["parameters"][name] = cst.string_regex()

        return cst.build_json(params)
