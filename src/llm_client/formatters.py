from __future__ import annotations

import json
import time
from typing import Any

import regex

from src.models.definition import Definition
from src.models.prompt import Prompt


def build_function_name_pattern(functions: list[str]) -> str:
    """
    Generates a regex pattern to enforce a JSON function name.

    Args:
        functions: List of available function names.

    Returns:
        JSON string containing the regex pattern for the function name.
    """
    functions = [
        regex.escape(f, special_only=True, literal_spaces=True)
        for f in functions
    ]
    function_name_pattern: str = rf"({'|'.join(functions)})"
    return f'{{"function_name": "{function_name_pattern}"}}'


def build_function_call_pattern(
    prompt: Prompt,
    definition: Definition,
) -> str:
    """
    Generates a regex pattern to enforce a JSON function call.

    Args:
        prompt: User input prompt.
        definition: Function definition to enforce.

    Returns:
        String representing the regex pattern for the expected JSON call.
    """
    params: dict[str, Any] = {
        "prompt": prompt.prompt.replace('"', "'"),
        "name": definition.name,
        "parameters": {},
    }

    timestamps = time.time_ns()
    KEY_STRING = f"___JSON_TYPE_STRING__{timestamps}___"
    KEY_NUMBER = f"___JSON_TYPE_NUMBER__{timestamps}___"
    KEY_BOOL = f"___JSON_TYPE_BOOL__{timestamps}___"

    for name, data in definition.parameters.items():
        match data.type:
            case "string":
                params["parameters"][name] = KEY_STRING
            case "number":
                params["parameters"][name] = KEY_NUMBER
            case "bool":
                params["parameters"][name] = KEY_BOOL
            case _:
                params["parameters"][name] = KEY_STRING

    fmt = json.dumps(params)
    fmt = regex.escape(fmt, special_only=True, literal_spaces=True)
    fmt = fmt.replace(f'"{KEY_STRING}"', r"\"[^\"\\]*\"")
    fmt = fmt.replace(
        f'"{KEY_NUMBER}"',
        r"[+-]?(\d{1,15}(\.\d{0,15})?|\.\d{1,15})([eE][+-]?\d{1,15})?",
    )
    fmt = fmt.replace(f'"{KEY_BOOL}"', r"(true|false)")

    return fmt
